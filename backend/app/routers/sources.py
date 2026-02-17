from fastapi import APIRouter, Request, HTTPException

from app.models import SourceCreate, SourceUpdate, SourceResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(request: Request):
    db = request.app.state.db
    cursor = await db.execute(
        """SELECT id, name, source_type, url, config, enabled,
                  last_fetched_at, created_at
           FROM sources ORDER BY created_at DESC"""
    )
    rows = await cursor.fetchall()
    return [
        SourceResponse(
            id=r["id"],
            name=r["name"],
            source_type=r["source_type"],
            url=r["url"],
            config=r["config"],
            enabled=bool(r["enabled"]),
            last_fetched_at=r["last_fetched_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(request: Request, body: SourceCreate):
    db = request.app.state.db
    cursor = await db.execute(
        """INSERT INTO sources (name, source_type, url, config, enabled)
           VALUES (?, ?, ?, ?, ?)""",
        (body.name, body.source_type, body.url, body.config, int(body.enabled)),
    )
    await db.commit()
    source_id = cursor.lastrowid

    row = await (
        await db.execute(
            """SELECT id, name, source_type, url, config, enabled,
                      last_fetched_at, created_at
               FROM sources WHERE id = ?""",
            (source_id,),
        )
    ).fetchone()

    return SourceResponse(
        id=row["id"],
        name=row["name"],
        source_type=row["source_type"],
        url=row["url"],
        config=row["config"],
        enabled=bool(row["enabled"]),
        last_fetched_at=row["last_fetched_at"],
        created_at=row["created_at"],
    )


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(request: Request, source_id: int, body: SourceUpdate):
    db = request.app.state.db

    existing = await (
        await db.execute("SELECT id FROM sources WHERE id = ?", (source_id,))
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")

    updates = []
    params: list = []
    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name)
    if body.url is not None:
        updates.append("url = ?")
        params.append(body.url)
    if body.config is not None:
        updates.append("config = ?")
        params.append(body.config)
    if body.enabled is not None:
        updates.append("enabled = ?")
        params.append(int(body.enabled))

    if updates:
        params.append(source_id)
        await db.execute(
            f"UPDATE sources SET {', '.join(updates)} WHERE id = ?", params
        )
        await db.commit()

    row = await (
        await db.execute(
            """SELECT id, name, source_type, url, config, enabled,
                      last_fetched_at, created_at
               FROM sources WHERE id = ?""",
            (source_id,),
        )
    ).fetchone()

    return SourceResponse(
        id=row["id"],
        name=row["name"],
        source_type=row["source_type"],
        url=row["url"],
        config=row["config"],
        enabled=bool(row["enabled"]),
        last_fetched_at=row["last_fetched_at"],
        created_at=row["created_at"],
    )


@router.delete("/{source_id}", status_code=204)
async def delete_source(request: Request, source_id: int):
    db = request.app.state.db
    cursor = await db.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Source not found")
