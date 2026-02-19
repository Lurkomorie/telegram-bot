#!/usr/bin/env python3
"""
Cleanup Stale Data Script
Deletes chats inactive for >2 weeks and analytics events older than 2 weeks.
Saves Cloudflare image IDs to files for later deletion.

Usage:
    python scripts/cleanup_stale_data.py                  # Preview only (safe)
    python scripts/cleanup_stale_data.py --confirm        # Actually delete
    python scripts/cleanup_stale_data.py --events-only    # Delete only events
    python scripts/cleanup_stale_data.py --chats-only     # Delete only chats
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds
from app.db.base import get_db
from app.db.models import ImageJob, UserShownImage, TgAnalyticsEvent
from app.core.cloudflare_upload import extract_image_id_from_url


# Configuration
RETENTION_DAYS = 14  # 2 weeks
BATCH_SIZE = 1000    # Smaller batches to avoid memory issues
SLEEP_BETWEEN_BATCHES = 0.5  # seconds

# Output files for Cloudflare IDs
TIMESTAMP = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
CF_IDS_CHATS_FILE = f"/tmp/cloudflare_ids_chats_{TIMESTAMP}.txt"
CF_IDS_EVENTS_FILE = f"/tmp/cloudflare_ids_events_{TIMESTAMP}.txt"


def get_cutoff_date():
    """Get the cutoff date for deletion (14 days ago)"""
    return datetime.utcnow() - timedelta(days=RETENTION_DAYS)


def preview_deletion():
    """Show what will be deleted"""
    print("Scanning database...\n")
    
    cutoff = get_cutoff_date()
    print(f"Cutoff date: {cutoff.isoformat()} (older than {RETENTION_DAYS} days)\n")
    
    with get_db() as db:
        # Count old chats (where last_user_message_at is older than cutoff OR NULL)
        # Use raw SQL to avoid model/schema mismatch issues
        old_chats_count = db.execute(text(
            "SELECT COUNT(*) FROM chats WHERE last_user_message_at < :cutoff OR last_user_message_at IS NULL"
        ), {"cutoff": cutoff}).scalar()
        
        total_chats = db.execute(text("SELECT COUNT(*) FROM chats")).scalar()
        
        # Get sample of old chat IDs for related counts (limit to avoid memory issues)
        sample_result = db.execute(text(
            "SELECT id FROM chats WHERE last_user_message_at < :cutoff OR last_user_message_at IS NULL LIMIT 10000"
        ), {"cutoff": cutoff}).fetchall()
        sample_old_chat_ids = [row[0] for row in sample_result]
        
        # Estimate messages in old chats
        old_messages_count = 0
        if sample_old_chat_ids:
            old_messages_count = db.execute(text(
                "SELECT COUNT(*) FROM messages WHERE chat_id = ANY(:ids)"
            ), {"ids": sample_old_chat_ids}).scalar()
            # Scale up estimate if we sampled
            if old_chats_count > 10000:
                old_messages_count = int(old_messages_count * (old_chats_count / 10000))
        
        total_messages = db.execute(text("SELECT COUNT(*) FROM messages")).scalar()
        
        # Estimate image_jobs in old chats
        old_image_jobs_count = 0
        if sample_old_chat_ids:
            old_image_jobs_count = db.query(ImageJob).filter(
                ImageJob.chat_id.in_(sample_old_chat_ids)
            ).count()
            if old_chats_count > 10000:
                old_image_jobs_count = int(old_image_jobs_count * (old_chats_count / 10000))
        
        total_image_jobs = db.query(ImageJob).count()
        
        # Count old events
        old_events_count = db.execute(text(
            "SELECT COUNT(*) FROM tg_analytics_events WHERE created_at < :cutoff"
        ), {"cutoff": cutoff}).scalar()
        
        total_events = db.execute(text("SELECT COUNT(*) FROM tg_analytics_events")).scalar()
        
        print("Database Statistics:")
        print("-" * 60)
        print(f"  Chats:            {old_chats_count:,} to delete / {total_chats:,} total")
        print(f"  Messages:         ~{old_messages_count:,} to delete / {total_messages:,} total")
        print(f"  Image Jobs:       ~{old_image_jobs_count:,} to delete / {total_image_jobs:,} total")
        print(f"  Analytics Events: {old_events_count:,} to delete / {total_events:,} total")
        print("-" * 60)
        print()
        
        return {
            "chats": old_chats_count,
            "messages": old_messages_count,
            "image_jobs": old_image_jobs_count,
            "events": old_events_count,
        }


def delete_chats_batch():
    """Delete old chats in batches, collecting Cloudflare IDs"""
    cutoff = get_cutoff_date()
    
    total_chats_deleted = 0
    total_image_jobs_deleted = 0
    total_user_shown_deleted = 0
    cf_ids = []
    batch_num = 0
    
    print(f"\nDeleting chats older than {cutoff.isoformat()}...")
    print(f"Batch size: {BATCH_SIZE}\n")
    
    while True:
        batch_num += 1
        
        # Retry loop for transient connection failures
        for retry in range(MAX_RETRIES):
            try:
                with get_db() as db:
                    # Get batch of old chat IDs using raw SQL
                    result = db.execute(text(
                        "SELECT id FROM chats WHERE last_user_message_at < :cutoff OR last_user_message_at IS NULL LIMIT :limit"
                    ), {"cutoff": cutoff, "limit": BATCH_SIZE}).fetchall()
                    
                    if not result:
                        # Save collected IDs before returning
                        if cf_ids:
                            cf_ids = list(dict.fromkeys(cf_ids))
                            with open(CF_IDS_CHATS_FILE, 'w') as f:
                                f.write('\n'.join(cf_ids))
                            print(f"\n💾 Saved {len(cf_ids)} Cloudflare IDs to {CF_IDS_CHATS_FILE}")
                        return {
                            "chats": total_chats_deleted,
                            "image_jobs": total_image_jobs_deleted,
                            "user_shown": total_user_shown_deleted,
                            "cf_ids": len(cf_ids),
                        }
                    
                    chat_ids = [row[0] for row in result]
                    print(f"📦 Batch {batch_num}: Processing {len(chat_ids)} chats...")
                    
                    # Step 1: Get ALL ImageJobs for these chats (loop to handle large counts)
                    image_job_ids = []
                    while True:
                        image_jobs_batch = db.query(ImageJob).filter(
                            ImageJob.chat_id.in_(chat_ids)
                        ).limit(5000).all()
                        
                        if not image_jobs_batch:
                            break
                        
                        batch_ids = []
                        for job in image_jobs_batch:
                            batch_ids.append(job.id)
                            image_job_ids.append(job.id)
                            if job.result_url and "imagedelivery.net" in job.result_url:
                                cf_id = extract_image_id_from_url(job.result_url)
                                if cf_id:
                                    cf_ids.append(cf_id)
                        
                        # Delete UserShownImages for this batch
                        db.query(UserShownImage).filter(
                            UserShownImage.image_job_id.in_(batch_ids)
                        ).delete(synchronize_session=False)
                        
                        # Delete ImageJobs for this batch
                        jobs_deleted = db.query(ImageJob).filter(
                            ImageJob.id.in_(batch_ids)
                        ).delete(synchronize_session=False)
                        total_image_jobs_deleted += jobs_deleted
                        
                        db.flush()  # Ensure deletes are applied before next iteration
                    
                    # Step 4: Delete Chats using raw SQL (Messages cascade automatically)
                    result = db.execute(text(
                        "DELETE FROM chats WHERE id = ANY(:ids)"
                    ), {"ids": chat_ids})
                    chats_deleted = result.rowcount
                    total_chats_deleted += chats_deleted
                    
                    db.commit()
                    
                    print(f"   ✅ Deleted: {chats_deleted} chats, {len(image_job_ids)} image jobs")
                    print(f"   📊 Total: {total_chats_deleted} chats, {total_image_jobs_deleted} image jobs")
                    print(f"   🖼️  Cloudflare IDs collected: {len(cf_ids)}")
                    
                    break  # Success, exit retry loop
                    
            except OperationalError as e:
                if retry < MAX_RETRIES - 1:
                    print(f"   ⚠️  Connection error, retrying in {RETRY_DELAY}s... ({retry + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"   ❌ Max retries exceeded. Saving progress...")
                    # Save collected IDs before failing
                    if cf_ids:
                        cf_ids = list(dict.fromkeys(cf_ids))
                        with open(CF_IDS_CHATS_FILE, 'w') as f:
                            f.write('\n'.join(cf_ids))
                        print(f"\n💾 Saved {len(cf_ids)} Cloudflare IDs to {CF_IDS_CHATS_FILE}")
                    raise
        
        time.sleep(SLEEP_BETWEEN_BATCHES)


def delete_events_batch():
    """Delete old analytics events in batches, collecting Cloudflare IDs"""
    cutoff = get_cutoff_date()
    
    total_deleted = 0
    cf_ids = []
    batch_num = 0
    
    print(f"\nDeleting events older than {cutoff.isoformat()}...")
    print(f"Batch size: {BATCH_SIZE}\n")
    
    while True:
        batch_num += 1
        
        for retry in range(MAX_RETRIES):
            try:
                with get_db() as db:
                    # Get batch of old events
                    old_events = db.query(TgAnalyticsEvent).filter(
                        TgAnalyticsEvent.created_at < cutoff
                    ).limit(BATCH_SIZE).all()
                    
                    if not old_events:
                        # Save collected IDs before returning
                        if cf_ids:
                            cf_ids = list(dict.fromkeys(cf_ids))
                            with open(CF_IDS_EVENTS_FILE, 'w') as f:
                                f.write('\n'.join(cf_ids))
                            print(f"\n💾 Saved {len(cf_ids)} Cloudflare IDs to {CF_IDS_EVENTS_FILE}")
                        return {
                            "events": total_deleted,
                            "cf_ids": len(cf_ids),
                        }
                    
                    event_ids = []
                    for event in old_events:
                        event_ids.append(event.id)
                        # Collect Cloudflare IDs from image_url
                        if event.image_url and "imagedelivery.net" in event.image_url:
                            cf_id = extract_image_id_from_url(event.image_url)
                            if cf_id:
                                cf_ids.append(cf_id)
                    
                    print(f"📦 Batch {batch_num}: Deleting {len(event_ids)} events...")
                    
                    # Delete events
                    deleted = db.query(TgAnalyticsEvent).filter(
                        TgAnalyticsEvent.id.in_(event_ids)
                    ).delete(synchronize_session=False)
                    
                    db.commit()
                    total_deleted += deleted
                    
                    print(f"   ✅ Deleted: {deleted}")
                    print(f"   📊 Total: {total_deleted}")
                    print(f"   🖼️  Cloudflare IDs collected: {len(cf_ids)}")
                    
                    break  # Success, exit retry loop
                    
            except OperationalError as e:
                if retry < MAX_RETRIES - 1:
                    print(f"   ⚠️  Connection error, retrying in {RETRY_DELAY}s... ({retry + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"   ❌ Max retries exceeded. Saving progress...")
                    if cf_ids:
                        cf_ids = list(dict.fromkeys(cf_ids))
                        with open(CF_IDS_EVENTS_FILE, 'w') as f:
                            f.write('\n'.join(cf_ids))
                        print(f"\n💾 Saved {len(cf_ids)} Cloudflare IDs to {CF_IDS_EVENTS_FILE}")
                    raise
        
        time.sleep(SLEEP_BETWEEN_BATCHES)


def main():
    print("=" * 60)
    print("CLEANUP STALE DATA")
    print(f"Retention period: {RETENTION_DAYS} days")
    print("=" * 60)
    print()
    
    do_confirm = "--confirm" in sys.argv
    events_only = "--events-only" in sys.argv
    chats_only = "--chats-only" in sys.argv
    
    # Preview what will be deleted
    stats = preview_deletion()
    
    total_to_delete = stats["chats"] + stats["events"]
    
    if total_to_delete == 0:
        print("Nothing to delete. Database is clean.")
        return
    
    if not do_confirm:
        print("DRY RUN MODE (no changes made)")
        print()
        print("To actually delete, run:")
        print("   python scripts/cleanup_stale_data.py --confirm")
        print("   python scripts/cleanup_stale_data.py --confirm --chats-only")
        print("   python scripts/cleanup_stale_data.py --confirm --events-only")
        return
    
    # Final confirmation
    print("FINAL CONFIRMATION")
    print("   This will permanently delete:")
    if not events_only:
        print(f"   - {stats['chats']:,} chats (with ~{stats['messages']:,} messages)")
        print(f"   - ~{stats['image_jobs']:,} image jobs")
    if not chats_only:
        print(f"   - {stats['events']:,} analytics events")
    print()
    
    response = input("Type 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("Aborted (confirmation not matched)")
        return
    
    print()
    
    # Perform deletion
    chat_result = {"chats": 0, "image_jobs": 0, "cf_ids": 0}
    event_result = {"events": 0, "cf_ids": 0}
    
    if not events_only:
        chat_result = delete_chats_batch()
    
    if not chats_only:
        event_result = delete_events_batch()
    
    # Summary
    print()
    print("=" * 60)
    print("SUCCESS: Cleanup completed")
    print("=" * 60)
    if not events_only:
        print(f"  Chats deleted:      {chat_result['chats']:,}")
        print(f"  Image jobs deleted: {chat_result['image_jobs']:,}")
        print(f"  CF IDs (chats):     {chat_result['cf_ids']:,}")
    if not chats_only:
        print(f"  Events deleted:     {event_result['events']:,}")
        print(f"  CF IDs (events):    {event_result['cf_ids']:,}")
    print()
    
    total_cf = chat_result['cf_ids'] + event_result['cf_ids']
    if total_cf > 0:
        print("⚠️  Cloudflare images saved to:")
        if chat_result['cf_ids'] > 0:
            print(f"   - {CF_IDS_CHATS_FILE}")
        if event_result['cf_ids'] > 0:
            print(f"   - {CF_IDS_EVENTS_FILE}")
        print()
        print("To delete from Cloudflare, update CF_IDS_FILE in cleanup_cloudflare.py")
        print("and run: python scripts/cleanup_cloudflare.py")


if __name__ == "__main__":
    main()
