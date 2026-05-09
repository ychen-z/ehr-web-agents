import logging

from sqlalchemy.orm import Session

from app.models.models import ModelConfig
from app.shared.config import Settings

logger = logging.getLogger(__name__)

_PROVIDER_METADATA = [
    {
        "provider_id": "deepseek",
        "display_name": "DeepSeek",
        "default_model_name": "deepseek-chat",
        "enabled": True,
    },
    {
        "provider_id": "openai",
        "display_name": "OpenAI GPT",
        "default_model_name": "gpt-4o-mini",
        "enabled": True,
    },
    {
        "provider_id": "minimax",
        "display_name": "Minimax",
        "default_model_name": "MiniMax-M1",
        "enabled": True,
    },
]


def seed_model_configs(db: Session) -> None:
    for entry in _PROVIDER_METADATA:
        existing = db.query(ModelConfig).filter(ModelConfig.provider_id == entry["provider_id"]).first()
        if existing is not None:
            continue
        config = ModelConfig(
            provider_id=entry["provider_id"],
            display_name=entry["display_name"],
            default_model_name=entry["default_model_name"],
            enabled=entry["enabled"],
        )
        db.add(config)
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.debug("Skipping duplicate model config for provider %s", entry["provider_id"])


def _is_configured(settings: Settings, provider_id: str) -> bool:
    key_map = {
        "deepseek": settings.deepseek_api_key,
        "openai": settings.openai_api_key,
        "minimax": settings.minimax_api_key,
    }
    api_key = key_map.get(provider_id, "")
    return bool(api_key and api_key.strip())


def list_models(settings: Settings, db: Session) -> list[dict]:
    rows = db.query(ModelConfig).all()

    result = []
    for row in rows:
        result.append({
            "provider_id": row.provider_id,
            "display_name": row.display_name,
            "default_model_name": row.default_model_name,
            "configured": _is_configured(settings, row.provider_id),
            "enabled": row.enabled,
        })
    return result
