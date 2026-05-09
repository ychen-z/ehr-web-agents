import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.agents.models import AgentRun
from app.conversations.models import Conversation, Message
from app.conversations.service import create_message
from app.models.adapters import ChatModelAdapter, DeepSeekChatAdapter, MinimaxChatAdapter, OpenAIChatAdapter
from app.shared.config import Settings
from app.shared.errors import AppError
from app.skills.models import Skill, UserSkill

logger = logging.getLogger(__name__)

_STALE_RUN_MINUTES = 5


def _validate_skill_installed(db: Session, user_id: str, builtin_skill_id: str) -> Skill:
    skill = db.query(Skill).filter(Skill.skill_id == builtin_skill_id).first()
    if skill is None:
        raise AppError(code="SKILL_NOT_FOUND", message=f"Skill '{builtin_skill_id}' not found.", status_code=400)

    installed = db.query(UserSkill).filter(
        UserSkill.user_id == user_id, UserSkill.skill_id == skill.id,
    ).first()
    if installed is None:
        raise AppError(
            code="SKILL_NOT_INSTALLED",
            message=f"Skill '{builtin_skill_id}' is not installed. Install it first.",
            status_code=400,
        )
    return skill


def _validate_conversation_owner(db: Session, conversation_id: str, user_id: str) -> None:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None:
        raise AppError(code="CONVERSATION_NOT_FOUND", message="Conversation not found.", status_code=404)
    if conv.user_id != user_id:
        raise AppError(
            code="FORBIDDEN",
            message="Cannot create a run in another user's conversation.",
            status_code=403,
        )


def resolve_chat_adapter(provider_id: str | None, settings: Settings) -> ChatModelAdapter:
    if provider_id is None:
        if settings.deepseek_api_key:
            return DeepSeekChatAdapter(settings)
        if settings.openai_api_key:
            return OpenAIChatAdapter(settings)
        if settings.minimax_api_key:
            return MinimaxChatAdapter(settings)
        raise AppError(
            code="NO_MODEL_CONFIGURED",
            message="No chat model provider configured. Set DEEPSEEK_API_KEY, OPENAI_API_KEY, or MINIMAX_API_KEY.",
            status_code=400,
        )

    if provider_id == "deepseek":
        if not settings.deepseek_api_key:
            raise AppError(
                code="PROVIDER_NOT_CONFIGURED",
                message="DeepSeek is selected but DEEPSEEK_API_KEY is not configured.",
                status_code=400,
            )
        return DeepSeekChatAdapter(settings)

    if provider_id == "openai":
        if not settings.openai_api_key:
            raise AppError(
                code="PROVIDER_NOT_CONFIGURED",
                message="OpenAI is selected but OPENAI_API_KEY is not configured.",
                status_code=400,
            )
        return OpenAIChatAdapter(settings)

    if provider_id == "minimax":
        if not settings.minimax_api_key:
            raise AppError(
                code="PROVIDER_NOT_CONFIGURED",
                message="Minimax is selected but MINIMAX_API_KEY is not configured.",
                status_code=400,
            )
        return MinimaxChatAdapter(settings)

    raise AppError(
        code="UNKNOWN_PROVIDER",
        message=f"Unknown model provider '{provider_id}'.",
        status_code=400,
    )


def create_run(
    db: Session,
    user_id: str,
    skill_id: str,
    user_message: str,
    conversation_id: str | None,
    model_provider_id: str | None,
) -> AgentRun:
    _validate_skill_installed(db, user_id, skill_id)

    if conversation_id:
        _validate_conversation_owner(db, conversation_id, user_id)

    skill = db.query(Skill).filter(Skill.skill_id == skill_id).first()

    run = AgentRun(
        conversation_id=conversation_id,
        user_id=user_id,
        skill_id=skill.id,
        model_provider_id=model_provider_id,
        status="pending",
        structured_output=None,
        error_message=None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if conversation_id:
        create_message(db, conversation_id, "user", user_message)

    run.status = "running"
    db.commit()
    db.refresh(run)

    return run


def recover_stale_runs(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_STALE_RUN_MINUTES)
    stale = (
        db.query(AgentRun)
        .filter(
            AgentRun.status == "running",
            AgentRun.updated_at < cutoff,
        )
        .all()
    )
    for run in stale:
        run.status = "failed"
        run.error_message = "Run timed out after being in running state for too long."
    if stale:
        db.commit()
    return len(stale)
