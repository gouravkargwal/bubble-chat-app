from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # Load from .env.dev file, but environment variables always take precedence.
    # In Docker Compose, the root .env.dev is injected via env_file, so vars
    # like YOUTUBE_API_KEY set there will override file-based values.
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env.dev"),
        env_file_encoding="utf-8",
        extra="ignore",
        # Environment variables override file values
        case_sensitive=False,
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
    # Backend: "ai_studio" (default, uses api_key) or "vertex_ai" (uses ADC/project+region).
    # Dev → ai_studio, Prod → vertex_ai (to use the $300 credits).
    gemini_provider: str = "ai_studio"
    # GCP project & region (required only when gemini_provider = "vertex_ai").
    gemini_project_id: str = ""
    gemini_region: str = "global"
    # Default model used when no per-node override is set.
    gemini_model: str = "gemini-3.1-flash-lite"
    # Optional per-node model overrides (empty = fall back to gemini_model).
    gemini_vision_model: str = ""
    gemini_generator_model: str = ""
    gemini_auditor_model: str = ""
    # Embeddings model (Vertex AI name: text-embedding-005 for 768d).
    gemini_embedding_model: str = "text-embedding-005"

    # OpenRouter — used by v2 agent generator_node
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen3.5-9b"

    # Groq — used by prompt eval judge AND (optionally) the v2 generator for A/B testing.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Which provider writes the replies (generator node ONLY — vision/auditor stay on Gemini).
    # "gemini" (default) or "groq". Flip GENERATOR_PROVIDER=groq in env to A/B a stronger
    # writer model on the same profile without touching vision/auditor cost.
    generator_provider: str = "gemini"

    # Which system prompt logic to use for generating replies.
    # "screenplay" (default, Netflix India Screenwriter roleplay) or "coach" (legacy Dating Coach rules).
    prompt_mode: str = "screenplay"

    # RevenueCat
    revenuecat_webhook_secret: str = ""

    # PayU (LTD payments — Indian payment gateway)
    payu_merchant_key: str = ""
    payu_merchant_salt: str = ""
    # PayU test environment: "test" or "live"
    payu_mode: str = "test"
    # PayU base URLs — changed in 2024, refer to PayU docs for your region
    # Test: https://test.payu.in, Live: https://secure.payu.in
    payu_base_url: str = "https://test.payu.in"
    # Where PayU redirects after payment (your domain)
    payu_redirect_base: str = "http://localhost:3000"
    # Sender email for LTD code emails (SendGrid / SMTP)
    ltd_email_from: str = "hello@cookdai.site"
    # SendPulse API credentials for transactional emails
    sendpulse_client_id: str = ""
    sendpulse_client_secret: str = ""

    # Signup trial — promo code auto-applied to new users (empty = no trial)
    signup_promo_code: str = "WELCOME"

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

    # Admin — shared secret for BFF proxy calls
    admin_api_key: str = ""

    # Social platform API keys (auto-poster)
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""

    # App
    environment: str = "development"
    log_level: str = "INFO"
    # One JSON object per line (Loki-friendly). Set LOG_JSON=false for pretty console locally.
    log_json: bool = True
    # Same value as the Docker Compose service name so Promtail `service_name` matches JSON logs.
    log_service_name: str = "api"
    cors_origins: list[str] = ["*"]
    base_url: str = "https://nonconscientious-annette-saddeningly.ngrok-free.dev"

    # Voice DNA (screenshot calibration + style learning). Off until re-enabled in product.
    voice_dna_enabled: bool = False

    # Lead magnet — public demo API
    lead_magnet_webhook_url: str = ""
    lead_magnet_app_url: str = (
        "https://play.google.com/store/apps/details?id=com.cookd.mobile"
    )
    lead_magnet_max_payload_mb: int = 5

    # OpenObserver (unified observability: logs, metrics, traces)
    openobserver_endpoint: str = "http://localhost:5001"
    openobserver_api_key: str = ""
    openobserver_service_name: str = "rizzbot-api"
    zo_org: str = "default"
    otlp_enabled: bool = True
    otlp_sample_rate: float = 0.1  # 10% sampling to control cost at scale
    # Root creds fall back to Basic auth for OTLP ingestion when no
    # per-org API key has been created yet in Settings -> API Keys.
    zo_root_user_email: str = ""
    zo_root_user_password: str = ""

    @property
    def openobserver_auth_header(self) -> str:
        """Full `Authorization` header value for OTLP export.

        Prefers a per-org API key (Bearer); falls back to root user
        Basic auth so logs/traces/metrics flow before an API key exists.
        """
        if self.openobserver_api_key:
            return f"Bearer {self.openobserver_api_key}"
        if self.zo_root_user_email and self.zo_root_user_password:
            import base64

            creds = f"{self.zo_root_user_email}:{self.zo_root_user_password}"
            return f"Basic {base64.b64encode(creds.encode()).decode()}"
        return ""

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
