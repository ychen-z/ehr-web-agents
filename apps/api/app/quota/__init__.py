"""Token 用量追踪 + 日上限。"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.shared.database import Base
from app.shared.errors import AppError

if TYPE_CHECKING:
    pass

DEFAULT_DAILY_TOKEN_LIMIT = 200_000


class TokenUsageLog(Base):
    __tablename__ = "token_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider_id: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def record_usage(
    db: Session,
    *,
    user_id: str,
    run_id: str | None,
    provider_id: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> TokenUsageLog:
    total = prompt_tokens + completion_tokens
    log = TokenUsageLog(
        user_id=user_id,
        run_id=run_id,
        provider_id=provider_id,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        usage_date=date.today(),
    )
    db.add(log)
    db.flush()
    return log


def get_daily_usage(db: Session, user_id: str, day: date | None = None) -> int:
    """获取指定用户当日已消耗 token 总量。"""
    day = day or date.today()
    result = db.query(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0)).filter(
        TokenUsageLog.user_id == user_id,
        TokenUsageLog.usage_date == day,
    ).scalar()
    return int(result)


def check_daily_quota(db: Session, user_id: str, daily_limit: int = DEFAULT_DAILY_TOKEN_LIMIT) -> None:
    """检查用户今日额度是否已用完，超限则抛出 AppError。"""
    used = get_daily_usage(db, user_id)
    if used >= daily_limit:
        raise AppError(
            code="QUOTA_EXCEEDED",
            message=f"今日 Token 额度已用完（已使用 {used:,} / 上限 {daily_limit:,}）",
            status_code=429,
        )
