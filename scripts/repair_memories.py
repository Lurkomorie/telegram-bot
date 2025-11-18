#!/usr/bin/env python3
"""
Memory Repair Tool
Identifies and repairs poor-quality conversation memories

Usage:
    python scripts/repair_memories.py list          # List chats with poor memories
    python scripts/repair_memories.py check <chat_id>  # Check specific chat memory
    python scripts/repair_memories.py repair <chat_id> # Repair specific chat memory
    python scripts/repair_memories.py repair-all    # Repair all poor memories (use with caution)
"""
import sys
import os
import asyncio
import re
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from uuid import UUID
from sqlalchemy import func
from app.db.base import get_db
from app.db.models import Chat
from app.db import crud
from app.core.memory_service import update_memory, _validate_memory_quality


def is_poor_quality_memory(memory: str) -> tuple[bool, list[str]]:
    """
    Check if a memory is poor quality
    
    Returns:
        (is_poor, reasons) - True if memory is poor quality with list of reasons
    """
    if not memory:
        return False, []  # Empty is OK for new chats
    
    reasons = []
    
    # Check for placeholder text
    if memory.strip() in ["No memory yet. This is the first interaction.", "No memory yet."]:
        reasons.append("Placeholder text")
    
    # Check for role confusion
    role_confusion_patterns = [
        r"user is an? ai",
        r"user is an? assistant",
        r"user is an? conversation",
        r"user is an? chatbot",
        r"user shows concern about the user",
        r"user.*\b(wings|tail|horns|persona)\b",
    ]
    
    for pattern in role_confusion_patterns:
        if re.search(pattern, memory.lower()):
            reasons.append(f"Role confusion: {pattern}")
    
    # Check for overly vague phrases
    vague_phrases = [
        "user is interested in",
        "user engaged in", 
        "user participated in",
        "user was described as",
    ]
    
    vague_count = sum(1 for phrase in vague_phrases if phrase in memory.lower())
    total_sentences = memory.count('.') + 1
    
    if total_sentences >= 3 and vague_count >= total_sentences * 0.5:
        reasons.append(f"Too vague: {vague_count}/{total_sentences} sentences")
    
    # Check if suspiciously short for multi-message chats
    if len(memory) < 50 and total_sentences < 2:
        reasons.append("Suspiciously short")
    
    return len(reasons) > 0, reasons


def list_poor_memories():
    """List all chats with poor quality memories"""
    print("🔍 Scanning for poor quality memories...\n")
    
    with get_db() as db:
        # Get all active chats with memories
        chats = db.query(Chat).filter(
            Chat.status == "active",
            Chat.memory.isnot(None),
            Chat.memory != ""
        ).all()
        
        print(f"Found {len(chats)} chats with memories\n")
        
        poor_quality_chats = []
        
        for chat in chats:
            is_poor, reasons = is_poor_quality_memory(chat.memory)
            
            if is_poor:
                # Get message count
                message_count = len(crud.get_chat_messages(db, chat.id, limit=100))
                
                poor_quality_chats.append({
                    "chat_id": chat.id,
                    "user_id": chat.user_id,
                    "message_count": message_count,
                    "memory_length": len(chat.memory),
                    "memory": chat.memory,
                    "reasons": reasons
                })
        
        if not poor_quality_chats:
            print("✅ No poor quality memories found!")
            return
        
        print(f"❌ Found {len(poor_quality_chats)} chats with poor quality memories:\n")
        
        for item in poor_quality_chats:
            print(f"Chat ID: {item['chat_id']}")
            print(f"User ID: {item['user_id']}")
            print(f"Messages: {item['message_count']}")
            print(f"Memory length: {item['memory_length']} chars")
            print(f"Issues: {', '.join(item['reasons'])}")
            print(f"Memory preview: {item['memory'][:150]}...")
            print("-" * 80)
            print()


def check_memory(chat_id: str):
    """Check memory quality for a specific chat"""
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        print(f"❌ Invalid chat ID format: {chat_id}")
        return
    
    with get_db() as db:
        chat = crud.get_chat_by_id(db, chat_uuid)
        if not chat:
            print(f"❌ Chat not found: {chat_id}")
            return
        
        messages = crud.get_chat_messages(db, chat_uuid, limit=100)
        
        print(f"📊 Chat Analysis")
        print(f"Chat ID: {chat.id}")
        print(f"User ID: {chat.user_id}")
        print(f"Status: {chat.status}")
        print(f"Messages: {len(messages)}")
        print(f"Created: {chat.created_at}")
        print(f"Last updated: {chat.updated_at}")
        print()
        
        if not chat.memory:
            print("⚠️  No memory set for this chat")
            return
        
        print(f"📝 Current Memory ({len(chat.memory)} chars):")
        print(chat.memory)
        print()
        
        is_poor, reasons = is_poor_quality_memory(chat.memory)
        
        if is_poor:
            print(f"❌ Memory Quality: POOR")
            print(f"Issues:")
            for reason in reasons:
                print(f"  - {reason}")
        else:
            print(f"✅ Memory Quality: GOOD")
        
        # Run validation
        is_valid, validation_reason = _validate_memory_quality(chat.memory, chat.memory)
        print(f"\nValidation: {'✅ PASS' if is_valid else '❌ FAIL'} - {validation_reason}")


async def repair_memory(chat_id: str, dry_run: bool = False):
    """Repair memory for a specific chat"""
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        print(f"❌ Invalid chat ID format: {chat_id}")
        return
    
    with get_db() as db:
        chat = crud.get_chat_by_id(db, chat_uuid)
        if not chat:
            print(f"❌ Chat not found: {chat_id}")
            return
        
        print(f"🔧 Repairing memory for chat {chat_id}")
        print(f"User ID: {chat.user_id}")
        
        # Get conversation history (last 15 messages)
        messages = crud.get_chat_messages(db, chat_uuid, limit=15)
        
        if not messages:
            print(f"⚠️  No messages found, cannot repair memory")
            return
        
        print(f"Found {len(messages)} messages for context")
        
        # Build chat history
        chat_history = [
            {"role": m.role, "content": m.text}
            for m in messages
            if m.text
        ]
        
        print(f"\n📝 Current Memory ({len(chat.memory or '')} chars):")
        print(chat.memory or "(empty)")
        print()
        
        print("🧠 Regenerating memory...")
        
        # Generate new memory
        new_memory = await update_memory(
            chat_id=chat_uuid,
            chat_history=chat_history,
            current_memory=None  # Start fresh to avoid bad memory influencing new one
        )
        
        print(f"\n✨ New Memory ({len(new_memory)} chars):")
        print(new_memory)
        print()
        
        # Validate new memory
        is_valid, reason = _validate_memory_quality(new_memory, chat.memory)
        print(f"Validation: {'✅ PASS' if is_valid else '❌ FAIL'} - {reason}")
        
        if not is_valid:
            print("⚠️  New memory failed validation, not saving")
            return
        
        if dry_run:
            print("\n🔍 DRY RUN - Memory not saved to database")
        else:
            # Save to database
            crud.update_chat_memory(db, chat_uuid, new_memory)
            print("\n✅ Memory saved to database")


async def repair_all_memories(dry_run: bool = True):
    """Repair all poor quality memories"""
    print("🔧 Starting bulk memory repair...")
    
    if not dry_run:
        confirm = input("⚠️  This will regenerate ALL poor quality memories. Continue? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            return
    
    with get_db() as db:
        chats = db.query(Chat).filter(
            Chat.status == "active",
            Chat.memory.isnot(None),
            Chat.memory != ""
        ).all()
        
        poor_chats = []
        for chat in chats:
            is_poor, reasons = is_poor_quality_memory(chat.memory)
            if is_poor:
                poor_chats.append(chat)
        
        print(f"Found {len(poor_chats)} chats needing repair")
        
        for i, chat in enumerate(poor_chats, 1):
            print(f"\n[{i}/{len(poor_chats)}] Repairing chat {chat.id}...")
            await repair_memory(str(chat.id), dry_run=dry_run)
            
            # Brief delay to avoid rate limiting
            await asyncio.sleep(2)
        
        print(f"\n✅ Completed repair of {len(poor_chats)} chats")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_poor_memories()
    
    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: python scripts/repair_memories.py check <chat_id>")
            return
        check_memory(sys.argv[2])
    
    elif command == "repair":
        if len(sys.argv) < 3:
            print("Usage: python scripts/repair_memories.py repair <chat_id>")
            return
        dry_run = "--dry-run" in sys.argv
        asyncio.run(repair_memory(sys.argv[2], dry_run=dry_run))
    
    elif command == "repair-all":
        dry_run = "--dry-run" not in sys.argv or "--live" not in sys.argv
        if dry_run:
            print("🔍 Running in DRY RUN mode (add --live to actually save changes)")
        asyncio.run(repair_all_memories(dry_run=dry_run))
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()





