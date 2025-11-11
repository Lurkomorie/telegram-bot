#!/usr/bin/env python3
"""
Clear All Memories Script
Deletes all conversation memories from the database

Usage:
    python scripts/clear_all_memories.py              # Preview only (safe)
    python scripts/clear_all_memories.py --confirm    # Actually delete
    python scripts/clear_all_memories.py --backup     # Backup first, then delete
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.base import get_db
from app.db.models import Chat


def backup_memories():
    """Backup all memories to a JSON file before deletion"""
    backup_file = f"memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = project_root / "backups" / backup_file
    
    # Create backups directory if it doesn't exist
    backup_path.parent.mkdir(exist_ok=True)
    
    print(f"📦 Creating backup: {backup_path}")
    
    with get_db() as db:
        chats = db.query(Chat).filter(
            Chat.memory.isnot(None),
            Chat.memory != ""
        ).all()
        
        backup_data = []
        for chat in chats:
            backup_data.append({
                "chat_id": str(chat.id),
                "user_id": chat.user_id,
                "persona_id": str(chat.persona_id),
                "memory": chat.memory,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None
            })
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Backed up {len(backup_data)} memories")
        print(f"📁 Backup saved to: {backup_path}")
        return backup_path


def preview_deletion():
    """Show what will be deleted"""
    print("🔍 Scanning database...\n")
    
    with get_db() as db:
        # Count chats with memories
        chats_with_memory = db.query(Chat).filter(
            Chat.memory.isnot(None),
            Chat.memory != ""
        ).count()
        
        # Count total chats
        total_chats = db.query(Chat).count()
        
        # Get sample of memories to show
        sample_chats = db.query(Chat).filter(
            Chat.memory.isnot(None),
            Chat.memory != ""
        ).limit(5).all()
        
        print(f"📊 Database Statistics:")
        print(f"   Total chats: {total_chats}")
        print(f"   Chats with memories: {chats_with_memory}")
        print(f"   Chats without memories: {total_chats - chats_with_memory}")
        print()
        
        if chats_with_memory > 0:
            print(f"📝 Sample memories (first 5):")
            print("-" * 80)
            for i, chat in enumerate(sample_chats, 1):
                memory_preview = chat.memory[:150] + "..." if len(chat.memory) > 150 else chat.memory
                print(f"\n{i}. Chat {chat.id}")
                print(f"   User: {chat.user_id}")
                print(f"   Length: {len(chat.memory)} chars")
                print(f"   Preview: {memory_preview}")
            print("-" * 80)
            print()
        
        return chats_with_memory


def clear_all_memories():
    """Clear all memories from the database"""
    print("🗑️  Clearing all memories...")
    
    with get_db() as db:
        # Update all chats to have empty memory
        updated = db.query(Chat).filter(
            Chat.memory.isnot(None),
            Chat.memory != ""
        ).update(
            {"memory": None},
            synchronize_session=False
        )
        
        db.commit()
        
        print(f"✅ Cleared {updated} memories")
        return updated


def main():
    print("=" * 80)
    print("🧠 CLEAR ALL MEMORIES")
    print("=" * 80)
    print()
    
    # Check flags
    do_backup = "--backup" in sys.argv
    do_confirm = "--confirm" in sys.argv
    
    # Preview what will be deleted
    count = preview_deletion()
    
    if count == 0:
        print("ℹ️  No memories to delete")
        return
    
    print()
    print(f"⚠️  WARNING: This will delete {count} memories!")
    print()
    
    # Backup if requested
    if do_backup:
        backup_path = backup_memories()
        print()
    
    # Confirmation
    if not do_confirm:
        print("🔒 DRY RUN MODE (no changes will be made)")
        print()
        print("To actually delete memories, run:")
        print("   python scripts/clear_all_memories.py --confirm")
        print()
        print("To backup first, then delete:")
        print("   python scripts/clear_all_memories.py --backup --confirm")
        return
    
    # Final confirmation
    print("🚨 FINAL CONFIRMATION")
    print(f"   This will permanently delete {count} memories")
    if do_backup:
        print(f"   Backup saved to: {backup_path}")
    print()
    
    response = input("Type 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("❌ Aborted (confirmation not matched)")
        return
    
    # Delete
    deleted_count = clear_all_memories()
    
    print()
    print("=" * 80)
    print(f"✅ SUCCESS: Deleted {deleted_count} memories")
    print("=" * 80)
    print()
    print("💡 Next steps:")
    print("   1. New conversations will use the improved memory system")
    print("   2. Existing chats will build fresh memories from scratch")
    print("   3. Monitor logs for memory quality improvements")


if __name__ == "__main__":
    main()

