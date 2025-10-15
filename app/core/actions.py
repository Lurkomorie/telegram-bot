"""
Chat action helpers (typing indicator, upload_photo indicator)
"""
import asyncio
from typing import Literal
from aiogram import Bot
from contextlib import asynccontextmanager


ActionType = Literal["typing", "upload_photo", "upload_video", "record_video", "upload_document"]


@asynccontextmanager
async def send_action_repeatedly(
    bot: Bot,
    chat_id: int,
    action: ActionType = "typing",
    interval: float = 4.5
):
    """
    Context manager that sends chat action repeatedly until exit
    
    Usage:
        async with send_action_repeatedly(bot, chat_id, "typing"):
            # Do long-running task
            result = await some_api_call()
        # Action automatically stops when exiting context
    
    Args:
        bot: Aiogram Bot instance
        chat_id: Telegram chat ID
        action: Chat action type
        interval: Seconds between action sends (Telegram requires <5s for persistent indicator)
    """
    task = None
    stop_event = asyncio.Event()
    
    async def action_loop():
        """Send action repeatedly until stopped"""
        try:
            while not stop_event.is_set():
                try:
                    await bot.send_chat_action(chat_id, action)
                except Exception as e:
                    print(f"[ACTION] Error sending {action}: {e}")
                
                # Wait for interval or until stop_event is set
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
    
    try:
        # Start the action loop
        task = asyncio.create_task(action_loop())
        yield
    finally:
        # Stop the action loop
        stop_event.set()
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


