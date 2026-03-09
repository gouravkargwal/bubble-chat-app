import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free, premium, pro
    tier_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Referral
    referral_code: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True, index=True)
    bonus_replies: Mapped[int] = mapped_column(Integer, default=0)
    referred_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    prompt_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    person_name: Mapped[str] = mapped_column(String(100))
    stage: Mapped[str] = mapped_column(String(30), default="new_match")
    tone_trend: Mapped[str] = mapped_column(String(20), default="stable")
    topics_worked: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    topics_failed: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_interaction_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        Index("ix_interactions_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    direction: Mapped[str] = mapped_column(String(30))
    custom_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # LLM analysis output
    their_last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    their_tone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    their_effort: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conversation_temperature: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detected_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    person_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    key_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Generated replies
    reply_0: Mapped[str] = mapped_column(Text)
    reply_1: Mapped[str] = mapped_column(Text)
    reply_2: Mapped[str] = mapped_column(Text)
    reply_3: Mapped[str] = mapped_column(Text)
    # Tracking
    copied_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_positive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Metadata
    llm_model: Mapped[str] = mapped_column(String(100))
    prompt_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    temperature_used: Mapped[float] = mapped_column(Float)
    screenshot_count: Mapped[int] = mapped_column(Integer, default=1)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserVoiceDNA(Base):
    __tablename__ = "user_voice_dna"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, index=True)
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
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    referee_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    bonus_granted: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    product_id: Mapped[str] = mapped_column(String(100))  # e.g. cookd_premium_monthly
    purchase_token: Mapped[str] = mapped_column(String(500), unique=True)
    order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")  # active, cancelled, expired, refunded
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_renewing: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Promo(Base):
    __tablename__ = "promos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    tier_grant: Mapped[str] = mapped_column(String(20))  # premium or pro
    duration_days: Mapped[int] = mapped_column(Integer, default=7)  # trial length
    max_uses: Mapped[int] = mapped_column(Integer, default=100)
    current_uses: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    new_users_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (
        UniqueConstraint("user_id", "promo_id", name="uq_promo_redemption_user_promo"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    promo_id: Mapped[str] = mapped_column(String(36), ForeignKey("promos.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
