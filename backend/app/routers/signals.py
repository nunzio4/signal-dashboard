from datetime import datetime

from fastapi import APIRouter, Query, Request, HTTPException

from app.models import ManualSignalCreate, SignalResponse

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[SignalResponse])
async def list_signals(
    request: Request,
    thesis_id: str | None = None,
    direction: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    db = request.app.state.db
    conditions = []
    params: list = []

    if thesis_id:
        conditions.append("thesis_id = ?")
        params.append(thesis_id)
    if direction:
        conditions.append("direction = ?")
        params.append(direction)
    if date_from:
        conditions.append("signal_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("signal_date <= ?")
        params.append(date_to)

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""SELECT id, thesis_id, direction, strength, confidence,
                       evidence_quote, reasoning, source_title, source_url,
                       signal_date, is_manual, created_at
                FROM signals WHERE {where}
                ORDER BY signal_date DESC, created_at DESC
                LIMIT ? OFFSET ?"""
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return [
        SignalResponse(
            id=r["id"],
            thesis_id=r["thesis_id"],
            direction=r["direction"],
            strength=r["strength"],
            confidence=r["confidence"],
            evidence_quote=r["evidence_quote"],
            reasoning=r["reasoning"],
            source_title=r["source_title"],
            source_url=r["source_url"],
            signal_date=r["signal_date"],
            is_manual=bool(r["is_manual"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/manual", response_model=SignalResponse, status_code=201)
async def create_manual_signal(request: Request, body: ManualSignalCreate):
    db = request.app.state.db

    # Validate thesis exists
    cursor = await db.execute("SELECT id FROM theses WHERE id = ?", (body.thesis_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=400, detail=f"Unknown thesis_id: {body.thesis_id}")

    signal_date = body.signal_date or datetime.utcnow().strftime("%Y-%m-%d")

    cursor = await db.execute(
        """INSERT INTO signals
               (article_id, thesis_id, direction, strength, confidence,
                evidence_quote, reasoning, source_title, source_url,
                signal_date, is_manual)
           VALUES (NULL, ?, ?, ?, 1.0, ?, ?, ?, ?, ?, 1)""",
        (
            body.thesis_id,
            body.direction,
            body.strength,
            body.evidence_quote,
            body.reasoning,
            body.source_title,
            body.source_url,
            signal_date,
        ),
    )
    await db.commit()
    signal_id = cursor.lastrowid

    row = await (
        await db.execute(
            """SELECT id, thesis_id, direction, strength, confidence,
                      evidence_quote, reasoning, source_title, source_url,
                      signal_date, is_manual, created_at
               FROM signals WHERE id = ?""",
            (signal_id,),
        )
    ).fetchone()

    return SignalResponse(
        id=row["id"],
        thesis_id=row["thesis_id"],
        direction=row["direction"],
        strength=row["strength"],
        confidence=row["confidence"],
        evidence_quote=row["evidence_quote"],
        reasoning=row["reasoning"],
        source_title=row["source_title"],
        source_url=row["source_url"],
        signal_date=row["signal_date"],
        is_manual=bool(row["is_manual"]),
        created_at=row["created_at"],
    )


@router.delete("/{signal_id}", status_code=204)
async def delete_signal(request: Request, signal_id: int):
    db = request.app.state.db
    cursor = await db.execute("DELETE FROM signals WHERE id = ?", (signal_id,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Signal not found")
