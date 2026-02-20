"""
Lightweight visitor analytics.

Records page views via a tracking pixel/endpoint and exposes an
hourly digest endpoint (admin-only via API key).
"""

import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _visitor_hash(ip: str, user_agent: str) -> str:
    """Create a privacy-friendly visitor ID from IP + UA (not reversible)."""
    raw = f"{ip}|{user_agent}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _extract_domain(referer: str) -> str:
    """Extract the domain from a referer URL (e.g. 'https://www.linkedin.com/feed' -> 'linkedin.com')."""
    if not referer:
        return ""
    try:
        host = urlparse(referer).hostname or ""
        # Strip 'www.' prefix for cleaner grouping
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


@router.get("/pixel")
async def tracking_pixel(request: Request, path: str = "/"):
    """1x1 transparent GIF tracking pixel. Called by the frontend on every page load."""
    db = request.app.state.db
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    referer = request.headers.get("referer", "")
    visitor_id = _visitor_hash(ip, ua)

    referer_domain = _extract_domain(referer)

    await db.execute(
        """INSERT INTO page_views (visitor_id, ip_addr, path, user_agent, referer, referer_domain)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (visitor_id, ip, path, ua[:500], referer[:500], referer_domain),
    )
    await db.commit()

    # Return a 1x1 transparent GIF
    gif = (
        b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
        b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00"
        b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
        b"\x44\x01\x00\x3b"
    )
    return Response(
        content=gif,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@router.get("/digest")
async def analytics_digest(
    request: Request,
    hours: int = Query(default=1, ge=1, le=720),
):
    """
    Get visitor analytics digest for the past N hours.
    Requires admin API key (enforced by middleware for GET on /analytics/digest).
    """
    db = request.app.state.db
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

    # Unique visitors in the window
    uv_cursor = await db.execute(
        "SELECT COUNT(DISTINCT visitor_id) as cnt FROM page_views WHERE created_at >= ?",
        (cutoff,),
    )
    unique_visitors = (await uv_cursor.fetchone())["cnt"]

    # Total page views in the window
    pv_cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM page_views WHERE created_at >= ?",
        (cutoff,),
    )
    total_views = (await pv_cursor.fetchone())["cnt"]

    # Top pages
    top_pages_cursor = await db.execute(
        """SELECT path, COUNT(*) as views, COUNT(DISTINCT visitor_id) as visitors
           FROM page_views WHERE created_at >= ?
           GROUP BY path ORDER BY views DESC LIMIT 10""",
        (cutoff,),
    )
    top_pages = [
        {"path": r["path"], "views": r["views"], "visitors": r["visitors"]}
        for r in await top_pages_cursor.fetchall()
    ]

    # Top referrer domains (e.g. linkedin.com, google.com)
    domain_cursor = await db.execute(
        """SELECT referer_domain as domain, COUNT(*) as views,
                  COUNT(DISTINCT visitor_id) as visitors
           FROM page_views WHERE created_at >= ? AND referer_domain != ''
           GROUP BY referer_domain ORDER BY visitors DESC LIMIT 10""",
        (cutoff,),
    )
    top_referrer_domains = [
        {"domain": r["domain"], "views": r["views"], "visitors": r["visitors"]}
        for r in await domain_cursor.fetchall()
    ]

    # Top referrer URLs (full URLs for detail)
    ref_cursor = await db.execute(
        """SELECT referer, COUNT(DISTINCT visitor_id) as visitors
           FROM page_views WHERE created_at >= ? AND referer != ''
           GROUP BY referer ORDER BY visitors DESC LIMIT 10""",
        (cutoff,),
    )
    top_referrer_urls = [
        {"url": r["referer"], "visitors": r["visitors"]}
        for r in await ref_cursor.fetchall()
    ]

    # Hourly breakdown (for multi-hour windows)
    hourly_cursor = await db.execute(
        """SELECT strftime('%%Y-%%m-%%d %%H:00', created_at) as hour,
                  COUNT(*) as views,
                  COUNT(DISTINCT visitor_id) as visitors
           FROM page_views WHERE created_at >= ?
           GROUP BY hour ORDER BY hour""",
        (cutoff,),
    )
    hourly = [
        {"hour": r["hour"], "views": r["views"], "visitors": r["visitors"]}
        for r in await hourly_cursor.fetchall()
    ]

    # All-time stats
    all_cursor = await db.execute(
        "SELECT COUNT(DISTINCT visitor_id) as uv, COUNT(*) as pv FROM page_views"
    )
    all_row = await all_cursor.fetchone()

    return {
        "period_hours": hours,
        "cutoff": cutoff,
        "unique_visitors": unique_visitors,
        "total_views": total_views,
        "top_pages": top_pages,
        "top_referrer_domains": top_referrer_domains,
        "top_referrer_urls": top_referrer_urls,
        "hourly_breakdown": hourly,
        "all_time": {
            "unique_visitors": all_row["uv"],
            "total_views": all_row["pv"],
        },
    }
