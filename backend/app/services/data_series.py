"""
Fetcher service for structured data series from FRED, BLS, and SEC EDGAR.
"""
import json
import logging
from datetime import datetime, timedelta

import aiosqlite
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
BLS_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
SEC_EDGAR_BASE = "https://data.sec.gov/api/xbrl/companyconcept"
SEC_USER_AGENT = "SignalDashboard admin@signaldashboard.app"


class DataSeriesFetcher:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def fetch_all(self) -> dict:
        """Fetch data for all enabled data series."""
        cursor = await self.db.execute(
            "SELECT * FROM data_series WHERE enabled = 1"
        )
        series_list = await cursor.fetchall()

        stats = {"fetched": 0, "new_points": 0, "errors": 0, "skipped": 0}

        for series in series_list:
            try:
                provider = series["provider"]
                config = json.loads(series["series_config"])

                if provider == "fred":
                    count = await self._fetch_fred(series["id"], config)
                elif provider == "bls":
                    count = await self._fetch_bls(series["id"], config)
                elif provider == "sec_edgar":
                    count = await self._fetch_sec_edgar(series["id"], config)
                else:
                    logger.warning(f"Unknown provider {provider} for series {series['id']}")
                    stats["skipped"] += 1
                    continue

                await self.db.execute(
                    "UPDATE data_series SET last_fetched_at = datetime('now') WHERE id = ?",
                    (series["id"],),
                )
                await self.db.commit()
                stats["fetched"] += 1
                stats["new_points"] += count
                logger.info(f"Fetched {count} new points for {series['id']}")

            except Exception as e:
                logger.error(f"Error fetching series {series['id']}: {e}")
                stats["errors"] += 1

        return stats

    async def _fetch_fred(self, series_id: str, config: dict) -> int:
        """Fetch observations from FRED — uses API key if available, falls back to CSV."""
        fred_series = config["series_id"]
        start_date = (datetime.utcnow() - timedelta(days=3 * 365)).strftime("%Y-%m-%d")

        if settings.fred_api_key:
            return await self._fetch_fred_api(series_id, fred_series, start_date)
        else:
            return await self._fetch_fred_csv(series_id, fred_series, start_date)

    async def _fetch_fred_api(self, series_id: str, fred_series: str, start_date: str) -> int:
        """Fetch via FRED JSON API (requires key)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(FRED_API_BASE, params={
                "series_id": fred_series,
                "api_key": settings.fred_api_key,
                "file_type": "json",
                "observation_start": start_date,
                "sort_order": "desc",
                "limit": 500,
            })
            resp.raise_for_status()
            data = resp.json()

        observations = data.get("observations", [])
        return await self._store_fred_observations(
            series_id,
            [(obs["date"], obs["value"]) for obs in observations],
        )

    async def _fetch_fred_csv(self, series_id: str, fred_series: str, start_date: str) -> int:
        """Fetch via FRED CSV download (no API key needed)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                FRED_CSV_BASE,
                params={"id": fred_series, "cosd": start_date},
                headers={"User-Agent": "Mozilla/5.0 SignalDashboard/1.0"},
                follow_redirects=True,
            )
            resp.raise_for_status()

        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            return 0

        # First line is header: "observation_date,SERIESID"
        observations = []
        for line in lines[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                observations.append((parts[0], parts[1]))

        logger.info(f"FRED CSV: {fred_series} returned {len(observations)} observations (no API key)")
        return await self._store_fred_observations(series_id, observations)

    async def _store_fred_observations(self, series_id: str, observations: list[tuple]) -> int:
        """Store date/value pairs from FRED into data_points."""
        new_count = 0
        for date_str, value_str in observations:
            if value_str == "." or not value_str:
                continue  # Missing data point
            try:
                value = float(value_str)
            except ValueError:
                continue
            try:
                await self.db.execute(
                    """INSERT OR IGNORE INTO data_points (series_id, date, value)
                       VALUES (?, ?, ?)""",
                    (series_id, date_str, value),
                )
                new_count += 1
            except Exception:
                pass  # Duplicate, ignore

        await self.db.commit()
        return new_count

    async def _fetch_bls(self, series_id: str, config: dict) -> int:
        """Fetch data from BLS API v2."""
        bls_series = config["series_id"]
        current_year = datetime.utcnow().year
        start_year = str(current_year - 3)
        end_year = str(current_year)

        payload = {
            "seriesid": [bls_series],
            "startyear": start_year,
            "endyear": end_year,
        }
        if settings.bls_api_key:
            payload["registrationkey"] = settings.bls_api_key

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(BLS_BASE, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            logger.error(f"BLS API error for {bls_series}: {data.get('message')}")
            return 0

        new_count = 0
        for series_data in data.get("Results", {}).get("series", []):
            for point in series_data.get("data", []):
                year = point["year"]
                period = point["period"]
                value_str = point["value"]

                if not period.startswith("M"):
                    continue  # Skip annual or other periods

                month = period[1:]  # "M01" -> "01"
                date_str = f"{year}-{month}-01"

                try:
                    value = float(value_str)
                except ValueError:
                    continue

                try:
                    await self.db.execute(
                        """INSERT OR IGNORE INTO data_points (series_id, date, value)
                           VALUES (?, ?, ?)""",
                        (series_id, date_str, value),
                    )
                    new_count += 1
                except Exception:
                    pass

        await self.db.commit()
        return new_count

    async def _fetch_sec_edgar(self, series_id: str, config: dict) -> int:
        """Fetch quarterly capex from SEC EDGAR XBRL API."""
        cik = config["cik"]
        # Some companies use different XBRL concepts for capex
        concepts = [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ]

        data = None
        async with httpx.AsyncClient(timeout=30) as client:
            for concept in concepts:
                url = f"{SEC_EDGAR_BASE}/CIK{cik}/us-gaap/{concept}.json"
                resp = await client.get(url, headers={"User-Agent": SEC_USER_AGENT})
                if resp.status_code == 200:
                    candidate = resp.json()
                    units = candidate.get("units", {}).get("USD", [])
                    forms = [f for f in units if f.get("form") in ("10-Q", "10-K")]
                    # Use whichever concept has the most recent data
                    if forms:
                        max_date = max(f["end"] for f in forms)
                        if data is None:
                            data = candidate
                            best_date = max_date
                            best_concept = concept
                        elif max_date > best_date:
                            data = candidate
                            best_date = max_date
                            best_concept = concept

        if data is None:
            logger.warning(f"No SEC EDGAR data found for {series_id} (CIK {cik})")
            return 0

        logger.info(f"Using XBRL concept '{best_concept}' for {series_id} (latest: {best_date})")

        units = data.get("units", {}).get("USD", [])
        if not units:
            return 0

        # Filter for quarterly filings (10-Q and 10-K) and deduplicate
        seen_periods = set()
        new_count = 0

        # Sort by filed date descending to get the most recent values
        quarterly_data = []
        for fact in units:
            form = fact.get("form", "")
            if form not in ("10-Q", "10-K"):
                continue
            end_date = fact.get("end", "")
            fp = fact.get("fp", "")
            val = fact.get("val", 0)

            # Use end date as the period key to deduplicate
            if end_date in seen_periods:
                continue
            seen_periods.add(end_date)

            quarterly_data.append({
                "date": end_date,
                "value": val / 1_000_000_000,  # Convert to billions
                "fp": fp,
            })

        # Store the data points
        for point in quarterly_data:
            try:
                await self.db.execute(
                    """INSERT OR IGNORE INTO data_points (series_id, date, value)
                       VALUES (?, ?, ?)""",
                    (series_id, point["date"], round(point["value"], 2)),
                )
                new_count += 1
            except Exception:
                pass

        await self.db.commit()
        return new_count
