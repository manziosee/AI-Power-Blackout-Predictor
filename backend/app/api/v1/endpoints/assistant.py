from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.assistant_service import ask

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


class AskRequest(BaseModel):
    question: str
    h3_index: str | None = None


class AskResponse(BaseModel):
    answer: str
    h3_index: str | None = None


@router.post("/ask", response_model=AskResponse)
async def ask_assistant(
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AskResponse:
    answer = await ask(body.question, db, h3_index=body.h3_index)
    return AskResponse(answer=answer, h3_index=body.h3_index)
