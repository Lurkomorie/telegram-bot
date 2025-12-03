"""
Generate evaluation dataset from real conversations.
Extracts conversations with sufficient messages for evaluation testing.

Usage:
    python scripts/generate_eval_dataset.py --chats 50 --min-messages 10
    python scripts/generate_eval_dataset.py --output custom_dataset.json
"""
import sys
import os
import json
import argparse
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings import load_configs
from app.db.base import get_db
from app.db import crud
from app.db.models import Chat, Message, Persona, ImageJob


def generate_dataset(
    num_chats: int = 50,
    min_messages: int = 10,
    output_file: str = "eval_dataset.json",
    include_image_jobs: bool = True
) -> dict:
    """
    Generate evaluation dataset from database.
    
    Args:
        num_chats: Maximum number of chats to include
        min_messages: Minimum messages per chat
        output_file: Output JSON file path
        include_image_jobs: Whether to include image job data
    
    Returns:
        Dataset dictionary
    """
    print(f"\n📊 Generating evaluation dataset...")
    print(f"   Max chats: {num_chats}")
    print(f"   Min messages per chat: {min_messages}")
    print(f"   Output: {output_file}\n")
    
    dataset = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "num_chats": 0,
            "total_messages": 0,
            "total_exchanges": 0,  # User-assistant pairs
        },
        "chats": []
    }
    
    with get_db() as db:
        # Query chats with message count filter
        # Get recent active chats with sufficient messages
        chats = db.query(Chat).filter(
            Chat.message_count >= min_messages,
            Chat.status == "active"
        ).order_by(
            Chat.updated_at.desc()
        ).limit(num_chats).all()
        
        print(f"   Found {len(chats)} qualifying chats\n")
        
        for chat in chats:
            # Fetch persona
            persona = db.query(Persona).filter(
                Persona.id == chat.persona_id
            ).first()
            
            if not persona:
                continue
            
            # Fetch all messages
            messages = db.query(Message).filter(
                Message.chat_id == chat.id
            ).order_by(
                Message.created_at.asc()
            ).all()
            
            if len(messages) < min_messages:
                continue
            
            # Build message list
            message_list = []
            for msg in messages:
                message_data = {
                    "role": msg.role,
                    "content": msg.text or "",
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                
                # Include state snapshot if available (assistant messages)
                if msg.state_snapshot:
                    message_data["state_snapshot"] = msg.state_snapshot
                
                message_list.append(message_data)
            
            # Fetch image jobs if requested
            image_jobs_list = []
            if include_image_jobs:
                image_jobs = db.query(ImageJob).filter(
                    ImageJob.chat_id == chat.id
                ).order_by(
                    ImageJob.created_at.asc()
                ).all()
                
                for job in image_jobs:
                    image_jobs_list.append({
                        "prompt": job.prompt,
                        "negative_prompt": job.negative_prompt,
                        "status": job.status,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "ext": job.ext or {},
                    })
            
            # Build exchanges (user-assistant pairs for evaluation)
            exchanges = []
            i = 0
            while i < len(message_list):
                # Find user message
                if message_list[i]["role"] == "user":
                    user_msg = message_list[i]
                    
                    # Find next assistant message
                    assistant_msg = None
                    for j in range(i + 1, len(message_list)):
                        if message_list[j]["role"] == "assistant":
                            assistant_msg = message_list[j]
                            i = j
                            break
                    
                    if assistant_msg:
                        # Build context (messages before this exchange)
                        context_messages = message_list[:i-1] if i > 1 else []
                        
                        exchange = {
                            "user_message": user_msg["content"],
                            "assistant_response": assistant_msg["content"],
                            "state_after": assistant_msg.get("state_snapshot"),
                            "context_messages": context_messages[-10:],  # Last 10 for context
                        }
                        exchanges.append(exchange)
                
                i += 1
            
            # Build chat data
            chat_data = {
                "chat_id": str(chat.id),
                "persona": {
                    "id": str(persona.id),
                    "name": persona.name,
                    "key": persona.key,
                    "prompt": persona.prompt,
                    "image_prompt": persona.image_prompt,
                },
                "memory": chat.memory,
                "current_state": chat.state_snapshot,
                "message_count": len(message_list),
                "messages": message_list,
                "exchanges": exchanges,
                "image_jobs": image_jobs_list if include_image_jobs else [],
            }
            
            dataset["chats"].append(chat_data)
            dataset["metadata"]["total_messages"] += len(message_list)
            dataset["metadata"]["total_exchanges"] += len(exchanges)
        
        dataset["metadata"]["num_chats"] = len(dataset["chats"])
    
    # Save to file
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "eval_data",
        output_file
    )
    
    # Create directory if needed
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Dataset generated successfully!")
    print(f"   📁 Output: {output_path}")
    print(f"   📊 Chats: {dataset['metadata']['num_chats']}")
    print(f"   💬 Messages: {dataset['metadata']['total_messages']}")
    print(f"   🔄 Exchanges: {dataset['metadata']['total_exchanges']}")
    
    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Generate evaluation dataset from conversations"
    )
    parser.add_argument(
        "--chats", "-c",
        type=int,
        default=50,
        help="Maximum number of chats to include (default: 50)"
    )
    parser.add_argument(
        "--min-messages", "-m",
        type=int,
        default=10,
        help="Minimum messages per chat (default: 10)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="eval_dataset.json",
        help="Output filename (default: eval_dataset.json)"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Exclude image job data"
    )
    
    args = parser.parse_args()
    
    # Load configs
    load_configs()
    
    # Generate dataset
    generate_dataset(
        num_chats=args.chats,
        min_messages=args.min_messages,
        output_file=args.output,
        include_image_jobs=not args.no_images
    )


if __name__ == "__main__":
    main()

