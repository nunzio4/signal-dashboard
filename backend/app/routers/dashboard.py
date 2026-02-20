import json
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request

from app.models import (
    DashboardResponse,
    SignalResponse,
    ThesisDashboardData,
    TrendPoint,
)
from app.services.aggregation import AggregationService


def _normalize_quote(quote: str) -> str:
    """Normalize a quote for fuzzy dedup: lowercase, strip punctuation/hyphens, collapse whitespace."""
    if not quote:
        return ""
    q = quote.lower()
    q = re.sub(r"[^a-z0-9\s]", " ", q)  # strip non-alphanumeric
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _normalize_title(title: str) -> str:
    """Normalize a title for dedup: strip trailing source attribution
    (e.g. ' - Fortune', ' - AOL.com', ' | WSJ'), lowercase, strip punctuation."""
    if not title:
        return ""
    # Strip trailing " - Source Name" or " | Source Name"
    t = re.sub(r"\s*[\-–—|]\s*[A-Za-z][A-Za-z0-9 .,'&]+$", "", title)
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(request: Request, days: int = Query(default=270, ge=7, le=365)):
    db = request.app.state.db
    agg = AggregationService(db)

    # Recompute today's scores before returning
    await agg.compute_daily_scores()

    cursor = await db.execute("SELECT id, name, description FROM theses ORDER BY id")
    theses = await cursor.fetchall()

    thesis_data = []
    for thesis in theses:
        tid = thesis["id"]

        current = await agg.get_current_score(tid)
        previous = await agg.get_previous_score(tid)
        trend_data = await agg.get_trend_data(tid, days)
        trend_dir = AggregationService.compute_trend_direction(trend_data)

        # Top 10 strongest signals from the trailing 24 hours,
        # deduplicated so each source_url / evidence_quote appears at most
        # once per thesis. Fetch extra rows then dedup in Python.
        cutoff_24h = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        sig_cursor = await db.execute(
            """SELECT id, thesis_id, direction, strength, confidence,
                      evidence_quote, reasoning, source_title, source_url,
                      signal_date, is_manual, signal_type, created_at
               FROM signals
               WHERE thesis_id = ? AND created_at >= ?
               ORDER BY strength DESC, confidence DESC
               LIMIT 50""",
            (tid, cutoff_24h),
        )
        sig_rows = await sig_cursor.fetchall()

        # Deduplicate: skip signals that share any of:
        #   - same source_url (exact)
        #   - same normalized source_title (catches same article from different RSS feeds)
        #   - same normalized evidence_quote (catches near-identical quotes with
        #     minor punctuation differences like "cash flow" vs "cash-flow")
        # Keeps the strongest signal since rows are sorted by strength DESC.
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        seen_quotes: set[str] = set()
        recent_signals: list[SignalResponse] = []
        for r in sig_rows:
            if len(recent_signals) >= 10:
                break
            url = r["source_url"] or ""
            title = r["source_title"] or ""
            quote = r["evidence_quote"] or ""
            norm_title = _normalize_title(title)
            norm_quote = _normalize_quote(quote)
            # Skip if we've already seen this article (by URL or title)
            # or this exact evidence (by normalized quote)
            if url and url in seen_urls:
                continue
            if norm_title and norm_title in seen_titles:
                continue
            if norm_quote and norm_quote in seen_quotes:
                continue
            if url:
                seen_urls.add(url)
            if norm_title:
                seen_titles.add(norm_title)
            if norm_quote:
                seen_quotes.add(norm_quote)
            recent_signals.append(
                SignalResponse(
                    id=r["id"],
                    thesis_id=r["thesis_id"],
                    direction=r["direction"],
                    strength=r["strength"],
                    confidence=r["confidence"],
                    evidence_quote=r["evidence_quote"],
                    reasoning=r["reasoning"],
                    source_title=r["source_title"],
                    source_url=r["source_url"],
                    signal_date=r["signal_date"],
                    is_manual=bool(r["is_manual"]),
                    signal_type=r["signal_type"] or "news",
                    created_at=r["created_at"],
                )
            )

        # Per-thesis signal counts split by type (news vs data).
        # Use created_at for both 7d and 24h so counts are consistent
        # (signal_date is the article publish date which can predate ingestion).
        cutoff_7d = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        count_cursor = await db.execute(
            """SELECT
                 SUM(CASE WHEN signal_type='news'  THEN 1 ELSE 0 END) as news_7d,
                 SUM(CASE WHEN signal_type='data'  THEN 1 ELSE 0 END) as data_7d
               FROM signals WHERE thesis_id = ? AND created_at >= ?""",
            (tid, cutoff_7d),
        )
        count_row = await count_cursor.fetchone()

        # 24h signal counts split by type
        count_24h_cursor = await db.execute(
            """SELECT
                 SUM(CASE WHEN signal_type='news'  THEN 1 ELSE 0 END) as news_24h,
                 SUM(CASE WHEN signal_type='data'  THEN 1 ELSE 0 END) as data_24h
               FROM signals WHERE thesis_id = ? AND created_at >= ?""",
            (tid, cutoff_24h),
        )
        count_24h_row = await count_24h_cursor.fetchone()

        thesis_data.append(
            ThesisDashboardData(
                thesis_id=tid,
                thesis_name=thesis["name"],
                thesis_description=thesis["description"],
                current_score=current,
                previous_score=previous,
                score_trend=trend_dir,
                trend_data=[TrendPoint(**p) for p in trend_data],
                recent_signals=recent_signals,
                news_signals_7d=count_row["news_7d"] or 0,
                news_signals_24h=count_24h_row["news_24h"] or 0,
                data_signals_7d=count_row["data_7d"] or 0,
                data_signals_24h=count_24h_row["data_24h"] or 0,
            )
        )

    # Global stats
    art_cursor = await db.execute("SELECT COUNT(*) as cnt FROM articles")
    art_count = (await art_cursor.fetchone())["cnt"]

    # Signal totals split by type
    sig_split_cursor = await db.execute(
        """SELECT
             SUM(CASE WHEN signal_type='news'  THEN 1 ELSE 0 END) as news_total,
             SUM(CASE WHEN signal_type='data'  THEN 1 ELSE 0 END) as data_total
           FROM signals"""
    )
    sig_split = await sig_split_cursor.fetchone()

    # 24-hour counts
    cutoff_global_24h = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    art_24h_cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE ingested_at >= ?",
        (cutoff_global_24h,),
    )
    art_24h = (await art_24h_cursor.fetchone())["cnt"]

    sig_24h_cursor = await db.execute(
        """SELECT
             SUM(CASE WHEN signal_type='news'  THEN 1 ELSE 0 END) as news_24h,
             SUM(CASE WHEN signal_type='data'  THEN 1 ELSE 0 END) as data_24h
           FROM signals WHERE created_at >= ?""",
        (cutoff_global_24h,),
    )
    sig_24h = await sig_24h_cursor.fetchone()

    # Data point totals
    dp_cursor = await db.execute("SELECT COUNT(*) as cnt FROM data_points")
    dp_total = (await dp_cursor.fetchone())["cnt"]

    dp_24h_cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM data_points WHERE fetched_at >= ?",
        (cutoff_global_24h,),
    )
    dp_24h = (await dp_24h_cursor.fetchone())["cnt"]

    last_cursor = await db.execute(
        "SELECT last_fetched_at FROM sources WHERE last_fetched_at IS NOT NULL ORDER BY last_fetched_at DESC LIMIT 1"
    )
    last_row = await last_cursor.fetchone()

    # Most recent data series fetch
    ds_cursor = await db.execute(
        "SELECT last_fetched_at FROM data_series WHERE last_fetched_at IS NOT NULL ORDER BY last_fetched_at DESC LIMIT 1"
    )
    ds_row = await ds_cursor.fetchone()

    # Next scheduled ingestion times from APScheduler
    # APScheduler returns tz-aware datetimes; convert to UTC for consistency
    next_ingestion_str = None
    next_data_fetch_str = None
    try:
        from datetime import timezone
        scheduler = request.app.state.scheduler
        if scheduler:
            ing_job = scheduler.get_job("ingestion")
            if ing_job and ing_job.next_run_time:
                utc_time = ing_job.next_run_time.astimezone(timezone.utc)
                next_ingestion_str = utc_time.strftime("%Y-%m-%d %H:%M:%S")
            ds_job = scheduler.get_job("data_series")
            if ds_job and ds_job.next_run_time:
                utc_time = ds_job.next_run_time.astimezone(timezone.utc)
                next_data_fetch_str = utc_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    return DashboardResponse(
        theses=thesis_data,
        last_ingestion=last_row["last_fetched_at"] if last_row else None,
        last_data_fetch=ds_row["last_fetched_at"] if ds_row else None,
        next_ingestion=next_ingestion_str,
        next_data_fetch=next_data_fetch_str,
        total_articles=art_count,
        total_news_signals=sig_split["news_total"] or 0,
        total_data_signals=sig_split["data_total"] or 0,
        news_signals_24h=sig_24h["news_24h"] or 0,
        data_signals_24h=sig_24h["data_24h"] or 0,
        articles_24h=art_24h,
        total_data_points=dp_total,
        data_points_24h=dp_24h,
    )
