import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _initial_ingestion(db):
    """Run initial ingestion as a background task (doesn't block server start)."""
    await asyncio.sleep(5)  # Let the server fully start first
    try:
        from app.services.ingestion import IngestionService

        logger.info("Running initial article ingestion (background)...")
        ingestion_svc = IngestionService(db)
        stats = await ingestion_svc.run_full_ingestion()
        logger.info(f"Initial ingestion complete: {stats}")
    except Exception as e:
        logger.error(f"Initial ingestion failed (will retry on schedule): {e}")

    # Generate data signals from existing data points
    try:
        from app.services.data_signals import DataSignalGenerator

        logger.info("Generating data signals (background)...")
        generator = DataSignalGenerator(db)
        ds_stats = await generator.generate_all()
        logger.info(f"Data signal generation complete: {ds_stats}")
    except Exception as e:
        logger.error(f"Data signal generation failed (will retry on schedule): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = None
    scheduler = None
    ingestion_task = None

    try:
        # ── Database init ──
        from app.database import (
            get_db, init_database, seed_theses, seed_sources,
            seed_data_series, load_seed_data,
        )

        logger.info("Initializing database...")
        db = await get_db()
        await init_database(db)
        logger.info("Database initialized")

        await seed_theses(db)
        logger.info("Theses seeded")

        await seed_sources(db)
        logger.info("Sources seeded")

        await seed_data_series(db)
        logger.info("Data series seeded")

        try:
            await load_seed_data(db)
            logger.info("Seed data loaded")
        except Exception as e:
            logger.error(f"Seed data loading failed (non-fatal): {e}")

        app.state.db = db

        # ── Scheduler ──
        try:
            from app.services.scheduler import create_scheduler

            scheduler = create_scheduler(db)
            scheduler.start()
            app.state.scheduler = scheduler
            logger.info("Scheduler started")
        except Exception as e:
            logger.error(f"Scheduler failed to start (non-fatal): {e}")

        logger.info("Signal Dashboard backend started — ready for requests")

        # Kick off initial ingestion without blocking the server
        ingestion_task = asyncio.create_task(_initial_ingestion(db))

    except Exception as e:
        logger.error(f"CRITICAL startup error: {e}", exc_info=True)
        # Still yield so the health endpoint can respond (for debugging)
        if db is not None:
            app.state.db = db

    yield

    # ── Shutdown ──
    if ingestion_task is not None:
        ingestion_task.cancel()
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    if db is not None:
        await db.close()
    logger.info("Signal Dashboard backend stopped")


app = FastAPI(title="Signal Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins — simplifies deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
from app.routers import dashboard, signals, articles, sources, ingest, data_series  # noqa: E402

app.include_router(dashboard.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(articles.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(data_series.router, prefix="/api")


@app.get("/api/health")
async def health(request: Request):
    """Health check with diagnostic info."""
    from pathlib import Path
    diag = {"status": "ok"}
    try:
        db = request.app.state.db
        if db:
            cur = await db.execute("SELECT COUNT(*) as c FROM daily_scores")
            row = await cur.fetchone()
            diag["daily_scores"] = row["c"]

            cur2 = await db.execute("SELECT COUNT(*) as c FROM signals")
            row2 = await cur2.fetchone()
            diag["signals"] = row2["c"]

            cur3 = await db.execute("SELECT COUNT(*) as c FROM data_points")
            row3 = await cur3.fetchone()
            diag["data_points"] = row3["c"]

            cur4 = await db.execute("SELECT COUNT(*) as c FROM articles")
            row4 = await cur4.fetchone()
            diag["articles"] = row4["c"]

        # Check if seed.db exists
        backend_dir = Path(__file__).resolve().parent.parent
        seed_path = backend_dir / "seed.db"
        diag["seed_db_exists"] = seed_path.exists()
        if seed_path.exists():
            diag["seed_db_size_kb"] = seed_path.stat().st_size // 1024
        from app.config import settings
        diag["db_path"] = str(settings.db_path)
        diag["db_exists"] = settings.db_path.exists()
    except Exception as e:
        diag["diag_error"] = str(e)
    return diag


# ── Root redirect to LinkedIn ──

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(
        "https://www.linkedin.com/in/jamesincognito/", status_code=302
    )


# ── Serve React frontend at /signal-dashboard ──
_static = settings.static_dir
if _static.exists() and (_static / "index.html").exists():
    logger.info(f"Serving static frontend from {_static} at /signal-dashboard")

    # Serve Vite-built assets at /signal-dashboard/assets
    if (_static / "assets").exists():
        app.mount(
            "/signal-dashboard/assets",
            StaticFiles(directory=str(_static / "assets")),
            name="assets",
        )

    @app.get("/signal-dashboard/favicon.ico", include_in_schema=False)
    async def favicon():
        fav = _static / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav))
        return FileResponse(str(_static / "index.html"))

    @app.get("/signal-dashboard", include_in_schema=False)
    async def signal_dashboard_root():
        """Serve the SPA index at /signal-dashboard (no trailing slash)."""
        return FileResponse(str(_static / "index.html"))

    @app.get("/signal-dashboard/{full_path:path}", include_in_schema=False)
    async def signal_dashboard_spa(full_path: str):
        """SPA catch-all: serve static files or index.html for client routing."""
        file_path = _static / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_static / "index.html"))
else:
    logger.info(f"No static frontend found at {_static} (dev mode)")
