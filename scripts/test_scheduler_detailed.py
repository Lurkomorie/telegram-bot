"""
Detailed scheduler test to verify no duplicate followup logic
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db import crud
from app.settings import settings
from app.db.models import Chat
from sqlalchemy import or_, and_


def analyze_chat_for_followup(chat):
    """Analyze a single chat to see if it would receive followup"""
    now = datetime.utcnow()
    
    # Check if eligible for 30min followup
    eligible_30min = False
    eligible_24h = False
    
    # 30min logic
    if chat.status == "active" and chat.last_assistant_message_at:
        threshold_30min = now - timedelta(minutes=30)
        
        # Assistant spoke more than 30min ago
        if chat.last_assistant_message_at < threshold_30min:
            # Assistant spoke last
            if not chat.last_user_message_at or chat.last_assistant_message_at > chat.last_user_message_at:
                # Never sent auto-message OR user replied after last auto-message
                if not chat.last_auto_message_at:
                    eligible_30min = True
                elif chat.last_user_message_at and chat.last_auto_message_at < chat.last_user_message_at:
                    eligible_30min = True
    
    # 24h logic
    if chat.status == "active" and chat.last_assistant_message_at and chat.last_auto_message_at:
        threshold_24h = now - timedelta(hours=24)
        
        # Assistant spoke last
        if not chat.last_user_message_at or chat.last_assistant_message_at > chat.last_user_message_at:
            # Last auto-message was 24h ago
            if chat.last_auto_message_at < threshold_24h:
                # User hasn't replied since auto-message
                if not chat.last_user_message_at or chat.last_auto_message_at > chat.last_user_message_at:
                    eligible_24h = True
    
    return eligible_30min, eligible_24h


def test_duplicate_followup_risk():
    """Check if any chat could receive both 30min and 24h followup"""
    print("\n" + "="*80)
    print("CHECKING FOR DUPLICATE FOLLOWUP RISK")
    print("="*80)
    
    with get_db() as db:
        # Get ALL active chats
        all_active_chats = db.query(Chat).filter(Chat.status == "active").all()
        
        print(f"\nAnalyzing {len(all_active_chats)} active chats...")
        
        chats_30min = []
        chats_24h = []
        chats_both = []
        
        for chat in all_active_chats:
            eligible_30min, eligible_24h = analyze_chat_for_followup(chat)
            
            if eligible_30min:
                chats_30min.append(chat)
            if eligible_24h:
                chats_24h.append(chat)
            if eligible_30min and eligible_24h:
                chats_both.append(chat)
        
        print(f"\n📊 Results:")
        print(f"  - Eligible for 30min followup: {len(chats_30min)}")
        print(f"  - Eligible for 24h followup: {len(chats_24h)}")
        print(f"  - Eligible for BOTH (DUPLICATE RISK): {len(chats_both)}")
        
        if chats_both:
            print("\n⚠️  WARNING: Found chats eligible for BOTH followups!")
            print("These chats have conflicting logic:")
            for chat in chats_both[:5]:
                print(f"\n  Chat {str(chat.id)[:8]}... | User: {chat.user_id}")
                print(f"    Last assistant msg: {chat.last_assistant_message_at}")
                print(f"    Last user msg: {chat.last_user_message_at}")
                print(f"    Last auto msg: {chat.last_auto_message_at}")
        else:
            print("\n✅ SAFE: No chats eligible for both followups simultaneously")
            print("   The logic correctly prevents duplicate messages")
        
        # Show sample chats for each category
        if chats_30min:
            print("\n📝 Sample chats eligible for 30min followup:")
            for chat in chats_30min[:3]:
                print(f"  - Chat {str(chat.id)[:8]}... | User: {chat.user_id}")
                print(f"      Last assistant: {chat.last_assistant_message_at}")
                print(f"      Last user: {chat.last_user_message_at}")
                print(f"      Last auto: {chat.last_auto_message_at}")
        
        if chats_24h:
            print("\n📝 Sample chats eligible for 24h followup:")
            for chat in chats_24h[:3]:
                print(f"  - Chat {str(chat.id)[:8]}... | User: {chat.user_id}")
                print(f"      Last assistant: {chat.last_assistant_message_at}")
                print(f"      Last user: {chat.last_user_message_at}")
                print(f"      Last auto: {chat.last_auto_message_at}")


def test_with_actual_crud_functions():
    """Test with actual CRUD functions to be 100% sure"""
    print("\n" + "="*80)
    print("TESTING WITH ACTUAL CRUD FUNCTIONS")
    print("="*80)
    
    # Temporarily remove test user filter to see real numbers
    print("\n⚠️  Testing WITHOUT test user filter (to see real numbers)")
    
    with get_db() as db:
        # Get 30min candidates
        chats_30min = crud.get_inactive_chats(db, minutes=30, test_user_ids=None)
        chat_ids_30min = set(str(c.id) for c in chats_30min)
        
        # Get 24h candidates  
        chats_24h = crud.get_inactive_chats_for_reengagement(db, minutes=1440, test_user_ids=None)
        chat_ids_24h = set(str(c.id) for c in chats_24h)
        
        # Find intersection
        duplicate_ids = chat_ids_30min & chat_ids_24h
        
        print(f"\n📊 CRUD Function Results:")
        print(f"  - Chats from get_inactive_chats (30min): {len(chat_ids_30min)}")
        print(f"  - Chats from get_inactive_chats_for_reengagement (24h): {len(chat_ids_24h)}")
        print(f"  - Chats in BOTH lists (DUPLICATES): {len(duplicate_ids)}")
        
        if duplicate_ids:
            print("\n❌ CRITICAL: Found chats in both lists!")
            print("These chats would receive TWO followup messages:")
            for chat_id in list(duplicate_ids)[:5]:
                chat = db.query(Chat).filter(Chat.id == chat_id).first()
                if chat:
                    print(f"\n  Chat {str(chat.id)[:8]}... | User: {chat.user_id}")
                    print(f"    Status: {chat.status}")
                    print(f"    Last assistant: {chat.last_assistant_message_at}")
                    print(f"    Last user: {chat.last_user_message_at}")
                    print(f"    Last auto: {chat.last_auto_message_at}")
        else:
            print("\n✅ VERIFIED: No duplicates found!")
            print("   Each chat appears in at most ONE list")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCHEDULER DUPLICATE FOLLOWUP TEST")
    print("="*80)
    print("\nChecking if any chat could receive duplicate followup messages")
    print(f"Current time: {datetime.utcnow().isoformat()}")
    
    test_duplicate_followup_risk()
    test_with_actual_crud_functions()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

