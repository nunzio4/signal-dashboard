import hashlib
import json
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

import feedparser
import httpx
import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)


def strip_html(text: str) -> str:
    """Remove HTML tags, decode entities, and clean up whitespace."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    clean = unescape(clean)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class IngestionService:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def run_full_ingestion(self) -> dict:
        """Fetch all enabled sources, dedupe, store new articles."""
        cursor = await self.db.execute(
            "SELECT id, name, source_type, url, config FROM sources WHERE enabled = 1"
        )
        sources = await cursor.fetchall()

        stats = {"fetched": 0, "new": 0, "duplicate": 0, "errors": 0}

        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True
        ) as client:
            for source in sources:
                try:
                    if source["source_type"] == "rss":
                        articles = await self._fetch_rss(client, source)
                    elif source["source_type"] == "newsapi":
                        articles = await self._fetch_newsapi(client, source)
                    else:
                        continue

                    for article in articles:
                        stats["fetched"] += 1
                        ext_id = self._compute_external_id(
                            article.get("url", article["title"])
                        )

                        existing = await (
                            await self.db.execute(
                                "SELECT id FROM articles WHERE external_id = ?",
                                (ext_id,),
                            )
                        ).fetchone()

                        if existing:
                            stats["duplicate"] += 1
                            continue

                        await self.db.execute(
                            """INSERT INTO articles
                                   (source_id, external_id, title, url, author,
                                    content, published_at, analysis_status)
                               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                            (
                                source["id"],
                                ext_id,
                                article["title"],
                                article.get("url"),
                                article.get("author"),
                                article.get("content", ""),
                                article.get("published_at"),
                            ),
                        )
                        stats["new"] += 1

                    await self.db.execute(
                        "UPDATE sources SET last_fetched_at = datetime('now') WHERE id = ?",
                        (source["id"],),
                    )
                    await self.db.commit()

                except Exception as e:
                    logger.error(f"Error fetching source {source['name']}: {e}")
                    stats["errors"] += 1

        return stats

    async def _fetch_rss(
        self, client: httpx.AsyncClient, source: dict
    ) -> list[dict]:
        response = await client.get(source["url"])
        feed = feedparser.parse(response.text)
        articles = []
        for entry in feed.entries:
            pub_date = None
            if hasattr(entry, "published"):
                try:
                    pub_date = parsedate_to_datetime(entry.published).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    pub_date = entry.published

            title = strip_html(entry.get("title", ""))
            summary = strip_html(
                entry.get("summary", entry.get("description", ""))
            )

            # Combine title + summary for richer content for analysis
            content = f"{title}. {summary}" if summary else title

            articles.append(
                {
                    "title": title,
                    "url": entry.get("link", ""),
                    "author": entry.get("author", ""),
                    "content": content,
                    "published_at": pub_date,
                }
            )
        return articles

    async def _fetch_newsapi(
        self, client: httpx.AsyncClient, source: dict
    ) -> list[dict]:
        if not settings.newsapi_key:
            logger.warning("NewsAPI key not configured, skipping source")
            return []

        config = json.loads(source["config"]) if source["config"] else {}
        params = {
            "q": config.get("query", ""),
            "apiKey": settings.newsapi_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
        }
        response = await client.get(
            "https://newsapi.org/v2/everything", params=params
        )
        data = response.json()

        return [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "author": a.get("author", ""),
                "content": a.get("content", a.get("description", "")),
                "published_at": a.get("publishedAt"),
            }
            for a in data.get("articles", [])
        ]

    @staticmethod
    def _compute_external_id(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:32]
