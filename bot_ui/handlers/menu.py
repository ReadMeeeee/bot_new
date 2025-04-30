from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from bot_ui.keyboards.keyboards import (
    start_main,
    start_main_base,
    start_main_group,
    start_main_requests,
    start_main_ai,
    help_main,
    help_main_base,
    help_main_group,
    help_main_requests,
    help_main_ai,
)
from bot_ui.keyboards.keyboards_config import MENU_SECTIONS


menu_router = Router()


class MenuStates(StatesGroup):
    waiting_for_input = State()


# region Меню start
@menu_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Выберите раздел меню:", reply_markup=start_main)


@menu_router.callback_query(lambda c: c.data and c.data.startswith("menu:"))
async def process_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    _, section, *rest = callback.data.split(":")

    # переход в help из базовых команд
    if section == "base" and rest and rest[0] == "help":
        await callback.message.edit_text(
            "Справка: выберите раздел:",
            reply_markup=help_main
        )
        return

    menu_map: dict[str, tuple[str, types.InlineKeyboardMarkup]] = {
        "main":     ("Выберите раздел меню:",    start_main),
        "base":     ("Базовые команды:",         start_main_base),
        "group":    ("Управление группой:",      start_main_group),
        "requests": ("Групповые запросы:",       start_main_requests),
        "ai":       ("Запросы через ИИ:",        start_main_ai)
    }

    if section not in menu_map:
        return

    text, kb = menu_map[section]
    if rest:
        text = f"Вы выбрали: {rest[0]}"
        # сохраняем в FSMContext и переключаемся в режим ввода
        await state.update_data(chosen=rest[0])
        await state.set_state(MenuStates.waiting_for_input)

    await callback.message.edit_text(text, reply_markup=kb)


@menu_router.message(MenuStates.waiting_for_input)
async def handle_menu_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chosen = data.get("chosen")
    await message.answer(
        f"Для пункта «{chosen}» вы ввели:\n\n{message.text}"
    )
    await state.clear()
# endregion


# region Меню help
@menu_router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Справка: выберите раздел:", reply_markup=help_main)


@menu_router.callback_query(lambda c: c.data and c.data.startswith("help:"))
async def process_help(callback: types.CallbackQuery):
    await callback.answer()

    _, section, *rest = callback.data.split(":")

    if rest:
        key = rest[0]
        desc = next(
            (d for (_t, k, d) in MENU_SECTIONS[section]["items"] if k == key),
            "Описание отсутствует."
        )
        detail_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [ types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"help:{section}") ]
        ])
        await callback.message.edit_text(desc, reply_markup=detail_kb)
        return

    # вывод основного или вложенного меню помощи
    if section == "main":
        title, kb = "Справка: выберите раздел:", help_main
    else:
        title = f"Справка по «{MENU_SECTIONS[section]['title']}»:"
        kb_map = {
            "base":    help_main_base,
            "group":   help_main_group,
            "requests":help_main_requests,
            "ai":      help_main_ai
        }
        kb = kb_map[section]

    await callback.message.edit_text(title, reply_markup=kb)
# endregion
