from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from utils.texts import START_MESSAGE


start_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        START_MESSAGE,  
        parse_mode="HTML"
    )