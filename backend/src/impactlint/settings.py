from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    impactlint_mode: Literal["fixture", "datahub"] = "fixture"
    datahub_mcp_url: str = "http://localhost:8000/mcp"
    datahub_mcp_token: str = ""
    paritok_proxy_url: str = "http://localhost:8080"
    paritok_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
