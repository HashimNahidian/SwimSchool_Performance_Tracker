import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    secret_key: str
    access_token_expire_minutes: int
    refresh_token_expire_minutes: int
    allow_bootstrap_manager: bool
    cors_origins: list[str]
    login_rate_limit_count: int
    login_rate_limit_window_seconds: int
    enable_audit_log: bool


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    values = [item.strip() for item in raw.split(",")]
    return [item for item in values if item]


settings = Settings(
    app_env=os.getenv("APP_ENV", "development").lower(),
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://propel:propelpass@localhost:5432/propel_eval",
    ),
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
    refresh_token_expire_minutes=int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080")),
    allow_bootstrap_manager=_bool_env("ALLOW_BOOTSTRAP_MANAGER", True),
    cors_origins=_list_env(
        "CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ),
    login_rate_limit_count=int(os.getenv("LOGIN_RATE_LIMIT_COUNT", "10")),
    login_rate_limit_window_seconds=int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")),
    enable_audit_log=_bool_env("ENABLE_AUDIT_LOG", True),
)
