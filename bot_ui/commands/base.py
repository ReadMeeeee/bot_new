from aiogram import Router, types
from aiogram.filters import Command

base_router = Router()

@base_router.message(Command("start"))
async def cmd_start_again(message: types.Message):
    # можно редиректить в menu_router или просто показывать стартовую клавиатуру
    from bot_ui.handlers.menu import start_main
    await message.answer("Выберите раздел меню:", reply_markup=start_main)

@base_router.message(Command("help"))
async def cmd_help(message: types.Message):
    from bot_ui.handlers.menu import help_main
    await message.answer("Справка по командам", reply_markup=help_main)

@base_router.message(Command("about"))
async def cmd_about(message: types.Message):
    await message.answer("Данный бот - ассистент старосты.\nПомогает заниматься управлением группы.\nПодкреплен ИИ.")
