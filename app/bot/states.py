"""
FSM states for the bot
"""
from aiogram.fsm.state import State, StatesGroup


class ImageGeneration(StatesGroup):
    """States for image generation flow"""
    waiting_for_prompt = State()
    waiting_for_another = State()  # After image generated, waiting for another request

