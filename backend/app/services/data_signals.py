"""
Generate signals from data series changes.

Compares the two most recent data points for each series, computes percent
change, and creates a signal whose direction is determined by the series'
direction_logic field.
"""
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)


def _pct_to_strength(pct_change: float) -> int:
    """Map absolute percent change to signal strength (1-10)."""
    abs_pct = abs(pct_change)
    if abs_pct < 1:
        return 3
    if abs_pct < 3:
        return 5
    if abs_pct < 5:
        return 6
    if abs_pct < 10:
        return 7
    if abs_pct < 20:
        return 8
    return 9


def _format_value(value: float, unit: str) -> str:
    """Format a numeric value with appropriate precision for display."""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


class DataSignalGenerator:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def generate_all(self) -> dict:
        """Generate data signals for all enabled data series."""
        cursor = await self.db.execute(
            """SELECT ds.id, ds.name, ds.thesis_id, ds.direction_logic, ds.unit,
                      t.name as thesis_name
               FROM data_series ds
               JOIN theses t ON t.id = ds.thesis_id
               WHERE ds.enabled = 1"""
        )
        series_list = await cursor.fetchall()

        stats = {"generated": 0, "skipped_no_data": 0, "skipped_duplicate": 0, "errors": 0}

        for series in series_list:
            try:
                created = await self._generate_for_series(series)
                if created is None:
                    stats["skipped_no_data"] += 1
                elif created:
                    stats["generated"] += 1
                else:
                    stats["skipped_duplicate"] += 1
            except Exception as e:
                logger.error(f"Error generating data signal for {series['id']}: {e}")
                stats["errors"] += 1

        await self.db.commit()
        logger.info(f"Data signal generation complete: {stats}")
        return stats

    async def _generate_for_series(self, series) -> bool | None:
        """Generate a signal for one data series.

        Returns:
            True  — signal created
            False — skipped (duplicate)
            None  — skipped (not enough data)
        """
        # Get the two most recent data points
        dp_cursor = await self.db.execute(
            """SELECT id, date, value
               FROM data_points
               WHERE series_id = ?
               ORDER BY date DESC
               LIMIT 2""",
            (series["id"],),
        )
        points = await dp_cursor.fetchall()

        if len(points) < 2:
            return None  # Need at least 2 data points to compute change

        latest = points[0]
        previous = points[1]

        # Check if we already generated a signal for this data point
        dup_cursor = await self.db.execute(
            "SELECT id FROM signals WHERE data_point_id = ?",
            (latest["id"],),
        )
        if await dup_cursor.fetchone():
            return False  # Already processed

        # Compute percent change
        prev_val = previous["value"]
        latest_val = latest["value"]
        if prev_val == 0:
            pct_change = 0.0
        else:
            pct_change = ((latest_val - prev_val) / abs(prev_val)) * 100

        # Determine direction based on direction_logic
        value_increased = latest_val > prev_val
        direction_logic = series["direction_logic"]

        if direction_logic == "higher_supporting":
            direction = "supporting" if value_increased else "weakening"
        else:  # lower_supporting
            direction = "supporting" if not value_increased else "weakening"

        strength = _pct_to_strength(pct_change)
        confidence = 0.8

        # Build human-readable evidence quote and reasoning
        series_name = series["name"]
        unit = series["unit"] or ""
        prev_fmt = _format_value(prev_val, unit)
        latest_fmt = _format_value(latest_val, unit)
        change_word = "increased" if value_increased else "decreased"
        sign = "+" if pct_change >= 0 else ""

        evidence_quote = (
            f"{series_name} {change_word} from {prev_fmt} to {latest_fmt} "
            f"({sign}{pct_change:.1f}%)"
        )
        if unit:
            evidence_quote = (
                f"{series_name} {change_word} from {prev_fmt} to {latest_fmt} {unit} "
                f"({sign}{pct_change:.1f}%)"
            )

        thesis_name = series["thesis_name"]
        if direction == "supporting":
            reasoning = f"{change_word.capitalize()} {series_name.lower()} supports the {thesis_name} thesis."
        else:
            reasoning = f"{change_word.capitalize()} {series_name.lower()} weakens the {thesis_name} thesis."

        await self.db.execute(
            """INSERT INTO signals
                   (article_id, thesis_id, direction, strength, confidence,
                    evidence_quote, reasoning, source_title, source_url,
                    signal_date, is_manual, signal_type, data_point_id)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, 'data', ?)""",
            (
                series["thesis_id"],
                direction,
                strength,
                confidence,
                evidence_quote,
                reasoning,
                series_name,
                latest["date"],
                latest["id"],
            ),
        )
        logger.info(
            f"Data signal: {series_name} → {direction} (str={strength}, "
            f"{sign}{pct_change:.1f}%) for {thesis_name}"
        )
        return True
