from aiogram import Router, F
from aiogram.types import Message, InputMediaPhoto

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from BingImageCreator import generate_images

image_router = Router()


class WaitGeneration(StatesGroup):
    processing = State()


@image_router.message(WaitGeneration.processing)
async def processing(message: Message):
    await message.answer("Пожалуйста, подождите, пока завершится предыдущая генерация.")


@image_router.message(F.text)
async def generation(message: Message, state: FSMContext):
    await state.set_state(WaitGeneration.processing)
    

    notification = None
    async def my_status_callback(status: str):
        nonlocal notification
 
        if status == "STATE_SENDING_REQUEST":
            notification = await message.answer("Запрос отправлен. Ожидание ответа от сервера...")  
        elif status == "STATE_WAITING_FOR_RESULTS":
            await notification.edit_text("Генерация изображений началась. Это может занять около 30 секунд...")
        elif status == "STATE_PARSING_RESULTS":
            pass
        elif status == "STATE_RESULTS_RECEIVED":
            await notification.delete()
        else:
            await notification.edit_text(status)


    prompt = message.text 
    try:
        links = await generate_images(prompt, cookie_file="U", status_callback=my_status_callback)
        
        media_group = [InputMediaPhoto(media=img_url) for img_url in links]
        await message.reply_media_group(media_group)

    except Exception as e:
        print(f"An error occurred: {e}")

    await state.clear()