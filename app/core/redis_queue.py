"""
Redis-based message queue for batching
Manages message queuing, processing locks, and batch retrieval
"""
import json
from typing import List, Dict
from uuid import UUID
import redis.asyncio as aioredis
from app.settings import settings


# Global Redis connection
_redis_client = None


async def get_redis():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def add_message_to_queue(
    chat_id: UUID,
    user_id: int,
    text: str,
    tg_chat_id: int
) -> int:
    """
    Add a message to the Redis queue for a chat
    
    Args:
        chat_id: Chat UUID
        user_id: Telegram user ID
        text: Message text
        tg_chat_id: Telegram chat ID
    
    Returns:
        Queue length after adding
    """
    redis = await get_redis()
    queue_key = f"msg_queue:{chat_id}"
    
    message_data = {
        "user_id": user_id,
        "text": text,
        "tg_chat_id": tg_chat_id
    }
    
    # Add to end of queue (RPUSH = append)
    queue_length = await redis.rpush(queue_key, json.dumps(message_data))
    
    # Set expiration to prevent stale queues (30 minutes)
    await redis.expire(queue_key, 1800)
    
    return queue_length


async def get_batch_messages(chat_id: UUID) -> List[Dict]:
    """
    Get all queued messages for a chat
    
    Args:
        chat_id: Chat UUID
    
    Returns:
        List of message dicts with user_id, text, tg_chat_id
    """
    redis = await get_redis()
    queue_key = f"msg_queue:{chat_id}"
    
    # Get all messages from queue (without removing yet)
    messages_json = await redis.lrange(queue_key, 0, -1)
    
    messages = []
    for msg_json in messages_json:
        try:
            messages.append(json.loads(msg_json))
        except json.JSONDecodeError:
            print(f"[REDIS-QUEUE] ⚠️ Failed to parse message: {msg_json}")
            continue
    
    return messages


async def clear_batch_messages(chat_id: UUID):
    """
    Clear all messages from queue after successful processing
    
    Args:
        chat_id: Chat UUID
    """
    redis = await get_redis()
    queue_key = f"msg_queue:{chat_id}"
    await redis.delete(queue_key)


async def set_processing_lock(chat_id: UUID, processing: bool, timeout_seconds: int = 600) -> bool:
    """
    Set processing lock for a chat (Redis-based)
    
    Args:
        chat_id: Chat UUID
        processing: True to lock, False to unlock
        timeout_seconds: Lock timeout (default 10 minutes)
        
    Returns:
        True if lock was acquired (when processing=True), always True for unlock
    """
    redis = await get_redis()
    lock_key = f"processing_lock:{chat_id}"
    
    if processing:
        # Use SETNX (set if not exists) for atomic lock acquisition
        # Returns 1 if key was set, 0 if key already existed
        result = await redis.set(lock_key, "1", ex=timeout_seconds, nx=True)
        return result is not None  # True if lock acquired, False if already locked
    else:
        # Clear lock
        await redis.delete(lock_key)
        return True


async def is_processing(chat_id: UUID) -> bool:
    """
    Check if a chat is currently being processed
    
    Args:
        chat_id: Chat UUID
    
    Returns:
        True if processing, False otherwise
    """
    redis = await get_redis()
    lock_key = f"processing_lock:{chat_id}"
    return await redis.exists(lock_key) > 0


async def get_queue_length(chat_id: UUID) -> int:
    """
    Get current queue length for a chat
    
    Args:
        chat_id: Chat UUID
    
    Returns:
        Number of messages in queue
    """
    redis = await get_redis()
    queue_key = f"msg_queue:{chat_id}"
    return await redis.llen(queue_key)

