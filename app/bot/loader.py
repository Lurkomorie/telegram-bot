"""
Bot and Dispatcher initialization
"""
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from app.settings import settings

# Create bot instance
bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)

# Create dispatcher
dp = Dispatcher()

# Create main router (all handlers will be registered here)
router = Router()

# Register router with dispatcher
dp.include_router(router)


