import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request

from app.models import (
    DashboardResponse,
    SignalResponse,
    ThesisDashboardData,
    TrendPoint,
)
from app.services.aggregation import AggregationService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(request: Request, days: int = Query(default=30, ge=7, le=90)):
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

        # Top 10 strongest signals from the trailing 24 hours
        cutoff_24h = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        sig_cursor = await db.execute(
            """SELECT id, thesis_id, direction, strength, confidence,
                      evidence_quote, reasoning, source_title, source_url,
                      signal_date, is_manual, created_at
               FROM signals WHERE thesis_id = ?
                 AND created_at >= ?
               ORDER BY strength DESC, confidence DESC
               LIMIT 10""",
            (tid, cutoff_24h),
        )
        sig_rows = await sig_cursor.fetchall()
        recent_signals = [
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
                created_at=r["created_at"],
            )
            for r in sig_rows
        ]

        # 7-day signal count
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        count_cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM signals WHERE thesis_id = ? AND signal_date >= ?",
            (tid, week_ago),
        )
        count_row = await count_cursor.fetchone()
        signal_count_7d = count_row["cnt"]

        # Supporting percentage
        sup_cursor = await db.execute(
            """SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN direction='supporting' THEN 1 ELSE 0 END) as sup
               FROM signals WHERE thesis_id = ?""",
            (tid,),
        )
        sup_row = await sup_cursor.fetchone()
        total = sup_row["total"] or 0
        sup = sup_row["sup"] or 0
        supporting_pct = (sup / total * 100) if total > 0 else 50.0

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
                signal_count_7d=signal_count_7d,
                supporting_pct=round(supporting_pct, 1),
            )
        )

    # Global stats
    art_cursor = await db.execute("SELECT COUNT(*) as cnt FROM articles")
    art_count = (await art_cursor.fetchone())["cnt"]

    sig_total_cursor = await db.execute("SELECT COUNT(*) as cnt FROM signals")
    sig_total = (await sig_total_cursor.fetchone())["cnt"]

    last_cursor = await db.execute(
        "SELECT last_fetched_at FROM sources WHERE last_fetched_at IS NOT NULL ORDER BY last_fetched_at DESC LIMIT 1"
    )
    last_row = await last_cursor.fetchone()

    return DashboardResponse(
        theses=thesis_data,
        last_ingestion=last_row["last_fetched_at"] if last_row else None,
        total_articles=art_count,
        total_signals=sig_total,
    )
