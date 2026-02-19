import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.ingestion import IngestionService
from app.services.analysis import AnalysisService
from app.services.aggregation import AggregationService
from app.services.data_series import DataSeriesFetcher
from app.config import settings

logger = logging.getLogger(__name__)


def create_scheduler(db) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def run_ingestion():
        try:
            svc = IngestionService(db)
            stats = await svc.run_full_ingestion()
            logger.info(f"Ingestion complete: {stats}")
        except Exception as e:
            logger.error(f"Ingestion error: {e}")

    async def run_analysis():
        try:
            svc = AnalysisService(db)
            stats = await svc.analyze_pending(batch_size=50)
            logger.info(f"Analysis complete: {stats}")
        except Exception as e:
            logger.error(f"Analysis error: {e}")

    async def run_aggregation():
        try:
            svc = AggregationService(db)
            await svc.compute_daily_scores()
            logger.info("Aggregation complete")
        except Exception as e:
            logger.error(f"Aggregation error: {e}")

    scheduler.add_job(
        run_ingestion,
        "interval",
        hours=settings.ingestion_interval_hours,
        id="ingestion",
    )
    scheduler.add_job(
        run_analysis,
        "interval",
        minutes=settings.analysis_interval_minutes,
        id="analysis",
    )
    scheduler.add_job(
        run_aggregation,
        "interval",
        hours=settings.aggregation_interval_hours,
        id="aggregation",
    )

    async def run_data_series():
        try:
            fetcher = DataSeriesFetcher(db)
            stats = await fetcher.fetch_all()
            logger.info(f"Data series fetch complete: {stats}")
        except Exception as e:
            logger.error(f"Data series fetch error: {e}")

    scheduler.add_job(
        run_data_series,
        "interval",
        hours=6,  # Fetch data series every 6 hours
        id="data_series",
    )

    return scheduler
