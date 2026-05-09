from pydantic import BaseModel, ConfigDict


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    skill_id: str
    name: str
    description: str | None = None
    category: str | None = None
    installed: bool = False


class InstallResponse(BaseModel):
    skill_id: str
    installed: bool
