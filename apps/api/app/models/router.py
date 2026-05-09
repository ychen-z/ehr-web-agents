from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.models.schemas import ModelConfigResponse
from app.models.service import list_models
from app.shared.auth import get_current_user
from app.shared.config import Settings, get_settings
from app.shared.database import get_db

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelConfigResponse])
def get_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return list_models(settings, db)
