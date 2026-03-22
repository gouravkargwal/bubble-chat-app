from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # Allow overriding the env file via ENV_FILE so we can have clean staging/prod configs.
    # Defaults to .env.dev for local development.
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env.dev"),
        env_file_encoding="utf-8",
    )

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
    # Used by GeminiClient, vision_v2 hybrid OCR, audits/blueprints, and v2 LangGraph nodes
    # (vision / generator / auditor) via agent.nodes_v2._shared.
    gemini_model: str = "gemini-2.5-flash"

    # OpenRouter — used by v2 agent generator_node
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen3.5-9b"

    # Google Play Billing
    google_play_service_account: str = ""
    google_play_package_name: str = "com.cookd.app"

    # RevenueCat
    revenuecat_webhook_secret: str = ""

    # Signup trial — promo code auto-applied to new users (empty = no trial)
    signup_promo_code: str = "WELCOME"

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # OCI Object Storage (Always Free tier: 20 GB standard)
    # IMPORTANT: Create a lifecycle rule in OCI Console to auto-delete objects
    # with prefix "temp-audits/" after 1 day. This cleans up orphans from
    # interrupted uploads or crashed workers. See:
    # OCI Console → Object Storage → Bucket → Lifecycle Policy Rules
    oci_config_file: str = "~/.oci/config"  # path to OCI config file
    oci_config_profile: str = "DEFAULT"
    oci_bucket_name: str = "cookd-assets"
    oci_namespace: str = ""  # auto-detected if empty
    oci_par_expiry_hours: int = 1  # signed URL lifetime

    # App
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]
    base_url: str = "https://nonconscientious-annette-saddeningly.ngrok-free.dev"

    def validate_production(self) -> None:
        """Fail fast if critical secrets are not configured in production."""
        if self.environment != "development":
            if self.jwt_secret in ("change-me", ""):
                raise RuntimeError(
                    "JWT_SECRET must be set to a strong random value in production. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            if not self.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY must be set in production.")
            if "CHANGE-ME" in self.database_url.upper():
                raise RuntimeError("DATABASE_URL contains placeholder credentials.")


settings = Settings()
settings.validate_production()
