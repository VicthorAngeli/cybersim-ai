from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CyberSim AI"
    environment: str = "development"
    secret_key: str = Field(default="change-me-before-deployment", min_length=16)
    access_token_expire_minutes: int = Field(default=60, gt=0)
    database_url: str = "sqlite:///./cybersim.db"
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str | None = None
    openai_timeout: int = Field(default=60, gt=0)
    openai_max_retries: int = Field(default=1, ge=0)
    openai_max_tokens: int = Field(default=3000, gt=0)
    admin_email: str = "admin@cybersim.local"
    admin_password: str | None = None
    streamlit_api_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
