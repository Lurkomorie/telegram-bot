"""
Bot middleware for handling cross-cutting concerns like service availability
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from app.settings import settings, get_ui_text
from app.core.rate import get_redis

class ServiceUnavailableMiddleware(BaseMiddleware):
    """
    Middleware to intercept all updates when service is unavailable
    and send a one-time message to users
    """
    
    REDIS_KEY_PREFIX = "service_unavailable_notified:"
    REDIS_TTL = 86400  # 24 hours
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Check if service is unavailable and handle accordingly"""
        
        # If service is available, process normally
        if not settings.SERVICE_UNAVAILABLE:
            return await handler(event, data)
        
        # Service is unavailable - extract user_id from the event
        user_id = None
        message = None
        
        if event.message:
            user_id = event.message.from_user.id
            message = event.message
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
            message = event.callback_query.message
        
        # If we couldn't extract user_id, just block silently
        if not user_id or not message:
            return None
        
        # Check if we've already notified this user
        redis = await get_redis()
        redis_key = f"{self.REDIS_KEY_PREFIX}{user_id}"
        
        try:
            already_notified = await redis.get(redis_key)
            
            if not already_notified:
                # First time seeing this user - send notification
                service_message = get_ui_text("system.service_unavailable")
                await message.answer(service_message)
                
                # Mark user as notified
                await redis.setex(redis_key, self.REDIS_TTL, "1")
                print(f"[SERVICE-UNAVAILABLE] Notified user {user_id}")
            else:
                # User already notified - silently ignore
                print(f"[SERVICE-UNAVAILABLE] User {user_id} already notified, ignoring")
            
            # If this was a callback query, answer it to remove the loading state
            if event.callback_query:
                await event.callback_query.answer()
        
        except Exception as e:
            print(f"[SERVICE-UNAVAILABLE] Error handling notification for user {user_id}: {e}")
        
        # Don't process the actual handler - stop here
        return None

