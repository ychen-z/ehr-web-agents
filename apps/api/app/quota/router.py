"""用量查询 API。"""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.models import User
from app.quota import get_daily_usage
from app.shared.auth import get_current_user
from app.shared.config import Settings, get_settings
from app.shared.database import get_db

router = APIRouter(prefix="/api/quota", tags=["quota"])


class UsageSummary(BaseModel):
    user_id: str
    date: str
    used_tokens: int
    daily_limit: int
    remaining: int
    percentage: float


@router.get("/usage/today", response_model=UsageSummary)
def get_today_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    today = date.today()
    used = get_daily_usage(db, current_user.id, today)
    limit = settings.daily_token_limit
    remaining = max(0, limit - used)
    pct = (used / limit * 100) if limit > 0 else 0

    return UsageSummary(
        user_id=current_user.id,
        date=today.isoformat(),
        used_tokens=used,
        daily_limit=limit,
        remaining=remaining,
        percentage=round(pct, 1),
    )
