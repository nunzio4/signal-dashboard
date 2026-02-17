from fastapi import APIRouter, Request

from app.models import IngestionStatusResponse

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/run")
async def trigger_ingestion(request: Request):
    """Trigger a manual ingestion + analysis cycle."""
    db = request.app.state.db

    # Import here to avoid circular imports
    from app.services.ingestion import IngestionService
    from app.services.analysis import AnalysisService

    ingestion_svc = IngestionService(db)
    stats = await ingestion_svc.run_full_ingestion()

    analysis_svc = AnalysisService(db)
    analysis_stats = await analysis_svc.analyze_pending(batch_size=50)

    return {
        "ingestion": stats,
        "analysis": analysis_stats,
    }


@router.get("/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(request: Request):
    db = request.app.state.db

    # Total articles
    total = (await (await db.execute("SELECT COUNT(*) as cnt FROM articles")).fetchone())["cnt"]
    pending = (await (await db.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE analysis_status = 'pending'"
    )).fetchone())["cnt"]
    analyzed = (await (await db.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE analysis_status = 'analyzed'"
    )).fetchone())["cnt"]
    sources_enabled = (await (await db.execute(
        "SELECT COUNT(*) as cnt FROM sources WHERE enabled = 1"
    )).fetchone())["cnt"]

    last_cursor = await db.execute(
        "SELECT last_fetched_at FROM sources WHERE last_fetched_at IS NOT NULL ORDER BY last_fetched_at DESC LIMIT 1"
    )
    last_row = await last_cursor.fetchone()

    return IngestionStatusResponse(
        last_run=last_row["last_fetched_at"] if last_row else None,
        articles_total=total,
        articles_pending=pending,
        articles_analyzed=analyzed,
        sources_enabled=sources_enabled,
    )
