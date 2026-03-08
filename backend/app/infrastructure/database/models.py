import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
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
