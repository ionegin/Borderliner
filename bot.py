import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, WEBHOOK_BASE_URL
from metrics import METRICS, get_measurement_config
from storage.sheets import GoogleSheetsStorage
from services.transcription import transcribe_voice

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()
storage = GoogleSheetsStorage()
scheduler = AsyncIOScheduler()

# Метрики, для которых показываем накопленное значение
SUM_METRICS = ['sleep_hours', 'productivity_hours', 'meditate_minutes']
CHANGE_METRICS = ['smoked', 'yoga']

class Survey(StatesGroup):
    waiting_for_metrics = State()

async def ask_next_metric(chat_id: int, state: FSMContext, idx: int):
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    if idx >= len(metrics_to_ask): return False
    
    key = metrics_to_ask[idx]
    metric = METRICS[key]
    cfg = get_measurement_config(key)
    base_question = metric["question"]
    
    # Проверка существующих данных за сегодня
    existing_val = storage.check_today_metric(chat_id, key)
    
    # Формируем динамический текст вопроса, сохраняя оригинальный вопрос
    if existing_val is not None and str(existing_val).strip() != "":
        if key in SUM_METRICS:
            unit = "ч." if "hours" in key else "мин."
            question = f"{base_question}\n(Уже записано: {existing_val} {unit}. Сколько ПРИБАВИТЬ?)"
        elif key in CHANGE_METRICS:
            question = f"{base_question}\n(Твой текущий ответ: {existing_val}. Изменить?)"
        else:
            question = base_question
    else:
        question = base_question

    if cfg["format"] == "yes_no":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да", callback_data=f"m:{key}:yes"),
            InlineKeyboardButton(text="Нет", callback_data=f"m:{key}:no")
        ]])
        await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
    elif cfg["format"] == "text":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Пропустить", callback_data=f"m:{key}:skip")
        ]])
        await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
    else:
        await bot.send_message(chat_id, f"📊 {question}")
    return True

@dp.message(Command("daily"))
async def start_daily(message: types.Message, state: FSMContext):
    await state.update_data(metrics_to_ask=list(METRICS.keys()), answers={}, current_idx=0)
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
    
    answers[key] = None if value == "skip" else value
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    await callback.answer()
    if not await ask_next_metric(callback.message.chat.id, state, idx):
        await finish_survey(callback.message, state)

async def finish_survey(message: types.Message, state: FSMContext):
    data = await state.get_data()
    now = datetime.now()
    
    # Date - в первой колонке, как ты просил
    final_row = {
        "Date": now.strftime("%Y-%m-%d"),
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "uploaded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": message.chat.id
    }
    final_row.update(data["answers"])
    
    storage.save_daily(message.chat.id, final_row)
    
    await message.answer("✅ Данные добавлены!")
    await state.clear()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🧠 Бот запущен. Жми /daily")

if __name__ == "__main__":
    if not WEBHOOK_BASE_URL:
        dp.run_polling(bot)