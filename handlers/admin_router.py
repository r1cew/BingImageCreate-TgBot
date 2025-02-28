from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, Filter
from utils.config import ADMINS_ID
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


admin_router = Router()

class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.id in ADMINS_ID

admin_router.message.filter(IsAdmin())

class State_wait(StatesGroup):
    wait_update = State()


@admin_router.message(Command("update"))
async def state_update_cookies(message: Message, state: FSMContext):
    U = message.text[len("/update"):].strip()
    if U:
        with open("U", "w", encoding="utf-8") as f:
            f.write(U)
        await message.reply("Обновлено.")
    else:
        kb = [[KeyboardButton(text="/cancel")]]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.reply("Введите значение U для обновления.", reply_markup=keyboard)

        await state.set_state(State_wait.wait_update)


@admin_router.message(State_wait.wait_update)
async def save_update(message: Message, state: FSMContext):
    with open("U", "w", encoding="utf-8") as f:
        f.write(message.text)
    await message.reply("Обновлено.")
    await state.clear()


@admin_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext):
    await state.clear()
    kb = [[KeyboardButton(text="/update")]]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "Действие отменено",
        reply_markup=keyboard
    )

@admin_router.message(Command("admin"))
async def state_update_cookies(message: Message):
    kb = [
        [KeyboardButton(text="/update")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Команды", reply_markup=keyboard)

