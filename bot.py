import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers.register import register_router
from handlers.user import user_router
from handlers.hr import hr_router


async def main():
    init_db()
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    dp.include_router(register_router)
    dp.include_router(hr_router)
    dp.include_router(user_router)

    print("🤖 Бот запущено")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зупинено вручну")
