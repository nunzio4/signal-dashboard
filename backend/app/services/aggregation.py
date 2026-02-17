import math
from datetime import datetime, timedelta

import aiosqlite


class AggregationService:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def compute_daily_scores(self):
        """Recompute composite scores for all theses for today."""
        cursor = await self.db.execute("SELECT id FROM theses")
        theses = await cursor.fetchall()
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for thesis in theses:
            result = await self._compute_score(thesis["id"], today)
            await self.db.execute(
                """INSERT INTO daily_scores
                       (thesis_id, score_date, composite_score,
                        signal_count, supporting_count, weakening_count)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(thesis_id, score_date) DO UPDATE SET
                       composite_score = excluded.composite_score,
                       signal_count = excluded.signal_count,
                       supporting_count = excluded.supporting_count,
                       weakening_count = excluded.weakening_count,
                       computed_at = datetime('now')""",
                (
                    thesis["id"],
                    today,
                    result["composite_score"],
                    result["signal_count"],
                    result["supporting_count"],
                    result["weakening_count"],
                ),
            )
        await self.db.commit()

    async def _compute_score(self, thesis_id: str, as_of_date: str) -> dict:
        """
        Confidence-weighted exponential decay scoring over 30-day window.

        Each signal contributes:
            signed_value = strength * confidence * decay * direction_sign
        where direction_sign = +1 supporting, -1 weakening
              decay = exp(-0.05 * days_ago) with ~14 day half-life

        Result is rescaled from [-10, +10] to [1, 10] gauge range.
        """
        cutoff = (
            datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=30)
        ).strftime("%Y-%m-%d")

        cursor = await self.db.execute(
            """SELECT direction, strength, confidence, signal_date
               FROM signals
               WHERE thesis_id = ? AND signal_date >= ? AND signal_date <= ?""",
            (thesis_id, cutoff, as_of_date),
        )
        signals = await cursor.fetchall()

        if not signals:
            return {
                "composite_score": 5.0,
                "signal_count": 0,
                "supporting_count": 0,
                "weakening_count": 0,
            }

        weighted_sum = 0.0
        weight_total = 0.0
        supporting_count = 0
        weakening_count = 0

        ref_date = datetime.strptime(as_of_date, "%Y-%m-%d")

        for sig in signals:
            sig_date = datetime.strptime(sig["signal_date"][:10], "%Y-%m-%d")
            days_ago = max((ref_date - sig_date).days, 0)
            decay = math.exp(-0.05 * days_ago)
            weight = sig["confidence"] * decay
            direction_sign = 1.0 if sig["direction"] == "supporting" else -1.0

            weighted_sum += sig["strength"] * weight * direction_sign
            weight_total += weight

            if sig["direction"] == "supporting":
                supporting_count += 1
            else:
                weakening_count += 1

        if weight_total > 0:
            raw_score = weighted_sum / weight_total
        else:
            raw_score = 0.0

        # Map [-10, +10] to [1, 10]: -10→1, 0→5.5, +10→10
        composite = 5.5 + (raw_score * 4.5 / 10.0)
        composite = max(1.0, min(10.0, round(composite, 2)))

        return {
            "composite_score": composite,
            "signal_count": supporting_count + weakening_count,
            "supporting_count": supporting_count,
            "weakening_count": weakening_count,
        }

    async def get_trend_data(
        self, thesis_id: str, days: int = 30
    ) -> list[dict]:
        """Get daily composite scores for trend chart."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor = await self.db.execute(
            """SELECT score_date, composite_score, signal_count
               FROM daily_scores
               WHERE thesis_id = ? AND score_date >= ?
               ORDER BY score_date ASC""",
            (thesis_id, cutoff),
        )
        rows = await cursor.fetchall()
        return [
            {
                "date": row["score_date"],
                "score": row["composite_score"],
                "count": row["signal_count"],
            }
            for row in rows
        ]

    async def get_current_score(self, thesis_id: str) -> float:
        """Get the latest composite score for a thesis."""
        cursor = await self.db.execute(
            """SELECT composite_score FROM daily_scores
               WHERE thesis_id = ?
               ORDER BY score_date DESC LIMIT 1""",
            (thesis_id,),
        )
        row = await cursor.fetchone()
        return row["composite_score"] if row else 5.0

    async def get_previous_score(self, thesis_id: str) -> float | None:
        """Get the composite score from yesterday."""
        cursor = await self.db.execute(
            """SELECT composite_score FROM daily_scores
               WHERE thesis_id = ?
               ORDER BY score_date DESC LIMIT 1 OFFSET 1""",
            (thesis_id,),
        )
        row = await cursor.fetchone()
        return row["composite_score"] if row else None

    @staticmethod
    def compute_trend_direction(trend_data: list[dict], window: int = 7) -> str:
        """Compare recent window avg to prior window avg."""
        scores = [p["score"] for p in trend_data]
        if len(scores) < window * 2:
            return "stable"
        recent = sum(scores[-window:]) / window
        prior = sum(scores[-window * 2 : -window]) / window
        delta = recent - prior
        if delta > 0.5:
            return "rising"
        elif delta < -0.5:
            return "falling"
        return "stable"
