from typing import Literal

from pydantic import BaseModel, ConfigDict


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    skill_id: str
    name: str
    description: str | None = None
    category: str | None = None
    prompt_template: str | None = None
    mock_tool_name: str | None = None
    owner_user_id: str | None = None
    visibility: Literal["private", "shared"] = "shared"
    source: Literal["system", "user"] = "system"
    installed: bool = False


class InstallResponse(BaseModel):
    skill_id: str
    installed: bool


class SkillCreate(BaseModel):
    skill_id: str
    name: str
    description: str | None = None
    category: str | None = None
    prompt_template: str | None = None
    mock_tool_name: str = "generate_jd"
    visibility: Literal["private", "shared"] = "private"


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    prompt_template: str | None = None
    mock_tool_name: str | None = None
    visibility: Literal["private", "shared"] | None = None
