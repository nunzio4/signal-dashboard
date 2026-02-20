import json

from fastapi import APIRouter, Request, Query

router = APIRouter(prefix="/data-series", tags=["data-series"])


def _build_source_url(provider: str, series_config: str) -> str | None:
    """Build a human-readable source URL from the provider and series_config."""
    try:
        cfg = json.loads(series_config)
    except (json.JSONDecodeError, TypeError):
        return None

    if provider == "fred":
        sid = cfg.get("series_id", "")
        return f"https://fred.stlouisfed.org/series/{sid}" if sid else None
    elif provider == "bls":
        sid = cfg.get("series_id", "")
        return f"https://data.bls.gov/timeseries/{sid}" if sid else None
    elif provider == "sec_edgar":
        ticker = cfg.get("ticker", "")
        cik = cfg.get("cik", "")
        if cik:
            return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-Q"
        return None
    return None


@router.get("")
async def list_data_series(request: Request, thesis_id: str | None = None):
    """List all data series, optionally filtered by thesis."""
    db = request.app.state.db

    # Join with data_points to get the most recent observation date per series
    base_query = """
        SELECT ds.*,
               (SELECT MAX(dp.date) FROM data_points dp WHERE dp.series_id = ds.id) AS latest_date
        FROM data_series ds
    """
    if thesis_id:
        cursor = await db.execute(
            base_query + " WHERE ds.thesis_id = ? ORDER BY ds.name", (thesis_id,)
        )
    else:
        cursor = await db.execute(base_query + " ORDER BY ds.thesis_id, ds.name")

    rows = await cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["source_url"] = _build_source_url(d["provider"], d.get("series_config", ""))
        result.append(d)
    return result


@router.get("/{series_id}/points")
async def get_data_points(
    request: Request,
    series_id: str,
    days: int = Query(default=365, ge=30, le=1825),
):
    """Get data points for a specific series."""
    db = request.app.state.db

    from datetime import datetime, timedelta
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor = await db.execute(
        """SELECT date, value FROM data_points
           WHERE series_id = ? AND date >= ?
           ORDER BY date ASC""",
        (series_id, start_date),
    )
    rows = await cursor.fetchall()
    return [{"date": r["date"], "value": r["value"]} for r in rows]


@router.get("/by-thesis/{thesis_id}")
async def get_series_with_data(
    request: Request,
    thesis_id: str,
    days: int = Query(default=365, ge=30, le=1825),
):
    """Get all data series for a thesis, each with their recent data points."""
    db = request.app.state.db

    from datetime import datetime, timedelta
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    series_cursor = await db.execute(
        "SELECT * FROM data_series WHERE thesis_id = ? AND enabled = 1 ORDER BY name",
        (thesis_id,),
    )
    series_list = await series_cursor.fetchall()

    result = []
    for series in series_list:
        points_cursor = await db.execute(
            """SELECT date, value FROM data_points
               WHERE series_id = ? AND date >= ?
               ORDER BY date ASC""",
            (series["id"], start_date),
        )
        points = await points_cursor.fetchall()

        # Compute latest value and change
        latest = None
        previous = None
        change_pct = None
        if points:
            latest = points[-1]["value"]
            if len(points) >= 2:
                previous = points[-2]["value"]
                if previous and previous != 0:
                    change_pct = round(((latest - previous) / abs(previous)) * 100, 2)

        result.append({
            "id": series["id"],
            "name": series["name"],
            "description": series["description"],
            "unit": series["unit"],
            "direction_logic": series["direction_logic"],
            "provider": series["provider"],
            "last_fetched_at": series["last_fetched_at"],
            "latest_value": latest,
            "previous_value": previous,
            "change_pct": change_pct,
            "points": [{"date": p["date"], "value": p["value"]} for p in points],
        })

    return result


@router.post("/fetch")
async def trigger_data_fetch(request: Request):
    """Manually trigger data series fetching."""
    db = request.app.state.db
    from app.services.data_series import DataSeriesFetcher
    fetcher = DataSeriesFetcher(db)
    stats = await fetcher.fetch_all()
    return stats
