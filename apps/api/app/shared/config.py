from pydantic_settings import BaseSettings, SettingsConfigDict

_settings: "Settings | None" = None


def get_settings() -> "Settings":
    if _settings is not None:
        return _settings
    return Settings()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "ehr_agents"
    mysql_user: str = "ehr_agents"
    mysql_password: str = "ehr_agents"

    jwt_secret: str = "change-me-in-local-dev"
    cors_origins: str = "http://localhost:5173"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "MiniMax-M1"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
