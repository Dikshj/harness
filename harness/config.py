
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    database_url: str = "sqlite+aiosqlite:///./harness.db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    anthropic_api_key: str | None = None
    minimax_api_key: str | None = None
    minimax_base_url: str = "https://api.minimax.io/v1"
    minimax_model: str = "MiniMax-M2.7"
    github_token: str | None = None
    default_model: str = "gpt-4o"
    sandbox_timeout: int = 300
    sandbox_cpu_limit: float = 2.0
    sandbox_mem_limit: str = "2g"
    log_level: str = "INFO"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
