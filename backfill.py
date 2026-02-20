"""
Historical backfill: fetch Google News articles from June 2025 – January 2026
and run Claude Haiku analysis to generate signals.

Usage:
    python backfill.py                   # fetch + analyze
    python backfill.py --fetch-only      # fetch articles only (no analysis)
    python backfill.py --analyze-only    # analyze pending articles only
"""

import asyncio
import hashlib
import logging
import re
import sys
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

import aiosqlite
import feedparser
import httpx

# ── Config ──

DB_PATH = "backend/data/signals.db"
START_MONTH = (2025, 6)   # June 2025
END_MONTH = (2026, 2)     # Up to (but not including) Feb 2026

# Same Google News queries as SEED_SOURCES in database.py
GOOGLE_NEWS_QUERIES = [
    # AI Job Displacement
    {
        "thesis_id": "ai_job_displacement",
        "name": "AI Layoffs & Job Displacement",
        "query": "%22AI+layoffs%22+OR+%22AI+replacing+jobs%22+OR+%22AI+automation+workforce%22+OR+%22AI+job+losses%22",
    },
    {
        "thesis_id": "ai_job_displacement",
        "name": "AI Workforce Reduction",
        "query": "%22workforce+reduction+AI%22+OR+%22AI+hiring+freeze%22+OR+%22white+collar+automation%22+OR+%22AI+headcount%22",
    },
    # AI Deflation
    {
        "thesis_id": "ai_deflation",
        "name": "AI Deflation & Price Disruption",
        "query": "%22AI+deflation%22+OR+%22AI+price+disruption%22+OR+%22SaaS+AI+competition%22+OR+%22AI+cost+reduction%22",
    },
    {
        "thesis_id": "ai_deflation",
        "name": "AI Software Pricing Pressure",
        "query": "%22software+pricing+pressure+AI%22+OR+%22AI+margin+compression%22+OR+%22cheaper+AI+tools%22+OR+%22AI+disrupting+SaaS%22",
    },
    # Datacenter Credit Crisis
    {
        "thesis_id": "datacenter_credit_crisis",
        "name": "Datacenter Overbuilding & Credit",
        "query": "%22datacenter+overbuilding%22+OR+%22AI+capex%22+OR+%22datacenter+credit%22+OR+%22datacenter+debt%22",
    },
    {
        "thesis_id": "datacenter_credit_crisis",
        "name": "GPU Obsolescence & Stranded Assets",
        "query": "%22GPU+obsolescence%22+OR+%22stranded+datacenter+assets%22+OR+%22AI+infrastructure+spending%22+OR+%22datacenter+financing%22",
    },
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill")


# ── Helpers ──

def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def compute_external_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def generate_months(start, end):
    """Yield (start_date, end_date) strings for each month in range."""
    y, m = start
    ey, em = end
    while (y, m) < (ey, em):
        start_date = f"{y}-{m:02d}-01"
        nm = m + 1 if m < 12 else 1
        ny = y if m < 12 else y + 1
        end_date = f"{ny}-{nm:02d}-01"
        yield start_date, end_date
        y, m = ny, nm


# ── Phase 1: Fetch ──

async def fetch_articles(db: aiosqlite.Connection):
    """Fetch historical articles from Google News RSS with date-range filtering."""
    log.info("=" * 60)
    log.info("PHASE 1: Fetching historical articles from Google News")
    log.info("=" * 60)

    # Get source IDs for linking (use first Google News source as fallback)
    source_cursor = await db.execute(
        "SELECT id, name FROM sources WHERE name LIKE '%Google News%' LIMIT 1"
    )
    source_row = await source_cursor.fetchone()
    default_source_id = source_row["id"] if source_row else None

    months = list(generate_months(START_MONTH, END_MONTH))
    total_new = 0
    total_dup = 0
    total_fetched = 0

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for qdef in GOOGLE_NEWS_QUERIES:
            query_new = 0
            log.info(f"\n  Query: {qdef['name']} ({qdef['thesis_id']})")

            for start_date, end_date in months:
                url = (
                    f"https://news.google.com/rss/search?"
                    f"q={qdef['query']}+after:{start_date}+before:{end_date}"
                    f"&hl=en-US&gl=US&ceid=US:en"
                )

                try:
                    resp = await client.get(
                        url, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    feed = feedparser.parse(resp.text)
                except Exception as e:
                    log.warning(f"    {start_date}: fetch error: {e}")
                    continue

                month_new = 0
                month_dup = 0

                for entry in feed.entries:
                    total_fetched += 1
                    title = strip_html(entry.get("title", ""))
                    link = entry.get("link", "")

                    if not title or len(title) <= 10:
                        continue

                    ext_id = compute_external_id(link or title)

                    # Check for duplicates
                    existing = await (
                        await db.execute(
                            "SELECT id FROM articles WHERE external_id = ?",
                            (ext_id,),
                        )
                    ).fetchone()
                    if existing:
                        month_dup += 1
                        total_dup += 1
                        continue

                    # Parse publish date
                    pub_date = None
                    if hasattr(entry, "published"):
                        try:
                            pub_date = parsedate_to_datetime(
                                entry.published
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pub_date = entry.published

                    summary = strip_html(
                        entry.get("summary", entry.get("description", ""))
                    )
                    content = f"{title}. {summary}" if summary else title

                    # Insert with ingested_at = published_at (so it looks historical)
                    ingested_at = pub_date or f"{start_date} 12:00:00"

                    await db.execute(
                        """INSERT INTO articles
                               (source_id, external_id, title, url, author,
                                content, published_at, ingested_at, analysis_status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                        (
                            default_source_id,
                            ext_id,
                            title,
                            link,
                            entry.get("author", ""),
                            content,
                            pub_date,
                            ingested_at,
                        ),
                    )
                    month_new += 1
                    query_new += 1
                    total_new += 1

                await db.commit()

                if month_new > 0 or month_dup > 0:
                    log.info(
                        f"    {start_date[:7]}: {month_new} new, {month_dup} dup"
                    )

                # Rate limiting: be polite to Google
                await asyncio.sleep(0.4)

            log.info(f"    Subtotal: {query_new} new articles")

    log.info(f"\nFetch complete: {total_new} new, {total_dup} duplicates, {total_fetched} total parsed")
    return total_new


# ── Phase 2: Analyze ──

async def analyze_articles(db: aiosqlite.Connection):
    """Run Claude Haiku analysis on all pending articles."""
    log.info("=" * 60)
    log.info("PHASE 2: Analyzing pending articles with Claude Haiku")
    log.info("=" * 60)

    # Check how many pending
    cur = await db.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE analysis_status = 'pending' AND LENGTH(title) > 10"
    )
    pending = (await cur.fetchone())["cnt"]
    log.info(f"Pending articles to analyze: {pending}")

    if pending == 0:
        log.info("Nothing to analyze!")
        return

    # Import the analysis service (needs app config for API key)
    sys.path.insert(0, "backend")
    from app.services.analysis import AnalysisService

    svc = AnalysisService(db)

    analyzed_total = 0
    errors_total = 0
    batch_num = 0
    batch_size = 10

    while True:
        batch_num += 1
        log.info(f"\n  Batch {batch_num} (articles {analyzed_total + 1}–{analyzed_total + batch_size})...")

        stats = await svc.analyze_pending(batch_size=batch_size)

        analyzed_total += stats["analyzed"]
        errors_total += stats["errors"]

        log.info(
            f"    Analyzed: {stats['analyzed']}, "
            f"Errors: {stats['errors']}, "
            f"Skipped: {stats['skipped']} "
            f"(total so far: {analyzed_total}/{pending})"
        )

        # Stop if no more pending articles
        if stats["analyzed"] == 0 and stats["errors"] == 0:
            break

        # Small delay between batches to avoid rate limits
        await asyncio.sleep(1.0)

    log.info(f"\nAnalysis complete: {analyzed_total} analyzed, {errors_total} errors")


# ── Phase 3: Regenerate scores ──

async def regenerate_scores(db: aiosqlite.Connection):
    """Recompute daily scores after backfill."""
    log.info("=" * 60)
    log.info("PHASE 3: Regenerating daily scores")
    log.info("=" * 60)

    sys.path.insert(0, "backend")
    from app.services.aggregation import AggregationService

    svc = AggregationService(db)
    await svc.compute_daily_scores()
    log.info("Daily scores regenerated")


# ── Main ──

async def main():
    fetch_only = "--fetch-only" in sys.argv
    analyze_only = "--analyze-only" in sys.argv

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    try:
        if not analyze_only:
            new_count = await fetch_articles(db)
        else:
            new_count = None

        if not fetch_only:
            await analyze_articles(db)
            await regenerate_scores(db)

        # Summary
        cur = await db.execute("SELECT COUNT(*) as cnt FROM articles")
        total_articles = (await cur.fetchone())["cnt"]
        cur = await db.execute("SELECT COUNT(*) as cnt FROM signals")
        total_signals = (await cur.fetchone())["cnt"]
        cur = await db.execute(
            "SELECT MIN(published_at) as mn, MAX(published_at) as mx FROM articles WHERE published_at IS NOT NULL"
        )
        row = await cur.fetchone()

        log.info("\n" + "=" * 60)
        log.info("BACKFILL COMPLETE")
        log.info(f"  Total articles: {total_articles}")
        log.info(f"  Total signals:  {total_signals}")
        log.info(f"  Date range:     {row['mn'][:10] if row['mn'] else '?'} to {row['mx'][:10] if row['mx'] else '?'}")
        log.info("=" * 60)

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
