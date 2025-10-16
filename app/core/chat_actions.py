"""
Chat action indicator manager
Shows persistent typing/upload_photo indicators until tasks complete
"""
import asyncio
from aiogram import Bot


class ChatActionManager:
    """Manages persistent chat actions until tasks complete"""
    
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self._task = None
        self._stop_event = asyncio.Event()
    
    async def start(self, action: str = "typing"):
        """Start showing action repeatedly"""
        # Stop any existing action first
        if self._task and not self._task.done():
            await self.stop()
        
        self._stop_event.clear()
        self._task = asyncio.create_task(self._action_loop(action))
    
    async def stop(self):
        """Stop showing action"""
        if self._task:
            self._stop_event.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _action_loop(self, action: str):
        """Send action every 4.5s until stopped"""
        while not self._stop_event.is_set():
            try:
                await self.bot.send_chat_action(self.chat_id, action)
            except Exception as e:
                # Silently ignore errors (chat might be deleted, etc.)
                pass
            
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=4.5)
            except asyncio.TimeoutError:
                continue

