from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.conversations.models import Conversation, Message
from app.shared.errors import AppError

_VALID_ROLES = {"user", "assistant", "system"}

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _validate_role(role: str) -> None:
    if role not in _VALID_ROLES:
        raise AppError(
            code="INVALID_MESSAGE_ROLE",
            message=f"Invalid role '{role}'. Must be one of: {', '.join(sorted(_VALID_ROLES))}.",
            status_code=400,
        )


def create_conversation(db: Session, user_id: str, title: str | None = None) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(conversation)
    return conversation


def list_conversations(
    db: Session, user_id: str, limit: int = _DEFAULT_LIMIT, offset: int = 0
) -> list[Conversation]:
    effective_limit = max(1, min(limit, _MAX_LIMIT))
    effective_offset = max(0, offset)
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(effective_limit)
        .offset(effective_offset)
        .all()
    )


def get_conversation(db: Session, conversation_id: str, user_id: str) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )


def create_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    _validate_role(role)

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise AppError(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
            status_code=404,
        )

    conversation.updated_at = datetime.now(timezone.utc)

    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(message)
    return message


def list_messages(
    db: Session, conversation_id: str, user_id: str, limit: int = _DEFAULT_LIMIT, offset: int = 0
) -> list[Message]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if conversation is None:
        raise AppError(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
            status_code=404,
        )

    effective_limit = max(1, min(limit, _MAX_LIMIT))
    effective_offset = max(0, offset)
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(effective_limit)
        .offset(effective_offset)
        .all()
    )
