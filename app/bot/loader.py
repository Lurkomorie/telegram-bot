"""
Bot and Dispatcher initialization
"""
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from app.settings import settings

# Create bot instance
bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)

# Create storage for FSM
storage = MemoryStorage()

# Create dispatcher with storage
dp = Dispatcher(storage=storage)

# Register middleware
from app.bot.middleware import ServiceUnavailableMiddleware
dp.update.middleware(ServiceUnavailableMiddleware())

# Create main router (all handlers will be registered here)
router = Router()

# Register router with dispatcher
dp.include_router(router)

