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
