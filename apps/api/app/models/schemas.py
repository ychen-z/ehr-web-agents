from pydantic import BaseModel, ConfigDict


class ModelConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider_id: str
    display_name: str
    default_model_name: str
    configured: bool = False
    enabled: bool = True
