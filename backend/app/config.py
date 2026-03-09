from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.dev", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://cookd:cookd@localhost:5432/cookd"

    # Auth
    jwt_secret: str = "change-me"
    jwt_expiry_hours: int = 720  # 30 days

    # Firebase
    firebase_service_account: str = ""  # path to service account JSON file
    firebase_project_id: str = ""

    # LLM — Gemini is the primary (and only) provider
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Google Play Billing
    google_play_service_account: str = ""
    google_play_package_name: str = "com.cookd.app"

    # Signup trial — promo code auto-applied to new users (empty = no trial)
    signup_promo_code: str = "WELCOME"

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # App
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]

    def validate_production(self) -> None:
        """Fail fast if critical secrets are not configured in production."""
        if self.environment != "development":
            if self.jwt_secret in ("change-me", ""):
                raise RuntimeError(
                    "JWT_SECRET must be set to a strong random value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            if not self.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY must be set in production.")
            if "CHANGE-ME" in self.database_url.upper():
                raise RuntimeError("DATABASE_URL contains placeholder credentials.")


settings = Settings()
settings.validate_production()
