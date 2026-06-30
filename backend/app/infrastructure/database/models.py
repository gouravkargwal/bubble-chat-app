import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Stable cross-device identifier for Google accounts, used for quota tracking.
    # This comes from Firebase providerData[].uid where providerId == "google.com".
    google_provider_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )
    device_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )  # Primary device ID (unique)
    android_device_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # Android device ID for anti-fraud
    firebase_uid: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(
        String(20), default="free"
    )  # free, crush, match, rizz
    tier_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tier_source: Mapped[str] = mapped_column(
        String(20), default="signup"
    )  # signup, trial, purchase, admin
    # Referral
    referral_code: Mapped[str | None] = mapped_column(
        String(8), unique=True, nullable=True, index=True
    )
    bonus_replies: Mapped[int] = mapped_column(Integer, default=0)
    referred_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    prompt_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Set to the purchase timestamp whenever a new paid plan activates (INITIAL_PURCHASE / RENEWAL).
    # Usage counters use MAX(week_start, plan_period_start) so limits reset with each new period.
    plan_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    audited_photos: Mapped[list["AuditedPhoto"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profile_blueprints: Mapped[list["ProfileBlueprint"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    voice_dna: Mapped["UserVoiceDNA"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class UserQuota(Base):
    """Per-user quota counters keyed by stable Google provider ID.

    CRITICAL: This table must NOT be wiped on account deletion so we can
    preserve historical usage limits even if the user nukes their profile.

    Credits system:
    - credits_remaining: current spendable credits in the active period.
    - credits_period_limit: total credits granted for this period (set by billing).
    - credits_reset_at: when the period resets (weekly or monthly).
    - signup_bonus_granted: whether the one-time 15-credit free bonus was given.
    - daily_free_credits_used: how many free daily credits used today (free tier only).
    - daily_free_reset_at: when the daily free credit window resets.
    """

    __tablename__ = "user_quotas"

    # Primary key is the stable Google provider ID, NOT the temporary firebase_uid.
    google_provider_id: Mapped[str] = mapped_column(String(128), primary_key=True)

    # --- Credits system (new) ---
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0)
    credits_period_limit: Mapped[int] = mapped_column(Integer, default=0)
    credits_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signup_bonus_granted: Mapped[bool] = mapped_column(Integer, default=False)
    # Free tier daily credits tracking
    daily_free_credits_used: Mapped[int] = mapped_column(Integer, default=0)
    daily_free_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Idempotency: last 5 correlation_ids that were charged — prevents double-charge on retry.
    last_charged_keys: Mapped[str | None] = mapped_column(Text, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    person_name: Mapped[str] = mapped_column(String(100))
    stage: Mapped[str] = mapped_column(String(30), default="new_match")
    tone_trend: Mapped[str] = mapped_column(String(20), default="stable")
    topics_worked: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    topics_failed: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    # Phase 4: per-dimension tally observed across scans, e.g.
    # {"warmth": {"warm": 3, "neutral": 1}, "playfulness": {...}, ...}. The stable
    # (mode-smoothed) dimensions, the derived archetype, and confidence are all
    # computed from this in build_conversation_context. Dimensions are the
    # primitive; the archetype is always derived.
    dimension_counts: Mapped[str] = mapped_column(Text, default="{}")  # JSON object
    # Phase 5: per-strategy outcome stats, e.g.
    # {"PUSH-PULL": {"shown": 5, "copied": 3}}. "shown" increments at generate
    # time, "copied" when the user copies a reply with that strategy_label.
    strategy_stats: Mapped[str] = mapped_column(Text, default="{}")  # JSON object
    # Sticky curated-persona read from her photos (e.g. "rebel/edgy"). Captured
    # at the opener (rich photos) and carried forward into later chat turns where
    # photos aren't visible, so the coach's tone stays matched to her vibe.
    # Written only when a scan returns a non-empty read (never degraded to empty).
    photo_persona: Mapped[str] = mapped_column(String(64), default="")
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="conversations")


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (Index("ix_interactions_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    direction: Mapped[str] = mapped_column(String(30))
    custom_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # LLM analysis output
    their_last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    their_tone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    their_effort: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conversation_temperature: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    detected_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    key_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_organic_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Verbatim turn transcript (compact JSON: [{"s":"them"|"user","t":"..."}]).
    # Lets build_conversation_context replay the REAL back-and-forth instead of
    # lossy 60-char summaries. Nullable: rows saved before this column existed
    # fall back to the their_last_message paraphrase.
    transcript_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Generated replies
    reply_0: Mapped[str] = mapped_column(Text)
    reply_1: Mapped[str] = mapped_column(Text)
    reply_2: Mapped[str] = mapped_column(Text)
    reply_3: Mapped[str] = mapped_column(Text)
    # Tracking
    copied_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_positive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Vector embedding of the copied reply for similarity search (768-dim, gemini-embedding-001)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    # Metadata
    llm_model: Mapped[str] = mapped_column(String(100))
    prompt_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    temperature_used: Mapped[float] = mapped_column(Float)
    screenshot_count: Mapped[int] = mapped_column(Integer, default=1)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="interactions")


class UserVoiceDNA(Base):
    __tablename__ = "user_voice_dna"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )
    avg_reply_length: Mapped[float] = mapped_column(Float, default=0.0)
    emoji_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    common_words: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    punctuation_style: Mapped[str] = mapped_column(String(30), default="casual")
    capitalization: Mapped[str] = mapped_column(String(20), default="lowercase")
    preferred_length: Mapped[str] = mapped_column(String(20), default="medium")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    # Internal tracking for running averages
    emoji_count: Mapped[int] = mapped_column(Integer, default=0)
    lowercase_count: Mapped[int] = mapped_column(Integer, default=0)
    no_period_count: Mapped[int] = mapped_column(Integer, default=0)
    ellipsis_count: Mapped[int] = mapped_column(Integer, default=0)
    word_frequency: Mapped[str] = mapped_column(Text, default="{}")  # JSON dict
    recent_organic_messages: Mapped[str] = mapped_column(
        Text, default="[]"
    )  # JSON array
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="voice_dna")


class PendingResolution(Base):
    """DB-backed pending resolution store for Hybrid Stitch confirmation flow.

    Replaces the in-memory dict so it works across multiple workers.
    Rows auto-expire via TTL check; a periodic cleanup job can purge old rows.
    """

    __tablename__ = "pending_resolutions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    suggested_conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    images: Mapped[str] = mapped_column(Text)  # JSON array of base64 strings
    direction: Mapped[str] = mapped_column(String(30))
    custom_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extracted_person_name: Mapped[str] = mapped_column(String(100))
    conflict_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conflict_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cached VisionNodeOutput JSON — avoids re-running the vision LLM on resolve.
    vision_output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    outcome: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # "confirmed_match" | "rejected_new" | "expired"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_pending_res_user_conv", "user_id", "suggested_conversation_id"),
    )


class ConversationMemory(Base):
    """Atomic facts extracted per conversation for RAG memory retrieval.

    One row per fact. Superseded rows are soft-deleted (superseded_at set)
    when an NLI contradiction is detected against a newer fact.
    """

    __tablename__ = "conversation_memories"
    __table_args__ = (Index("ix_conv_mem_user_conv", "user_id", "conversation_id"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    fact_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    # Importance scoring for RAG retrieval prioritization (1-5 scale)
    # 5 = critical identity facts (marriage, religion, location)
    # 4 = important preferences (diet, job, kids)
    # 3 = opinions/goals
    # 2 = general facts (default)
    # 1 = minor details
    importance_score: Mapped[int | None] = mapped_column(
        Integer, default=2, nullable=True
    )
    # Categorization: identity, preference, opinion, factual, preference
    fact_category: Mapped[str | None] = mapped_column(
        String(50), default="factual", nullable=True
    )
    # Learned Sparse Retrieval: LLM-expanded synonyms and cross-lingual
    # tokens that feed into the combined GIN full-text-search index.
    lexical_expansion: Mapped[str | None] = mapped_column(
        Text, default="", nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConversationMemoryEntity(Base):
    """Graph RAG — entity nodes extracted from conversational facts.

    Each row represents a concrete noun (person, profession, location, hobby,
    organization, etc.) discovered by the LLM extraction layer.
    """

    __tablename__ = "conversation_memory_entities"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "entity_name",
            name="unique_conversation_entity",
        ),
        Index("ix_graph_entities_lookup", "conversation_id", "entity_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    entity_name: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))  # person, profession, hobby, location, etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConversationMemoryEdge(Base):
    """Graph RAG — directional edges between entity nodes.

    Each row represents a relationship (WORKS_AS, PLAYS, LIVES_IN, etc.)
    between two entities in the same conversation.
    """

    __tablename__ = "conversation_memory_edges"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "source_entity_id", "target_entity_id",
            "relationship_type",
            name="unique_conversation_edge",
        ),
        Index("ix_graph_edges_lookup", "conversation_id", "source_entity_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    source_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversation_memory_entities.id", ondelete="CASCADE")
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversation_memory_entities.id", ondelete="CASCADE")
    )
    relationship_type: Mapped[str] = mapped_column(String(50))  # WORKS_AS, PLAYS, LIVES_IN, etc.
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PersonAlias(Base):
    """Identity resolution table — maps OCR-extracted name variants to canonical conversations.

    When a user confirms a stitch (or auto-stitch succeeds), we persist the alias
    so future OCR extractions of the same name variant resolve instantly without
    fuzzy matching.
    """

    __tablename__ = "person_aliases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    alias_name: Mapped[str] = mapped_column(String(100))  # normalized lowercase name
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), index=True
    )
    source: Mapped[str] = mapped_column(
        String(30), default="auto_stitch"
    )  # auto_stitch | user_confirmed | manual
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "alias_name", name="uq_person_alias_user_name"),
        Index("ix_person_alias_user_alias", "user_id", "alias_name"),
    )


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    referrer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    referee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    bonus_granted: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    product_id: Mapped[str] = mapped_column(String(100))  # e.g. cookd_premium_monthly
    purchase_token: Mapped[str] = mapped_column(String(500), unique=True)
    order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="active"
    )  # active, cancelled, expired, refunded
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_renewing: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditJob(Base):
    """Tracks async profile audit jobs.

    When a user submits photos, a job row is created immediately and processing
    happens in the background.  The SSE / polling endpoints read this row to
    stream progress back to the client.
    """

    __tablename__ = "audit_jobs"
    __table_args__ = (
        # Partial unique index: only one non-failed job per (user, key).
        # NULL keys are excluded by Postgres (NULLs are never equal).
        # Failed jobs don't participate, allowing retries with the same key.
        Index(
            "uq_audit_jobs_user_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where="status != 'failed'",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    # pending → processing → completed | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_step: Mapped[str] = mapped_column(String(50), default="uploading")
    lang: Mapped[str] = mapped_column(String(30), default="English")
    # JSON-serialised AuditResponse on completion
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditedPhoto(Base):
    __tablename__ = "audited_photos"
    __table_args__ = (
        Index("ix_audited_photos_user_hash", "user_id", "hash", unique=True),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256 hex digest
    score: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(20))
    brutal_feedback: Mapped[str] = mapped_column(Text)
    improvement_tip: Mapped[str] = mapped_column(Text)
    # Optional per-audit one-liner roast (not stored per-photo in JSON).
    roast_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Idempotency key: allows safe retries without double-charging Gemini API credits.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="audited_photos")


class ProfileBlueprint(Base):
    __tablename__ = "profile_blueprints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    overall_theme: Mapped[str] = mapped_column(String(500))
    bio: Mapped[str] = mapped_column(Text, default="")
    # Prevents double-charges on network retries: if the same key is submitted
    # twice before the first response is received, the second call returns the
    # already-generated blueprint without calling the LLM again.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile_blueprints")
    slots: Mapped[list["BlueprintSlot"]] = relationship(
        back_populates="blueprint", cascade="all, delete-orphan"
    )
    universal_prompts: Mapped[list["BlueprintUniversalPrompt"]] = relationship(
        back_populates="blueprint", cascade="all, delete-orphan"
    )


class BlueprintSlot(Base):
    __tablename__ = "blueprint_slots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    blueprint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("profile_blueprints.id"), index=True
    )
    photo_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("audited_photos.id"), nullable=True, index=True
    )
    slot_number: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(200))
    caption: Mapped[str] = mapped_column(String(500))
    universal_hook: Mapped[str] = mapped_column(String(500))
    hinge_prompt: Mapped[str] = mapped_column(String(500), default="")
    aisle_prompt: Mapped[str] = mapped_column(String(500), default="")
    # coach_reasoning is stored for future admin/debug tooling.
    coach_reasoning: Mapped[str] = mapped_column(Text, default="")
    # storage_path is stored so the image_url can be re-derived if base_url changes.
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str] = mapped_column(String(1000), default="")

    blueprint: Mapped[ProfileBlueprint] = relationship(back_populates="slots")


class BlueprintUniversalPrompt(Base):
    """Universal cross-app prompt hooks generated per blueprint."""

    __tablename__ = "blueprint_universal_prompts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    blueprint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("profile_blueprints.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(200))
    suggested_text: Mapped[str] = mapped_column(Text)

    blueprint: Mapped[ProfileBlueprint] = relationship(
        back_populates="universal_prompts"
    )
