from fastapi import APIRouter, Query, Request

from app.models import ArticleResponse

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleResponse])
async def list_articles(
    request: Request,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    db = request.app.state.db
    conditions = []
    params: list = []

    if status:
        conditions.append("analysis_status = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""SELECT id, source_id, title, url, author,
                       published_at, ingested_at, analysis_status
                FROM articles WHERE {where}
                ORDER BY ingested_at DESC
                LIMIT ? OFFSET ?"""
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return [
        ArticleResponse(
            id=r["id"],
            source_id=r["source_id"],
            title=r["title"],
            url=r["url"],
            author=r["author"],
            published_at=r["published_at"],
            ingested_at=r["ingested_at"],
            analysis_status=r["analysis_status"],
        )
        for r in rows
    ]
