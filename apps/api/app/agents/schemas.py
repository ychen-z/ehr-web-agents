from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RunCreate(BaseModel):
    skill_id: str
    user_message: str
    conversation_id: str | None = None
    model_provider_id: str | None = None


class RunResponse(BaseModel):
    id: str
    conversation_id: str | None
    user_id: str
    skill_id: str
    model_provider_id: str | None
    status: str
    structured_output: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
