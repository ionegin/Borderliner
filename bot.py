import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta

from config import BOT_TOKEN, WEBHOOK_BASE_URL
from metrics import METRICS, get_measurement_config
from storage.sheets import GoogleSheetsStorage
from menu import render_menu
from handlers import handle_start, handle_menu, handle_edit_history, handle_edit_date_callback

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()
storage = GoogleSheetsStorage()

SUM_METRICS = ['sleep_hours', 'productivity_hours', 'meditate_minutes', 'meals']
CHANGE_METRICS = ['smoked', 'yoga']

class Survey(StatesGroup):
    waiting_for_metrics = State()

def get_logical_date(dt: datetime):
    # Порог 6 утра
    if dt.hour < 6:
        return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")

async def ask_next_metric(chat_id: int, state: FSMContext, idx: int):
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    if idx >= len(metrics_to_ask): return False
    
    key = metrics_to_ask[idx]
    metric = METRICS[key]
    cfg = get_measurement_config(key)
    base_question = metric["question"]
    
    # Получаем накопленное значение за ЛОГИЧЕСКИЙ день
    l_date = data.get("logical_date")
    existing_val = storage.check_today_metric(chat_id, key, l_date)
    
    question = base_question
    buttons_row = []
    
    if existing_val is not None:
        if key in SUM_METRICS:
            unit = "ч." if "hours" in key else ("мин." if "minutes" in key else "раз")
            val_display = round(float(existing_val), 1) if isinstance(existing_val, (int, float)) else existing_val
            question = f"{base_question}\n(Уже записано: {val_display} {unit}. Сколько ПРИБАВИТЬ?)"
            # Кнопка "Оставить"
            buttons_row.append(InlineKeyboardButton(text="✅ Оставить", callback_data=f"m:{key}:keep"))
        elif key in CHANGE_METRICS:
            question = f"{base_question}\n(Текущий ответ: {existing_val}. Изменить?)"
            buttons_row.append(InlineKeyboardButton(text="✅ Оставить", callback_data=f"m:{key}:keep"))

    if cfg["format"] == "yes_no":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"m:{key}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"m:{key}:no")
            ],
            buttons_row if buttons_row else []
        ])
        await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
    elif cfg["format"] == "text":
        kb_rows = [[InlineKeyboardButton(text="Пропустить", callback_data=f"m:{key}:skip")]]
        if buttons_row:
            kb_rows.append(buttons_row)
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
    else:
        if buttons_row:
            kb = InlineKeyboardMarkup(inline_keyboard=[buttons_row])
            await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
        else:
            await bot.send_message(chat_id, f"📊 {question}")
    return True

@dp.message(Command("daily"))
async def start_daily(message: types.Message, state: FSMContext):
    l_date = get_logical_date(message.date)
    await state.update_data(metrics_to_ask=list(METRICS.keys()), answers={}, current_idx=0, logical_date=l_date)
    await state.set_state(Survey.waiting_for_metrics)
    await ask_next_metric(message.chat.id, state, 0)

@dp.message(Survey.waiting_for_metrics, F.text)
async def handle_metrics_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx, answers = data["current_idx"], data["answers"]
    key = data["metrics_to_ask"][idx]
    
    answers[key] = message.text.strip()
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    if not await ask_next_metric(message.chat.id, state, idx):
        await finish_survey(message, state)

@dp.callback_query(Survey.waiting_for_metrics, F.data.startswith("m:"))
async def handle_metrics_callback(callback: CallbackQuery, state: FSMContext):
    _, key, value = callback.data.split(":")
    data = await state.get_data()
    answers, idx = data["answers"], data["current_idx"]
    
    if value == "keep":
        # Не записываем ничего (оставляем как есть)
        answers[key] = None
    elif value == "skip":
        answers[key] = None
    else:
        answers[key] = value
    
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    await callback.answer()
    if not await ask_next_metric(callback.message.chat.id, state, idx):
        await finish_survey(callback.message, state)

async def finish_survey(message: types.Message, state: FSMContext):
    data = await state.get_data()
    created_at = message.date 
    logical_day = data.get("logical_date")
    
    final_row = {
        "Date": logical_day,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": str(message.chat.id)
    }
    final_row.update(data["answers"])
    
    storage.save_daily(message.chat.id, final_row)
    
    # Показываем главное меню после опроса
    keyboard = render_menu('main')
    await message.answer(f"✅ Данные сохранены за {logical_day}!", reply_markup=keyboard)
    await state.clear()

# Регистрируем handlers из handlers.py
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await handle_start(message)

@dp.message(F.text == "📝 МЕНЮ")
async def menu_button(message: types.Message):
    await handle_menu(message)

@dp.message(F.text == "📅 ИСТОРИЯ")
async def history_button(message: types.Message, state: FSMContext):
    await handle_edit_history(message, state)

@dp.message(F.text == "📊 ПРОЙТИ ОПРОС")
async def daily_button(message: types.Message, state: FSMContext):
    await start_daily(message, state)

@dp.callback_query(F.data.startswith("edit_date:"))
async def edit_date_callback(callback: CallbackQuery, state: FSMContext):
    await handle_edit_date_callback(callback, state)

if __name__ == "__main__":
    dp.run_polling(bot)
