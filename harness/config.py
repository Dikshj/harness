
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    database_url: str = "sqlite+aiosqlite:///./harness.db"
    rlm_memory_path: str = ".rlm_memory.jsonl"
    log_level: str = "INFO"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
