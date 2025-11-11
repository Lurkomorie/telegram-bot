"""
Archive inactive chats (no activity in last 24 hours)

This prevents old inactive chats from receiving followup messages
when the followup system is enabled.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db.models import Chat
from sqlalchemy import or_, and_


def archive_inactive_chats(hours: int = 24, dry_run: bool = True):
    """
    Archive chats that have been inactive for more than N hours
    
    Args:
        hours: Number of hours of inactivity (default: 24)
        dry_run: If True, only show what would be archived without making changes
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Archiving chats inactive for more than {hours} hours...")
    
    threshold = datetime.utcnow() - timedelta(hours=hours)
    
    with get_db() as db:
        # Find active chats where the most recent activity (user or assistant) is older than threshold
        query = db.query(Chat).filter(
            Chat.status == "active",
            or_(
                # Both timestamps exist and both are old
                and_(
                    Chat.last_user_message_at.isnot(None),
                    Chat.last_assistant_message_at.isnot(None),
                    Chat.last_user_message_at < threshold,
                    Chat.last_assistant_message_at < threshold
                ),
                # Only user message exists and it's old
                and_(
                    Chat.last_user_message_at.isnot(None),
                    Chat.last_assistant_message_at.is_(None),
                    Chat.last_user_message_at < threshold
                ),
                # Only assistant message exists and it's old
                and_(
                    Chat.last_user_message_at.is_(None),
                    Chat.last_assistant_message_at.isnot(None),
                    Chat.last_assistant_message_at < threshold
                ),
                # No activity timestamps at all (very old chats)
                and_(
                    Chat.last_user_message_at.is_(None),
                    Chat.last_assistant_message_at.is_(None),
                    Chat.updated_at < threshold
                )
            )
        )
        
        chats_to_archive = query.all()
        
        if not chats_to_archive:
            print("✅ No inactive chats found to archive")
            return
        
        print(f"\nFound {len(chats_to_archive)} inactive chats to archive:")
        print("-" * 80)
        
        # Group by user for better overview
        by_user = {}
        for chat in chats_to_archive:
            if chat.user_id not in by_user:
                by_user[chat.user_id] = []
            by_user[chat.user_id].append(chat)
        
        for user_id, user_chats in by_user.items():
            print(f"\nUser {user_id}: {len(user_chats)} chat(s)")
            for chat in user_chats:
                last_activity = max(
                    filter(None, [
                        chat.last_user_message_at,
                        chat.last_assistant_message_at,
                        chat.updated_at
                    ])
                )
                days_ago = (datetime.utcnow() - last_activity).days
                print(f"  - Chat {chat.id} (Persona: {chat.persona_id}) - Last activity: {days_ago} days ago")
        
        print("-" * 80)
        print(f"\nTotal: {len(chats_to_archive)} chats from {len(by_user)} users")
        
        if not dry_run:
            # Archive the chats
            for chat in chats_to_archive:
                chat.status = "archived"
            
            db.commit()
            print(f"\n✅ Successfully archived {len(chats_to_archive)} chats")
        else:
            print(f"\n⚠️  DRY RUN: No changes made. Run with --commit to actually archive chats.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Archive inactive chats to prevent followup spam"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours of inactivity before archiving (default: 24)"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually archive chats (without this flag, it's a dry run)"
    )
    
    args = parser.parse_args()
    
    archive_inactive_chats(
        hours=args.hours,
        dry_run=not args.commit
    )

