"""
Backfill historical prediction market data from Polymarket CLOB and Kalshi APIs.

Polymarket: Uses CLOB /prices-history endpoint (daily fidelity, interval=all)
Kalshi: Uses /series/{s}/markets/{t}/candlesticks endpoint (daily candles)

Both APIs are public (no auth needed).
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone

import aiosqlite
import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

POLYMARKET_CLOB = "https://clob.polymarket.com"
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"

# June 1, 2025 in Unix time
START_TS = 1748736000


async def backfill_polymarket(db: aiosqlite.Connection, series_id: str, config: dict) -> int:
    """Backfill Polymarket historical prices via CLOB prices-history."""
    clob_token_id = config.get("clob_token_id")
    if not clob_token_id:
        logger.warning(f"  {series_id}: no clob_token_id in config, skipping")
        return 0

    url = f"{POLYMARKET_CLOB}/prices-history"
    params = {
        "market": clob_token_id,
        "interval": "all",
        "fidelity": 1440,  # daily
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    history = data.get("history", [])
    if not history:
        logger.warning(f"  {series_id}: no history returned")
        return 0

    new_count = 0
    for point in history:
        ts = point["t"]
        prob = round(point["p"] * 100, 2)  # 0-1 -> 0-100%
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

        try:
            await db.execute(
                "INSERT OR IGNORE INTO data_points (series_id, date, value) VALUES (?, ?, ?)",
                (series_id, date_str, prob),
            )
            new_count += 1
        except Exception:
            pass

    await db.commit()
    return new_count


async def backfill_kalshi(db: aiosqlite.Connection, series_id: str, config: dict) -> int:
    """Backfill Kalshi historical prices via candlestick endpoint."""
    ticker = config["ticker"]
    series_ticker = config.get("series_ticker")
    if not series_ticker:
        # Derive from event endpoint
        async with httpx.AsyncClient(timeout=30) as client:
            event_ticker = config.get("event_ticker", ticker)
            resp = await client.get(f"{KALSHI_API}/events/{event_ticker}")
            resp.raise_for_status()
            event_data = resp.json()
            series_ticker = event_data.get("event", {}).get("series_ticker", "")
        if not series_ticker:
            logger.warning(f"  {series_id}: could not determine series_ticker, skipping")
            return 0

    end_ts = int(datetime.now(timezone.utc).timestamp())
    url = f"{KALSHI_API}/series/{series_ticker}/markets/{ticker}/candlesticks"
    params = {
        "start_ts": START_TS,
        "end_ts": end_ts,
        "period_interval": 1440,  # daily
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    candles = data.get("candlesticks", [])
    if not candles:
        logger.warning(f"  {series_id}: no candlesticks returned")
        return 0

    new_count = 0
    for candle in candles:
        ts = candle["end_period_ts"]
        close_price = candle["price"]["close"]  # 0-99 cents = probability %
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

        try:
            await db.execute(
                "INSERT OR IGNORE INTO data_points (series_id, date, value) VALUES (?, ?, ?)",
                (series_id, date_str, float(close_price)),
            )
            new_count += 1
        except Exception:
            pass

    await db.commit()
    return new_count


async def main():
    sys.path.insert(0, ".")
    from app.config import settings

    db_path = str(settings.db_path)
    logger.info(f"Opening database: {db_path}")

    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row

    # Update series_config for prediction market series with new fields
    logger.info("\n=== Updating series configs with historical API fields ===")
    updates = {
        "poly_recession_2026": {"slug": "us-recession-by-end-of-2026", "outcome_index": 0,
            "clob_token_id": "100379208559626151022751801118534484742123694725746262280150222742563282755057"},
        "poly_unemployment_5pct": {"slug": "how-high-will-us-unemployment-go-in-2026", "outcome_index": 0, "market_index": 0,
            "clob_token_id": "108683340244272797423903928139400863604636305580987691842877673995933500284505"},
        "poly_unemployment_6pct": {"slug": "how-high-will-us-unemployment-go-in-2026", "outcome_index": 0, "market_index": 2,
            "clob_token_id": "108018091346802760465812775595296174303353396224301843350580443613286618815662"},
        "poly_ai_bubble_2026": {"slug": "ai-bubble-burst-by", "outcome_index": 0, "market_index": 2,
            "clob_token_id": "95143949049440805515065120245245136072200903084986833252741074455111459269340"},
        "kalshi_recession_2026": {"ticker": "KXRECSSNBER-26", "series_ticker": "KXRECSSNBER", "event_ticker": "KXRECSSNBER-26"},
        "kalshi_unemployment_5pct": {"ticker": "KXU3MAX-27-5", "series_ticker": "KXU3MAX", "event_ticker": "KXU3MAX-27"},
        "kalshi_unemployment_6pct": {"ticker": "KXU3MAX-27-6", "series_ticker": "KXU3MAX", "event_ticker": "KXU3MAX-27"},
        "kalshi_fed_rate_above_4": {"ticker": "KXFED-27APR-T4.00", "series_ticker": "KXFED", "event_ticker": "KXFED-27APR"},
        "kalshi_ai_takeover": {"ticker": "KXUSTAKEOVER-30", "series_ticker": "KXUSTAKEOVER", "event_ticker": "KXUSTAKEOVER-30"},
        "kalshi_imf_recession": {"ticker": "KXIMFRECESS-27", "series_ticker": "KXIMFRECESS", "event_ticker": "KXIMFRECESS-27"},
    }

    for sid, new_config in updates.items():
        await db.execute(
            "UPDATE data_series SET series_config = ? WHERE id = ?",
            (json.dumps(new_config), sid),
        )
    await db.commit()
    logger.info(f"Updated configs for {len(updates)} series")

    # Fetch all prediction market series
    cursor = await db.execute(
        "SELECT * FROM data_series WHERE provider IN ('polymarket', 'kalshi') AND enabled = 1"
    )
    series_list = await cursor.fetchall()
    logger.info(f"\n=== Backfilling {len(series_list)} prediction market series ===\n")

    total_points = 0
    for series in series_list:
        config = json.loads(series["series_config"])
        provider = series["provider"]

        try:
            if provider == "polymarket":
                count = await backfill_polymarket(db, series["id"], config)
            elif provider == "kalshi":
                count = await backfill_kalshi(db, series["id"], config)
            else:
                continue

            # Check how many points we now have
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt, MIN(date) as first_date, MAX(date) as last_date FROM data_points WHERE series_id = ?",
                (series["id"],),
            )
            row = await cursor.fetchone()
            logger.info(
                f"  {series['name']:42} | +{count:3} new | total: {row['cnt']:4} pts | "
                f"{row['first_date']} to {row['last_date']}"
            )
            total_points += count
        except Exception as e:
            logger.error(f"  {series['name']:42} | ERROR: {e}")

    logger.info(f"\n=== Done: {total_points} new data points added ===")

    # Show summary
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM data_points")
    row = await cursor.fetchone()
    logger.info(f"Total data points in database: {row['cnt']}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
