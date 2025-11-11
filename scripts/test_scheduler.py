"""
Test scheduler logic to see which chats would receive followup messages
WITHOUT actually sending any messages
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db import crud
from app.settings import settings


def test_30min_followups():
    """Test which chats would receive 30min followup messages"""
    print("\n" + "="*80)
    print("TESTING 30-MIN FOLLOWUP LOGIC")
    print("="*80)
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"\n🧪 Test mode enabled: Followups restricted to user IDs: {test_user_ids}")
    else:
        print(f"\n⚠️  Test mode disabled: Followups will apply to ALL users")
    
    with get_db() as db:
        # Get chats that would receive 30min followup
        inactive_chats = crud.get_inactive_chats(db, minutes=30, test_user_ids=test_user_ids)
        
        if not inactive_chats:
            print(f"\n✅ No chats would receive 30min followup")
            return
        
        print(f"\n⚠️  Found {len(inactive_chats)} chats that would receive 30min followup:")
        print("-" * 80)
        
        # Group by status and analyze
        by_status = {}
        for chat in inactive_chats:
            status = chat.status
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(chat)
        
        for status, chats in by_status.items():
            print(f"\nStatus: {status} - {len(chats)} chat(s)")
            for chat in chats[:5]:  # Show first 5 from each status
                last_activity = chat.last_assistant_message_at or chat.last_user_message_at or chat.updated_at
                days_ago = (datetime.utcnow() - last_activity).days if last_activity else "unknown"
                
                has_auto_msg = "Yes" if chat.last_auto_message_at else "No"
                print(f"  - Chat {chat.id[:8]}... | User: {chat.user_id} | "
                      f"Last activity: {days_ago} days ago | "
                      f"Has auto-message: {has_auto_msg}")
            
            if len(chats) > 5:
                print(f"  ... and {len(chats) - 5} more")


def test_24h_followups():
    """Test which chats would receive 24h re-engagement followup"""
    print("\n" + "="*80)
    print("TESTING 24H RE-ENGAGEMENT FOLLOWUP LOGIC")
    print("="*80)
    
    # Check if test user whitelist is enabled
    test_user_ids = settings.followup_test_user_ids
    if test_user_ids:
        print(f"\n🧪 Test mode enabled: Followups restricted to user IDs: {test_user_ids}")
    else:
        print(f"\n⚠️  Test mode disabled: Followups will apply to ALL users")
    
    with get_db() as db:
        # Get chats that would receive 24h followup
        inactive_chats = crud.get_inactive_chats_for_reengagement(db, minutes=1440, test_user_ids=test_user_ids)
        
        if not inactive_chats:
            print(f"\n✅ No chats would receive 24h re-engagement followup")
            return
        
        print(f"\n⚠️  Found {len(inactive_chats)} chats that would receive 24h re-engagement followup:")
        print("-" * 80)
        
        # Analyze
        for chat in inactive_chats[:10]:  # Show first 10
            last_activity = chat.last_assistant_message_at or chat.last_user_message_at or chat.updated_at
            days_ago = (datetime.utcnow() - last_activity).days if last_activity else "unknown"
            
            auto_msg_age = (datetime.utcnow() - chat.last_auto_message_at).days if chat.last_auto_message_at else "N/A"
            
            print(f"  - Chat {chat.id[:8]}... | User: {chat.user_id} | "
                  f"Last activity: {days_ago} days ago | "
                  f"Last auto-message: {auto_msg_age} days ago | "
                  f"Status: {chat.status}")
        
        if len(inactive_chats) > 10:
            print(f"  ... and {len(inactive_chats) - 10} more")


def check_active_chats_stats():
    """Get statistics about active chats"""
    print("\n" + "="*80)
    print("ACTIVE CHATS STATISTICS")
    print("="*80)
    
    with get_db() as db:
        from app.db.models import Chat
        
        # Count active chats
        total_active = db.query(Chat).filter(Chat.status == "active").count()
        total_archived = db.query(Chat).filter(Chat.status == "archived").count()
        total_all = db.query(Chat).count()
        
        print(f"\nTotal chats: {total_all}")
        print(f"  - Active: {total_active}")
        print(f"  - Archived: {total_archived}")
        
        # Get recent active chats (last 24 hours)
        threshold_24h = datetime.utcnow() - timedelta(hours=24)
        recent_active = db.query(Chat).filter(
            Chat.status == "active",
            Chat.updated_at >= threshold_24h
        ).count()
        
        print(f"\nActive chats with activity in last 24 hours: {recent_active}")
        
        # Get chats where assistant spoke last (potential followup candidates)
        from sqlalchemy import or_
        potential_30min = db.query(Chat).filter(
            Chat.status == "active",
            Chat.last_assistant_message_at.isnot(None),
            or_(
                Chat.last_user_message_at.is_(None),
                Chat.last_assistant_message_at > Chat.last_user_message_at
            )
        ).count()
        
        print(f"Active chats where assistant spoke last: {potential_30min}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCHEDULER FOLLOWUP TEST")
    print("="*80)
    print("\nThis script tests scheduler logic WITHOUT sending any messages")
    print(f"Current time: {datetime.utcnow().isoformat()}")
    
    # Check settings
    print(f"\nFollowup enabled: {settings.ENABLE_FOLLOWUPS}")
    
    if not settings.ENABLE_FOLLOWUPS:
        print("\n⚠️  WARNING: ENABLE_FOLLOWUPS is False - scheduler won't send any followups")
    
    # Run tests
    check_active_chats_stats()
    test_30min_followups()
    test_24h_followups()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

