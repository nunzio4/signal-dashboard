"""Create a clean seed database with just the data we need for production."""
import sqlite3
import shutil
from pathlib import Path

src_db = "backend/data/signals.db"
seed_db = "backend/seed.db"

# Remove old seed if exists
Path(seed_db).unlink(missing_ok=True)

# Checkpoint WAL so all pending writes are flushed to the main DB file
src_conn = sqlite3.connect(src_db)
src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
src_conn.close()
print("WAL checkpoint complete")

# Copy the entire database
shutil.copy2(src_db, seed_db)

# Now open it and clean up
conn = sqlite3.connect(seed_db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Disable foreign keys so we can safely remove unreferenced articles
cur.execute("PRAGMA foreign_keys=OFF")

# Remove articles that have no signals AND are not pending analysis
cur.execute("SELECT COUNT(*) FROM articles")
total_articles = cur.fetchone()[0]

cur.execute("""DELETE FROM articles
               WHERE id NOT IN (SELECT DISTINCT article_id FROM signals WHERE article_id IS NOT NULL)
                 AND analysis_status != 'pending'""")
deleted = cur.rowcount
print(f"Removed {deleted} unreferenced articles (kept {total_articles - deleted})")

# Reset analysis status on kept articles
cur.execute("UPDATE articles SET analysis_status = 'analyzed'")

# Normalize timestamps so bulk-import artifacts don't inflate "Past 24h" counts.
# Only normalize OLD records (>7 days); preserve recent created_at/ingested_at
# so that 24h counts are accurate immediately after deploy.
# - data_points.fetched_at → always use observation date (bulk fetch artifact)
# - articles.ingested_at  → only normalize old articles (>7 days)
# - signals.created_at    → only normalize old signals  (>7 days)
cur.execute("UPDATE data_points SET fetched_at = date || ' 12:00:00' WHERE date IS NOT NULL")
print("Normalized data_points.fetched_at to observation dates")

cur.execute("""UPDATE articles SET ingested_at = published_at
WHERE published_at IS NOT NULL AND published_at < datetime('now', '-7 days')""")
n = cur.rowcount
print(f"Normalized {n} old articles ingested_at (preserved recent 7 days)")

cur.execute("""UPDATE signals SET created_at = signal_date || ' 12:00:00'
WHERE signal_date IS NOT NULL AND created_at < datetime('now', '-7 days')""")
n = cur.rowcount
print(f"Normalized {n} old signals created_at (preserved recent 7 days)")

# Print summary
for table in ["theses", "sources", "data_series", "articles", "signals", "daily_scores", "data_points"]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"  {table}: {count} rows")

# Vacuum to shrink the file
conn.commit()
cur.execute("VACUUM")
conn.close()

size_kb = Path(seed_db).stat().st_size // 1024
print(f"\nSeed database: {seed_db} ({size_kb} KB)")
