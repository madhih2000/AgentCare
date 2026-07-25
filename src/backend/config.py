import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

_SQLITE_DEFAULT_DATABASE_URL = "sqlite:///./data/agentcare.db"

# Suffixes of env var names that hold a usable Postgres connection string,
# most-preferred first. Vercel's native "Vercel Postgres" storage injects
# these unprefixed (POSTGRES_URL); connecting a marketplace integration (e.g.
# Neon via the Storage tab) namespaces every var with a prefix the user
# chooses at connect-time (e.g. VERCEL_STORAGE_POSTGRES_URL) — the prefix
# itself is arbitrary and not something to hardcode, so we match on suffix
# instead. Deliberately narrow (not a generic "*_URL" scan) so this can never
# accidentally pick up an unrelated var — e.g. Neon Auth's
# *_NEON_AUTH_BASE_URL / *_VITE_NEON_AUTH_URL don't end in any of these.
_POSTGRES_URL_SUFFIXES = (
    "POSTGRES_URL",  # pooled — preferred for serverless
    "POSTGRES_URL_NON_POOLING",
    "DATABASE_URL_UNPOOLED",
)


def _find_env_postgres_url() -> str | None:
    for suffix in _POSTGRES_URL_SUFFIXES:
        matches = sorted(
            value
            for key, value in os.environ.items()
            if key.upper() == suffix or key.upper().endswith("_" + suffix)
        )
        if matches:
            return matches[0]
    return None


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

    # Database — SQLite locally by default. If DATABASE_URL isn't set
    # explicitly, fall back to whatever Postgres connection string a
    # connected storage integration injected (see _find_env_postgres_url) —
    # no manual DATABASE_URL copy-paste needed on Vercel. This means the same
    # codebase runs on SQLite locally and Postgres on Vercel purely from
    # which env vars happen to be present, with no environment branching.
    database_url: str = _SQLITE_DEFAULT_DATABASE_URL

    @model_validator(mode="after")
    def _prefer_connected_postgres_if_no_explicit_database_url(self) -> "Settings":
        if self.database_url != _SQLITE_DEFAULT_DATABASE_URL:
            return self  # DATABASE_URL was set explicitly — respect it as-is.
        pg_url = _find_env_postgres_url()
        if pg_url:
            # SQLAlchemy dropped the `postgres://` scheme alias; Vercel/Neon
            # still hand out URLs with it, so normalize before use.
            self.database_url = pg_url.replace("postgres://", "postgresql://", 1)
        return self

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
