from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "sqlite+aiosqlite:///./rizzbot.db"

    # Auth
    jwt_secret: str = "change-me"
    jwt_expiry_hours: int = 720  # 30 days

    # Firebase
    firebase_service_account: str = ""  # path to service account JSON file
    firebase_project_id: str = ""

    # LLM — Gemini is the primary (and only) provider
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Rate limits
    daily_free_limit: int = 5

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # App
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]


settings = Settings()
