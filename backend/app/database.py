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

CREATE TABLE IF NOT EXISTS data_series (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    thesis_id       TEXT NOT NULL REFERENCES theses(id),
    provider        TEXT NOT NULL,
    series_config   TEXT NOT NULL,
    unit            TEXT NOT NULL DEFAULT '',
    direction_logic TEXT NOT NULL DEFAULT 'higher_supporting',
    enabled         INTEGER NOT NULL DEFAULT 1,
    last_fetched_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS data_points (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id       TEXT NOT NULL REFERENCES data_series(id),
    date            TEXT NOT NULL,
    value           REAL NOT NULL,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(series_id, date)
);

CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(analysis_status);
CREATE INDEX IF NOT EXISTS idx_articles_external_id ON articles(external_id);
CREATE INDEX IF NOT EXISTS idx_signals_thesis ON signals(thesis_id, signal_date);
CREATE INDEX IF NOT EXISTS idx_signals_article ON signals(article_id);
CREATE INDEX IF NOT EXISTS idx_daily_scores_thesis_date ON daily_scores(thesis_id, score_date);
CREATE INDEX IF NOT EXISTS idx_data_points_series_date ON data_points(series_id, date);
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


SEED_DATA_SERIES = [
    # ═══ AI Job Displacement ═══
    {
        "id": "fred_jolts",
        "name": "JOLTS Job Openings",
        "description": "Total nonfarm job openings (thousands). Declining openings = fewer jobs available.",
        "thesis_id": "ai_job_displacement",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "JTSJOL"}),
        "unit": "Thousands",
        "direction_logic": "lower_supporting",
    },
    {
        "id": "fred_jobless_claims",
        "name": "Initial Jobless Claims",
        "description": "Weekly initial unemployment insurance claims. Rising claims = more job losses.",
        "thesis_id": "ai_job_displacement",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "ICSA"}),
        "unit": "Claims",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "fred_indeed_us",
        "name": "Indeed Job Postings (US)",
        "description": "Indeed job postings index (Feb 2020 = 100). Declining index = less hiring.",
        "thesis_id": "ai_job_displacement",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "IHLIDXUS"}),
        "unit": "Index",
        "direction_logic": "lower_supporting",
    },
    {
        "id": "fred_indeed_software",
        "name": "Indeed Software Dev Postings",
        "description": "Software development job postings index. Declining = AI replacing dev jobs.",
        "thesis_id": "ai_job_displacement",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "IHLIDXUSTPSOFTDEVE"}),
        "unit": "Index",
        "direction_logic": "lower_supporting",
    },
    {
        "id": "bls_info_employment",
        "name": "Information Sector Employment",
        "description": "Total employees in the Information sector (NAICS 51). Declining = thesis supporting.",
        "thesis_id": "ai_job_displacement",
        "provider": "bls",
        "series_config": json.dumps({"series_id": "CES5000000001"}),
        "unit": "Thousands",
        "direction_logic": "lower_supporting",
    },
    # ═══ AI Deflation ═══
    {
        "id": "fred_cpi_it",
        "name": "CPI: IT Hardware & Services",
        "description": "Consumer price index for information technology. Falling prices = deflationary.",
        "thesis_id": "ai_deflation",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "CUSR0000SEEE"}),
        "unit": "Index",
        "direction_logic": "lower_supporting",
    },
    {
        "id": "fred_ppi_data_hosting",
        "name": "PPI: Data Processing & Hosting",
        "description": "Producer price index for data processing/hosting services. Falling = deflation.",
        "thesis_id": "ai_deflation",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "PCU518210518210"}),
        "unit": "Index",
        "direction_logic": "lower_supporting",
    },
    {
        "id": "fred_pce_info_processing",
        "name": "Private Investment: IT Equipment",
        "description": "Private fixed investment in information processing equipment (billions $). Shifts in spending.",
        "thesis_id": "ai_deflation",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "A679RC1Q027SBEA"}),
        "unit": "Billions $",
        "direction_logic": "lower_supporting",
    },
    # ═══ Datacenter Credit Crisis ═══
    {
        "id": "fred_construction_commercial",
        "name": "Commercial Construction Spending",
        "description": "Total commercial construction spending (millions $). Parabolic growth = overbuilding.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "TLCOMCONS"}),
        "unit": "Millions $",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "fred_corp_spreads",
        "name": "Corporate Bond Spreads (IG)",
        "description": "ICE BofA US Corporate index option-adjusted spread. Widening = credit stress.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "BAMLC0A0CM"}),
        "unit": "% Spread",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "fred_hy_spreads",
        "name": "High Yield Bond Spreads",
        "description": "ICE BofA US High Yield index spread. Widening = credit risk increasing.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "BAMLH0A0HYM2"}),
        "unit": "% Spread",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "fred_sloos",
        "name": "Bank Lending Standards (SLOOS)",
        "description": "Net % of banks tightening C&I loan standards. Rising = tighter credit.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "fred",
        "series_config": json.dumps({"series_id": "DRTSCILM"}),
        "unit": "Net %",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "edgar_msft_capex",
        "name": "Microsoft Capex",
        "description": "Microsoft quarterly capital expenditures from 10-Q filings.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "sec_edgar",
        "series_config": json.dumps({"cik": "0000789019", "ticker": "MSFT"}),
        "unit": "$ Billions",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "edgar_goog_capex",
        "name": "Alphabet Capex",
        "description": "Alphabet/Google quarterly capital expenditures from 10-Q filings.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "sec_edgar",
        "series_config": json.dumps({"cik": "0001652044", "ticker": "GOOG"}),
        "unit": "$ Billions",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "edgar_amzn_capex",
        "name": "Amazon Capex",
        "description": "Amazon quarterly capital expenditures from 10-Q filings.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "sec_edgar",
        "series_config": json.dumps({"cik": "0001018724", "ticker": "AMZN"}),
        "unit": "$ Billions",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "edgar_meta_capex",
        "name": "Meta Capex",
        "description": "Meta Platforms quarterly capital expenditures from 10-Q filings.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "sec_edgar",
        "series_config": json.dumps({"cik": "0001326801", "ticker": "META"}),
        "unit": "$ Billions",
        "direction_logic": "higher_supporting",
    },
    {
        "id": "edgar_nvda_capex",
        "name": "NVIDIA Capex",
        "description": "NVIDIA quarterly capital expenditures from 10-Q filings.",
        "thesis_id": "datacenter_credit_crisis",
        "provider": "sec_edgar",
        "series_config": json.dumps({"cik": "0001045810", "ticker": "NVDA"}),
        "unit": "$ Billions",
        "direction_logic": "higher_supporting",
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


async def seed_data_series(db: aiosqlite.Connection):
    """Seed default data series definitions if none exist yet."""
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM data_series")
    row = await cursor.fetchone()
    if row["cnt"] > 0:
        return

    for series in SEED_DATA_SERIES:
        await db.execute(
            """INSERT OR IGNORE INTO data_series
               (id, name, description, thesis_id, provider, series_config, unit, direction_logic)
               VALUES (:id, :name, :description, :thesis_id, :provider, :series_config, :unit, :direction_logic)""",
            series,
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
