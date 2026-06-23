"""Community endpoints — gamification, neighbor alerts, community notes."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import Annotated

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.community import CommunityNote, NoteUpvote
from app.models.user import User
from app.services.gamification_service import (
    get_leaderboard,
    get_user_stats,
)

router = APIRouter(prefix="/community", tags=["Community"])

NoteBody = Annotated[str, StringConstraints(min_length=1, max_length=280)]


# ── Gamification ──────────────────────────────────────────────────────────────

@router.get("/stats/me")
async def my_stats(current_user: User = Depends(get_current_user)):
    """Return current user's points, badges, level and streaks."""
    return await get_user_stats(current_user.id)


@router.get("/leaderboard")
async def leaderboard(
    country_code: str = Query(..., description="ISO country code e.g. RW, KE"),
    period: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    limit: int = Query(default=20, ge=5, le=50),
):
    """Return the top reporters leaderboard for a country."""
    return await get_leaderboard(country_code, period=period, limit=limit)


# ── Community Notes ───────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    h3_index: str
    body: NoteBody


class NoteOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    body: str
    upvotes: int
    created_at: datetime
    expires_at: datetime
    is_mine: bool = False

    model_config = {"from_attributes": True}


@router.post("/notes", response_model=NoteOut, status_code=201)
async def add_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a community note to an active outage area. Expires in 24 hours."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    note = CommunityNote(
        user_id=current_user.id,
        h3_index=payload.h3_index,
        body=payload.body.strip(),
        expires_at=expires_at,
    )
    db.add(note)
    await db.flush()

    # Award points for contributing a note
    from app.services.gamification_service import award_points
    await award_points(current_user.id, "add_note", str(note.id), db)

    result = NoteOut.model_validate(note)
    result.is_mine = True
    return result


@router.get("/notes/{h3_index}", response_model=List[NoteOut])
async def get_notes(
    h3_index: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return active community notes for an H3 cell, sorted by upvotes."""
    result = await db.execute(
        select(CommunityNote).where(
            CommunityNote.h3_index == h3_index,
            CommunityNote.is_active,
            CommunityNote.expires_at > datetime.now(timezone.utc),
        ).order_by(CommunityNote.upvotes.desc(), CommunityNote.created_at.desc())
    )
    notes = result.scalars().all()

    out = []
    for note in notes:
        n = NoteOut.model_validate(note)
        n.is_mine = note.user_id == current_user.id
        out.append(n)
    return out


@router.post("/notes/{note_id}/upvote", status_code=200)
async def upvote_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upvote a community note. Each user can upvote a note once."""
    note_result = await db.execute(
        select(CommunityNote).where(CommunityNote.id == note_id, CommunityNote.is_active)
    )
    note = note_result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or expired")

    existing = await db.execute(
        select(NoteUpvote).where(NoteUpvote.note_id == note_id, NoteUpvote.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already upvoted")

    db.add(NoteUpvote(note_id=note_id, user_id=current_user.id))
    note.upvotes += 1
    await db.flush()
    return {"upvotes": note.upvotes}


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete your own note."""
    result = await db.execute(
        select(CommunityNote).where(
            CommunityNote.id == note_id,
            CommunityNote.user_id == current_user.id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.is_active = False
