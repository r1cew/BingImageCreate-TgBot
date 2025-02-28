import asyncio
from aiogram import Bot, Dispatcher

from handlers import start_handler, image_handler, admin_router
from utils.config import API_TOKEN

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    dp.include_router(admin_router.admin_router)
    dp.include_router(start_handler.start_router)
    dp.include_router(image_handler.image_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=None)

if __name__ == '__main__':
    asyncio.run(main())


        