import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import get_db, init_database, seed_theses, seed_sources, seed_data_series, load_seed_data
from app.services.scheduler import create_scheduler
from app.services.ingestion import IngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def _initial_ingestion(db):
    """Run initial ingestion as a background task (doesn't block server start)."""
    await asyncio.sleep(5)  # Let the server fully start first
    try:
        logging.info("Running initial article ingestion (background)...")
        ingestion_svc = IngestionService(db)
        stats = await ingestion_svc.run_full_ingestion()
        logging.info(f"Initial ingestion complete: {stats}")
    except Exception as e:
        logging.error(f"Initial ingestion failed (will retry on schedule): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = await get_db()
    await init_database(db)
    await seed_theses(db)
    await seed_sources(db)
    await seed_data_series(db)
    await load_seed_data(db)
    app.state.db = db

    scheduler = create_scheduler(db)
    scheduler.start()
    app.state.scheduler = scheduler

    logging.info("Signal Dashboard backend started — ready for requests")

    # Kick off initial ingestion without blocking the server
    ingestion_task = asyncio.create_task(_initial_ingestion(db))

    yield

    # Shutdown
    ingestion_task.cancel()
    scheduler.shutdown(wait=False)
    await db.close()
    logging.info("Signal Dashboard backend stopped")


app = FastAPI(title="Signal Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
async def health():
    return {"status": "ok"}


# ── Serve React frontend in production ──
_static = settings.static_dir
if _static.exists() and (_static / "index.html").exists():
    # Serve static assets (JS, CSS, images) at /assets
    app.mount("/assets", StaticFiles(directory=str(_static / "assets")), name="assets")

    # Serve other static files (favicon, manifest, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        fav = _static / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav))
        return FileResponse(str(_static / "index.html"))

    # SPA catch-all: any non-API route serves index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Try to serve the file directly first (for things like robots.txt)
        file_path = _static / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_static / "index.html"))
