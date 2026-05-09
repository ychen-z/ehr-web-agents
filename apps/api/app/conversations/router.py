from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.models import User
from app.conversations.schemas import ConversationCreate, ConversationResponse, MessageResponse
from app.conversations.service import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
)
from app.shared.auth import get_current_user
from app.shared.database import get_db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=200)
def create(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_conversation(db, current_user.id, body.title)


@router.get("", response_model=list[ConversationResponse])
def list_my(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_conversations(db, current_user.id, limit=limit, offset=offset)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_conv_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_messages(db, conversation_id, current_user.id, limit=limit, offset=offset)
