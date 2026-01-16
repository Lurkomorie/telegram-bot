#!/usr/bin/env python3
"""
Cleanup Old Data Script
Deletes old analytics events and inactive chats (with messages and images) older than 1 week.

Usage:
    python scripts/cleanup_old_data.py                      # Preview only (safe)
    python scripts/cleanup_old_data.py --confirm            # Actually delete all
    python scripts/cleanup_old_data.py --events-only        # Delete only analytics events (skips preview)
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.base import get_db
from app.db.models import Chat, Message, ImageJob, TgAnalyticsEvent


RETENTION_DAYS = 7
BATCH_SIZE = 5000  # Delete in batches to avoid connection timeouts


def get_cutoff_date():
    """Get the cutoff date for deletion (7 days ago)"""
    return datetime.utcnow() - timedelta(days=RETENTION_DAYS)


def preview_deletion():
    """Show what will be deleted"""
    print("Scanning database...\n")
    
    cutoff = get_cutoff_date()
    print(f"Cutoff date: {cutoff.isoformat()} (older than {RETENTION_DAYS} days)\n")
    
    with get_db() as db:
        # Count old events
        old_events_count = db.query(TgAnalyticsEvent).filter(
            TgAnalyticsEvent.created_at < cutoff
        ).count()
        
        total_events = db.query(TgAnalyticsEvent).count()
        
        # Count old chats (where last_user_message_at is older than cutoff)
        old_chats_query = db.query(Chat).filter(
            Chat.last_user_message_at < cutoff
        )
        old_chats_count = old_chats_query.count()
        
        total_chats = db.query(Chat).count()
        
        # Get IDs of old chats for related queries
        old_chat_ids = [chat.id for chat in old_chats_query.all()]
        
        # Count messages in old chats
        old_messages_count = 0
        if old_chat_ids:
            old_messages_count = db.query(Message).filter(
                Message.chat_id.in_(old_chat_ids)
            ).count()
        
        total_messages = db.query(Message).count()
        
        # Count image_jobs in old chats
        old_image_jobs_count = 0
        if old_chat_ids:
            old_image_jobs_count = db.query(ImageJob).filter(
                ImageJob.chat_id.in_(old_chat_ids)
            ).count()
        
        total_image_jobs = db.query(ImageJob).count()
        
        print("Database Statistics:")
        print("-" * 60)
        print(f"  Analytics Events: {old_events_count:,} to delete / {total_events:,} total")
        print(f"  Chats:            {old_chats_count:,} to delete / {total_chats:,} total")
        print(f"  Messages:         {old_messages_count:,} to delete / {total_messages:,} total")
        print(f"  Image Jobs:       {old_image_jobs_count:,} to delete / {total_image_jobs:,} total")
        print("-" * 60)
        print()
        
        return {
            "events": old_events_count,
            "chats": old_chats_count,
            "messages": old_messages_count,
            "image_jobs": old_image_jobs_count,
            "old_chat_ids": old_chat_ids,
        }


def delete_in_batches(db, model, filter_condition, label):
    """Delete records in batches to avoid connection timeouts"""
    total_deleted = 0
    
    while True:
        # Get batch of IDs to delete
        batch_ids = db.query(model.id).filter(filter_condition).limit(BATCH_SIZE).all()
        
        if not batch_ids:
            break
        
        batch_ids = [row[0] for row in batch_ids]
        
        # Delete this batch
        deleted = db.query(model).filter(model.id.in_(batch_ids)).delete(synchronize_session=False)
        db.commit()
        
        total_deleted += deleted
        print(f"  {label}: deleted {total_deleted:,} so far...")
    
    return total_deleted


def perform_deletion():
    """Delete old data from the database"""
    cutoff = get_cutoff_date()
    
    print(f"Starting deletion (batch size: {BATCH_SIZE:,})...\n")
    
    with get_db() as db:
        # Step 1: Get old chat IDs
        old_chat_ids = [
            chat.id for chat in db.query(Chat).filter(
                Chat.last_user_message_at < cutoff
            ).all()
        ]
        
        # Step 2: Delete image_jobs for old chats first (no cascade) - in batches
        image_jobs_deleted = 0
        if old_chat_ids:
            # Process in chunks since IN clause with 10k+ IDs can be slow
            for i in range(0, len(old_chat_ids), BATCH_SIZE):
                chunk_ids = old_chat_ids[i:i + BATCH_SIZE]
                deleted = db.query(ImageJob).filter(
                    ImageJob.chat_id.in_(chunk_ids)
                ).delete(synchronize_session=False)
                db.commit()
                image_jobs_deleted += deleted
                print(f"  Image jobs: deleted {image_jobs_deleted:,} so far...")
        
        print(f"  Image jobs: {image_jobs_deleted:,} total deleted")
        
        # Step 3: Delete old chats in batches (messages cascade automatically)
        chats_deleted = delete_in_batches(
            db, Chat,
            Chat.last_user_message_at < cutoff,
            "Chats"
        )
        print(f"  Chats: {chats_deleted:,} total deleted (messages cascaded)")
        
        # Step 4: Delete old events in batches
        events_deleted = delete_in_batches(
            db, TgAnalyticsEvent,
            TgAnalyticsEvent.created_at < cutoff,
            "Analytics events"
        )
        print(f"  Analytics events: {events_deleted:,} total deleted")
        
        print()
        return {
            "events": events_deleted,
            "chats": chats_deleted,
            "image_jobs": image_jobs_deleted,
        }


def delete_events_only():
    """Delete only analytics events (skips chats/images)"""
    cutoff = get_cutoff_date()
    
    print(f"Deleting analytics events older than {cutoff.isoformat()}")
    print(f"Batch size: {BATCH_SIZE:,}\n")
    
    with get_db() as db:
        events_deleted = delete_in_batches(
            db, TgAnalyticsEvent,
            TgAnalyticsEvent.created_at < cutoff,
            "Analytics events"
        )
        print(f"\nTotal analytics events deleted: {events_deleted:,}")
        return events_deleted


def main():
    print("=" * 60)
    print("CLEANUP OLD DATA")
    print(f"Retention period: {RETENTION_DAYS} days")
    print("=" * 60)
    print()
    
    do_confirm = "--confirm" in sys.argv
    events_only = "--events-only" in sys.argv
    
    # Events-only mode: skip preview, just delete events
    if events_only:
        print("MODE: Events only (skipping chats/images)\n")
        response = input("Type 'DELETE' to confirm deletion of old analytics events: ")
        if response != "DELETE":
            print("Aborted (confirmation not matched)")
            return
        
        events_deleted = delete_events_only()
        print()
        print("=" * 60)
        print(f"SUCCESS: Deleted {events_deleted:,} analytics events")
        print("=" * 60)
        return
    
    # Preview what will be deleted
    stats = preview_deletion()
    
    total_to_delete = stats["events"] + stats["chats"] + stats["messages"] + stats["image_jobs"]
    
    if total_to_delete == 0:
        print("Nothing to delete. Database is clean.")
        return
    
    print(f"WARNING: This will delete {total_to_delete:,} total records!")
    print()
    
    if not do_confirm:
        print("DRY RUN MODE (no changes made)")
        print()
        print("To actually delete, run:")
        print("   python scripts/cleanup_old_data.py --confirm")
        return
    
    # Final confirmation
    print("FINAL CONFIRMATION")
    print("   This will permanently delete:")
    print(f"   - {stats['events']:,} analytics events")
    print(f"   - {stats['chats']:,} chats")
    print(f"   - {stats['messages']:,} messages")
    print(f"   - {stats['image_jobs']:,} image jobs")
    print()
    
    response = input("Type 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("Aborted (confirmation not matched)")
        return
    
    # Perform deletion
    result = perform_deletion()
    
    print("=" * 60)
    print("SUCCESS: Cleanup completed")
    print(f"  Events deleted:     {result['events']:,}")
    print(f"  Chats deleted:      {result['chats']:,}")
    print(f"  Image jobs deleted: {result['image_jobs']:,}")
    print("=" * 60)


if __name__ == "__main__":
    main()
