import aiosqlite
import json
from pathlib import Path
from app.config import settings

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS theses (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords    TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    url             TEXT,
    config          TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1,
    last_fetched_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       INTEGER REFERENCES sources(id),
    external_id     TEXT,
    title           TEXT NOT NULL,
    url             TEXT,
    author          TEXT,
    content         TEXT,
    published_at    TEXT,
    ingested_at     TEXT NOT NULL DEFAULT (datetime('now')),
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    UNIQUE(external_id)
);

CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id      INTEGER REFERENCES articles(id),
    thesis_id       TEXT NOT NULL REFERENCES theses(id),
    direction       TEXT NOT NULL,
    strength        INTEGER NOT NULL,
    confidence      REAL NOT NULL,
    evidence_quote  TEXT NOT NULL,
    reasoning       TEXT NOT NULL,
    source_title    TEXT,
    source_url      TEXT,
    signal_date     TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_manual       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_scores (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    thesis_id        TEXT NOT NULL REFERENCES theses(id),
    score_date       TEXT NOT NULL,
    composite_score  REAL NOT NULL,
    signal_count     INTEGER NOT NULL,
    supporting_count INTEGER NOT NULL,
    weakening_count  INTEGER NOT NULL,
    computed_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(thesis_id, score_date)
);

CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(analysis_status);
CREATE INDEX IF NOT EXISTS idx_articles_external_id ON articles(external_id);
CREATE INDEX IF NOT EXISTS idx_signals_thesis ON signals(thesis_id, signal_date);
CREATE INDEX IF NOT EXISTS idx_signals_article ON signals(article_id);
CREATE INDEX IF NOT EXISTS idx_daily_scores_thesis_date ON daily_scores(thesis_id, score_date);
"""

SEED_THESES = [
    {
        "id": "ai_job_displacement",
        "name": "AI Job Displacement",
        "description": (
            "Significant job losses coming due to AI adoption across industries. "
            "Tracking layoffs attributed to AI, hiring freezes, automation of "
            "white-collar work, company statements about AI replacing headcount."
        ),
        "keywords": json.dumps([
            "AI layoffs", "AI job losses", "AI automation jobs",
            "AI replacing workers", "workforce reduction AI",
            "AI hiring freeze", "white collar automation",
        ]),
    },
    {
        "id": "ai_deflation",
        "name": "AI Deflation",
        "description": (
            "Deflationary effects as cheaper AI tools replace expensive people "
            "and software. Tracking price drops in software/services due to AI "
            "competition, SaaS disruption, margin compression, AI driving down costs."
        ),
        "keywords": json.dumps([
            "AI deflation", "AI price disruption", "SaaS AI competition",
            "AI cost reduction", "software pricing pressure AI",
            "AI margin compression", "cheaper AI tools",
        ]),
    },
    {
        "id": "datacenter_credit_crisis",
        "name": "Datacenter Credit Crisis",
        "description": (
            "Credit crisis from datacenter overbuilding. AI revenue failing to "
            "match capex, GPU obsolescence risk, datacenter financing stress, "
            "stranded assets. Specifically because AI-driven revenues will not "
            "catch nor keep up with capex, and existing chips and technology "
            "risk becoming deprecated and obsolete."
        ),
        "keywords": json.dumps([
            "datacenter overbuilding", "AI capex", "datacenter credit",
            "GPU obsolescence", "datacenter debt",
            "AI infrastructure spending", "stranded datacenter assets",
            "datacenter financing",
        ]),
    },
]


async def get_db() -> aiosqlite.Connection:
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_database(db: aiosqlite.Connection):
    await db.executescript(SCHEMA_SQL)
    await db.commit()


SEED_SOURCES = [
    # ── AI Job Displacement feeds ──
    {
        "name": "Google News — AI Layoffs & Job Displacement",
        "source_type": "rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%22AI+layoffs%22+OR+%22AI+replacing+jobs%22+OR+"
            "%22AI+automation+workforce%22+OR+%22AI+job+losses%22"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "name": "Google News — AI Workforce Reduction",
        "source_type": "rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%22workforce+reduction+AI%22+OR+%22AI+hiring+freeze%22+OR+"
            "%22white+collar+automation%22+OR+%22AI+headcount%22"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    # ── AI Deflation feeds ──
    {
        "name": "Google News — AI Deflation & Price Disruption",
        "source_type": "rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%22AI+deflation%22+OR+%22AI+price+disruption%22+OR+"
            "%22SaaS+AI+competition%22+OR+%22AI+cost+reduction%22"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "name": "Google News — AI Software Pricing Pressure",
        "source_type": "rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%22software+pricing+pressure+AI%22+OR+%22AI+margin+compression%22+OR+"
            "%22cheaper+AI+tools%22+OR+%22AI+disrupting+SaaS%22"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    # ── Datacenter Credit Crisis feeds ──
    {
        "name": "Google News — Datacenter Overbuilding & Credit",
        "source_type": "rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%22datacenter+overbuilding%22+OR+%22AI+capex%22+OR+"
            "%22datacenter+credit%22+OR+%22datacenter+debt%22"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "name": "Google News — GPU Obsolescence & Stranded Assets",
        "source_type": "rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%22GPU+obsolescence%22+OR+%22stranded+datacenter+assets%22+OR+"
            "%22AI+infrastructure+spending%22+OR+%22datacenter+financing%22"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    # ── Broad AI / Tech RSS feeds ──
    {
        "name": "TechCrunch — AI",
        "source_type": "rss",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "name": "Ars Technica — AI",
        "source_type": "rss",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    },
    {
        "name": "The Verge — AI",
        "source_type": "rss",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    },
]


async def seed_theses(db: aiosqlite.Connection):
    for thesis in SEED_THESES:
        await db.execute(
            """INSERT OR IGNORE INTO theses (id, name, description, keywords)
               VALUES (:id, :name, :description, :keywords)""",
            thesis,
        )
    await db.commit()


async def seed_sources(db: aiosqlite.Connection):
    """Seed default RSS sources if none exist yet."""
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM sources")
    row = await cursor.fetchone()
    if row["cnt"] > 0:
        return  # Already have sources configured, don't re-seed

    for source in SEED_SOURCES:
        await db.execute(
            """INSERT INTO sources (name, source_type, url, enabled)
               VALUES (:name, :source_type, :url, 1)""",
            source,
        )
    await db.commit()
