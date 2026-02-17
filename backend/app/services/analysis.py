import json
import logging
import re
from datetime import datetime

import aiosqlite

from app.config import settings
from app.models import ArticleAnalysisResult
from app.prompts.signal_extraction import build_system_prompt, build_user_content

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def analyze_pending(self, batch_size: int = 10) -> dict:
        """Process pending articles through Claude for signal extraction."""
        if not settings.anthropic_api_key:
            logger.warning("Anthropic API key not configured, skipping analysis")
            return {"analyzed": 0, "skipped": 0, "errors": 0}

        # Lazy import to avoid issues when key is not set
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        # Fetch pending articles — title alone is enough (min 10 chars)
        cursor = await self.db.execute(
            """SELECT id, title, url, content, published_at
               FROM articles
               WHERE analysis_status = 'pending'
                 AND title IS NOT NULL AND LENGTH(title) > 10
               ORDER BY ingested_at ASC
               LIMIT ?""",
            (batch_size,),
        )
        articles = await cursor.fetchall()

        # Skip articles with no meaningful title
        skip_cursor = await self.db.execute(
            """UPDATE articles SET analysis_status = 'skipped'
               WHERE analysis_status = 'pending'
                 AND (title IS NULL OR LENGTH(title) <= 10)"""
        )
        await self.db.commit()

        theses_cursor = await self.db.execute(
            "SELECT id, name, description FROM theses"
        )
        theses = [dict(t) for t in await theses_cursor.fetchall()]

        stats = {"analyzed": 0, "skipped": skip_cursor.rowcount, "errors": 0}

        system_prompt = build_system_prompt(theses)

        for article in articles:
            try:
                user_content = build_user_content(dict(article))

                response = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                )

                # Parse response — handle both raw JSON and markdown-wrapped JSON
                text = response.content[0].text.strip()

                # Strip markdown code fences if present
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)

                result = ArticleAnalysisResult.model_validate_json(text)

                # Store relevant signals
                for signal in result.signals:
                    if not signal.is_relevant:
                        continue

                    signal_date = (article["published_at"] or "")[:10]
                    if not signal_date:
                        signal_date = datetime.utcnow().strftime("%Y-%m-%d")

                    await self.db.execute(
                        """INSERT INTO signals
                               (article_id, thesis_id, direction, strength,
                                confidence, evidence_quote, reasoning,
                                source_title, source_url, signal_date, is_manual)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                        (
                            article["id"],
                            signal.thesis_id,
                            signal.direction,
                            signal.strength,
                            signal.confidence,
                            signal.evidence_quote,
                            signal.reasoning,
                            article["title"],
                            article["url"],
                            signal_date,
                        ),
                    )

                await self.db.execute(
                    "UPDATE articles SET analysis_status = 'analyzed' WHERE id = ?",
                    (article["id"],),
                )
                await self.db.commit()
                stats["analyzed"] += 1
                logger.info(
                    f"Analyzed article {article['id']}: "
                    f"{sum(1 for s in result.signals if s.is_relevant)} signals found"
                )

            except Exception as e:
                logger.error(f"Error analyzing article {article['id']}: {e}")
                await self.db.execute(
                    "UPDATE articles SET analysis_status = 'error' WHERE id = ?",
                    (article["id"],),
                )
                await self.db.commit()
                stats["errors"] += 1

        return stats
