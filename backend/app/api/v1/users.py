"""User data management endpoints."""

from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.deps import get_current_user
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import (
    AuditedPhoto,
    Conversation,
    Interaction,
    PersonAlias,
    ProfileBlueprint,
    User,
    UserVoiceDNA,
)

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()
STATIC_ROOT = Path("static")


@router.delete("/me/data")
async def delete_all_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Nuclear option: Delete all user data including interactions, photos, blueprints, and reset Voice DNA.

    This is an all-or-nothing operation wrapped in a transaction.
    """
    try:
        # Start transaction
        user_id = user.id

        # 1. Delete all Interactions (Chat history)
        interactions_result = await db.execute(
            select(Interaction).where(Interaction.user_id == user_id)
        )
        interactions = interactions_result.scalars().all()
        for interaction in interactions:
            await db.delete(interaction)
        logger.info(
            "user_data_purge_interactions", count=len(interactions), user_id=user_id
        )

        # 2. Delete all ProfileBlueprints first (cascade will handle BlueprintSlots)
        blueprints_result = await db.execute(
            select(ProfileBlueprint).where(ProfileBlueprint.user_id == user_id)
        )
        blueprints = blueprints_result.scalars().all()
        for blueprint in blueprints:
            await db.delete(blueprint)
        logger.info(
            "user_data_purge_blueprints", count=len(blueprints), user_id=user_id
        )

        # 3. Delete all AuditedPhotos and their files
        photos_result = await db.execute(
            select(AuditedPhoto).where(AuditedPhoto.user_id == user_id)
        )
        photos = photos_result.scalars().all()
        for photo in photos:
            # Delete the file from storage
            try:
                file_path = STATIC_ROOT / photo.storage_path.lstrip("/")
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(
                    "user_data_purge_file_failed",
                    error=str(e),
                    path=photo.storage_path,
                )
            await db.delete(photo)
        logger.info("user_data_purge_photos", count=len(photos), user_id=user_id)

        # 4. Delete person aliases (FK to conversations.id) before conversations
        aliases_result = await db.execute(
            select(PersonAlias).where(PersonAlias.user_id == user_id)
        )
        aliases = aliases_result.scalars().all()
        for alias in aliases:
            await db.delete(alias)
        logger.info(
            "user_data_purge_person_aliases", count=len(aliases), user_id=user_id
        )

        # 5. Delete all Conversations
        conversations_result = await db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversations = conversations_result.scalars().all()
        for conversation in conversations:
            await db.delete(conversation)
        logger.info(
            "user_data_purge_conversations", count=len(conversations), user_id=user_id
        )

        # 6. Reset UserVoiceDNA to blank state (don't delete, just reset)
        voice_dna_result = await db.execute(
            select(UserVoiceDNA).where(UserVoiceDNA.user_id == user_id)
        )
        voice_dna = voice_dna_result.scalar_one_or_none()
        if voice_dna:
            voice_dna.avg_reply_length = 0.0
            voice_dna.emoji_frequency = 0.0
            voice_dna.common_words = "[]"
            voice_dna.punctuation_style = "casual"
            voice_dna.capitalization = "lowercase"
            voice_dna.preferred_length = "medium"
            voice_dna.sample_count = 0
            voice_dna.emoji_count = 0
            voice_dna.lowercase_count = 0
            voice_dna.no_period_count = 0
            voice_dna.ellipsis_count = 0
            voice_dna.word_frequency = "{}"
            voice_dna.recent_organic_messages = "[]"
            voice_dna.semantic_profile = None
            logger.info("user_data_purge_voice_dna_reset", user_id=user_id)

        # 7. Null out directly identifying fields on the User record
        user.email = None
        user.display_name = None

        # Commit transaction
        await db.commit()

        logger.info(
            "user_data_purge_success",
            user_id=user_id,
            interactions_deleted=len(interactions),
            photos_deleted=len(photos),
            blueprints_deleted=len(blueprints),
            conversations_deleted=len(conversations),
        )

        return {
            "success": True,
            "message": "All user data deleted successfully.",
            "deleted": {
                "interactions": len(interactions),
                "photos": len(photos),
                "blueprints": len(blueprints),
                "conversations": len(conversations),
            },
        }
    except Exception as e:
        # Rollback on error
        await db.rollback()
        logger.error("user_data_purge_failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=500, detail="Failed to delete user data. Please try again."
        ) from e
