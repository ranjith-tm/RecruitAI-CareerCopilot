from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RecruitAI"
    app_version: str = "2.0.0"
    debug: bool = False

    openai_api_key: str = ""
    groq_api_key: str = ""

    default_provider: str = "openai"
    default_model: str = "gpt-4o-mini"

    cors_origins: list[str] = ["*"]
    max_pdf_size_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
