"""
Redis-based rate limiting (sliding window)
"""
import time
from typing import Tuple
import redis.asyncio as aioredis
from app.settings import settings


# Global Redis connection
_redis_client = None


async def get_redis():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        # Simple connection for Railway Redis (no SSL needed)
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def check_rate_limit(
    user_id: int,
    limit_type: str,
    max_requests: int,
    window_seconds: int = 60
) -> Tuple[bool, int]:
    """
    Check if user is within rate limit using sliding window
    
    Args:
        user_id: Telegram user ID
        limit_type: Type of limit (e.g., "text", "image")
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds (default 60 = per minute)
    
    Returns:
        Tuple of (is_allowed, requests_count)
    """
    redis = await get_redis()
    key = f"rate:{limit_type}:{user_id}"
    
    now = time.time()
    window_start = now - window_seconds
    
    # Remove old entries outside the window
    await redis.zremrangebyscore(key, 0, window_start)
    
    # Count current requests in window
    count = await redis.zcard(key)
    
    if count >= max_requests:
        return False, count
    
    # Add current request
    await redis.zadd(key, {str(now): now})
    
    # Set expiration (cleanup)
    await redis.expire(key, window_seconds + 10)
    
    return True, count + 1


async def close_redis():
    """Close Redis connection (call on shutdown)"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


