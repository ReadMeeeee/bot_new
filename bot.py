import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import API_TG

from bot_ui.handlers.menu       import menu_router
from bot_ui.commands.base       import base_router
from bot_ui.commands.management import management_router
from bot_ui.commands.requests   import requests_router

from bot_api.Database.models import engine, Base


async def init_db():
    """
    Создаёт все таблицы из описанных в Base.metadata,
    если они ещё не существуют.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("База данных инициализирована")


async def drop_db():
    """
    Удаляет все таблицы, описанные в Base.metadata.
    После вызова БД будет пуста (но файл останется).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("База данных очищена")


async def main():
    await drop_db()
    await init_db()

    bot = Bot(token=API_TG)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(menu_router)
    dp.include_router(base_router)
    dp.include_router(management_router)
    dp.include_router(requests_router)

    # 3) Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
