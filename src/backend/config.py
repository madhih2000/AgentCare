from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"

    # LLM (Groq)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # Comma-separated backup models, tried in order if the primary (or an
    # earlier backup) errors out (rate limit, outage, decommissioned model).
    groq_fallback_models: str = "openai/gpt-oss-20b,llama-3.3-70b-versatile,llama-3.1-8b-instant"

    # Database
    database_url: str = "sqlite:///./data/agentcare.db"

    # LangGraph checkpointing
    langgraph_checkpointer: str = "memory"  # "memory" | "sqlite"
    langgraph_checkpoint_db: str = "./data/checkpoints.db"

    # Auth
    jwt_secret: str = "dev_only_change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # File storage
    upload_dir: str = "./uploads"

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def groq_model_chain(self) -> list[str]:
        """Primary model followed by fallback models, de-duplicated in order."""
        seen: list[str] = [self.groq_model]
        for name in self.groq_fallback_models.split(","):
            name = name.strip()
            if name and name not in seen:
                seen.append(name)
        return seen


@lru_cache
def get_settings() -> Settings:
    return Settings()
