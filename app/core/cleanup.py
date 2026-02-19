"""
Daily cleanup job: delete old inactive chats with all related data
(messages, image jobs, Cloudflare images, purchases, shown images)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Chat, ImageJob, UserShownImage
from app.core.cloudflare_upload import extract_image_id_from_url, delete_from_cloudflare

logger = logging.getLogger(__name__)

# Config
INACTIVE_DAYS = 30
BATCH_SIZE = 50  # Chats per batch
CF_DELETE_DELAY = 0.1  # Seconds between Cloudflare delete calls
BATCH_DELAY = 2  # Seconds between DB batches


async def _delete_cloudflare_images_for_jobs(db: Session, chat_ids: list) -> int:
    """Delete Cloudflare images for all image jobs belonging to given chat IDs.
    Returns count of successfully deleted CF images."""
    cf_deleted = 0

    image_jobs = db.query(ImageJob).filter(
        ImageJob.chat_id.in_(chat_ids)
    ).all()

    for job in image_jobs:
        # Delete main result_url from Cloudflare
        if job.result_url and "imagedelivery.net" in job.result_url:
            image_id = extract_image_id_from_url(job.result_url)
            if image_id:
                success = await delete_from_cloudflare(image_id)
                if success:
                    cf_deleted += 1
                await asyncio.sleep(CF_DELETE_DELAY)

        # Delete blurred_original_url from Cloudflare (stored in ext)
        if job.ext and isinstance(job.ext, dict):
            blurred_url = job.ext.get("blurred_original_url")
            if blurred_url and "imagedelivery.net" in blurred_url:
                image_id = extract_image_id_from_url(blurred_url)
                if image_id:
                    success = await delete_from_cloudflare(image_id)
                    if success:
                        cf_deleted += 1
                    await asyncio.sleep(CF_DELETE_DELAY)

    return cf_deleted


def _delete_db_records_for_chats(db: Session, chat_ids: list) -> dict:
    """Delete all DB records related to the given chat IDs.
    Messages and ChatPurchases cascade-delete from Chat.
    ImageJobs and UserShownImages must be deleted manually.
    Returns counts of deleted records."""

    # 1. Delete UserShownImage records that reference ImageJobs for these chats
    image_job_ids_subq = (
        db.query(ImageJob.id).filter(ImageJob.chat_id.in_(chat_ids)).subquery()
    )
    shown_deleted = db.query(UserShownImage).filter(
        UserShownImage.image_job_id.in_(select(image_job_ids_subq))
    ).delete(synchronize_session="fetch")

    # 2. Delete ImageJobs for these chats
    jobs_deleted = db.query(ImageJob).filter(
        ImageJob.chat_id.in_(chat_ids)
    ).delete(synchronize_session="fetch")

    # 3. Delete Chats (Messages + ChatPurchases cascade automatically)
    chats_deleted = db.query(Chat).filter(
        Chat.id.in_(chat_ids)
    ).delete(synchronize_session="fetch")

    db.commit()

    return {
        "chats": chats_deleted,
        "image_jobs": jobs_deleted,
        "shown_images": shown_deleted,
    }


async def cleanup_old_chats():
    """Main cleanup entry point. Finds chats inactive for >INACTIVE_DAYS days
    and deletes them with all related data in batches."""
    cutoff = datetime.utcnow() - timedelta(days=INACTIVE_DAYS)
    print(f"[CLEANUP] Starting daily cleanup. Cutoff: {cutoff.isoformat()} ({INACTIVE_DAYS} days ago)")

    total_chats = 0
    total_jobs = 0
    total_shown = 0
    total_cf = 0
    batch_num = 0

    while True:
        batch_num += 1

        with get_db() as db:
            # Find a batch of chats where the last activity is older than cutoff
            stale_chats = db.query(Chat).filter(
                Chat.updated_at < cutoff
            ).limit(BATCH_SIZE).all()

            if not stale_chats:
                break

            chat_ids = [c.id for c in stale_chats]
            print(f"[CLEANUP] Batch {batch_num}: processing {len(chat_ids)} chats...")

            # Step 1: Delete Cloudflare images (async HTTP calls)
            cf_deleted = await _delete_cloudflare_images_for_jobs(db, chat_ids)
            total_cf += cf_deleted

            # Step 2: Delete DB records
            counts = _delete_db_records_for_chats(db, chat_ids)
            total_chats += counts["chats"]
            total_jobs += counts["image_jobs"]
            total_shown += counts["shown_images"]

            print(
                f"[CLEANUP] Batch {batch_num} done: "
                f"{counts['chats']} chats, {counts['image_jobs']} image_jobs, "
                f"{counts['shown_images']} shown_images, {cf_deleted} CF images"
            )

        # Pause between batches to reduce DB/API pressure
        await asyncio.sleep(BATCH_DELAY)

    print(
        f"[CLEANUP] Daily cleanup finished. "
        f"Totals: {total_chats} chats, {total_jobs} image_jobs, "
        f"{total_shown} shown_images, {total_cf} CF images deleted"
    )
