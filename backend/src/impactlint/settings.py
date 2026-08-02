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
    datahub_mcp_url: str = "http://localhost:8001/mcp"
    datahub_mcp_token: str = ""
    paritok_api_url: str = "https://www.paritok.com/api"
    paritok_api_key: str = ""
    paritok_model: str = "paritok-4b-v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
