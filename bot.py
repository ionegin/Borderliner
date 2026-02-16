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
from metrics import METRICS, MEASUREMENT_TYPES, get_measurement_config
from storage.sheets import GoogleSheetsStorage
from services.transcription import transcribe_voice

logging.basicConfig(level=logging.INFO)

if BOT_TOKEN:
    bot = Bot(token=BOT_TOKEN)
else:
    bot = None

dp = Dispatcher()
storage = GoogleSheetsStorage()
scheduler = AsyncIOScheduler()

# СИНХРОНИЗИРОВАНО С metrics.py
TIME_METRICS = ['sleep_hours', 'productivity_hours', 'meditate_minutes']

class Survey(StatesGroup):
    waiting_for_metrics = State()
    confirm_update = State()

def get_yes_no_keyboard(metric_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"metric:{metric_key}:yes"),
            InlineKeyboardButton(text="Нет", callback_data=f"metric:{metric_key}:no"),
        ]
    ])

def get_update_mode_keyboard(metric_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Перезаписать", callback_data=f"mode:overwrite:{metric_key}"),
            InlineKeyboardButton(text="Добавить время", callback_data=f"mode:add:{metric_key}"),
        ],
        [InlineKeyboardButton(text="Отмена", callback_data="mode:cancel")]
    ])

async def ask_next_metric(chat_id: int, state: FSMContext, idx: int):
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    if idx >= len(metrics_to_ask):
        return False
    
    key = metrics_to_ask[idx]
    metric = METRICS[key]
    measurement_cfg = get_measurement_config(key)
    question = metric["question"]
    
    if measurement_cfg["format"] == "yes_no":
        await bot.send_message(chat_id, f"📊 {question}", reply_markup=get_yes_no_keyboard(key))
    elif measurement_cfg["format"] == "text":
        await bot.send_message(chat_id, f"📊 {question}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data=f"metric:{key}:skip")]
        ]))
    else:
        min_val = measurement_cfg.get("min")
        max_val = measurement_cfg.get("max")
        rng = f" ({min_val}-{max_val})" if min_val is not None else ""
        await bot.send_message(chat_id, f"📊 {question}{rng}")
    return True

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🧠 **Borderliner System Online**\n\n/daily — Заполнить метрики")

@dp.message(Command("daily"))
async def start_daily(message: types.Message, state: FSMContext):
    metrics_to_ask = list(METRICS.keys())
    await state.update_data(metrics_to_ask=metrics_to_ask, answers={}, current_idx=0)
    await state.set_state(Survey.waiting_for_metrics)
    await ask_next_metric(message.chat.id, state, 0)

def _validate_number(value: str, cfg: dict) -> "tuple[bool, str]":
    try:
        n = float(value.replace(',', '.'))
    except ValueError:
        return False, "Введи число."
    lo, hi = cfg.get("min"), cfg.get("max")
    if lo is not None and n < lo: return False, f"Минимум {lo}."
    if hi is not None and n > hi: return False, f"Максимум {hi}."
    return True, ""

@dp.message(Survey.waiting_for_metrics, F.text)
async def handle_metrics_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    answers = data["answers"]
    idx = data["current_idx"]
    key = metrics_to_ask[idx]
    measurement_cfg = get_measurement_config(key)
    
    val_str = message.text.strip()
    if measurement_cfg["format"] != "text":
        ok, err = _validate_number(val_str, measurement_cfg)
        if not ok:
            await message.answer(f"❌ {err}")
            return

    # Логика проверки на повтор
    if key in TIME_METRICS:
        existing_val = storage.check_today_metric(message.from_user.id, key)
        if existing_val is not None:
            await state.update_data(temp_value=val_str)
            await message.answer(
                f"📊 За сегодня уже записано {key}: {existing_val}.\nЧто сделать с новым значением {val_str}?",
                reply_markup=get_update_mode_keyboard(key)
            )
            await state.set_state(Survey.confirm_update)
            return

    answers[key] = val_str
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    if not await ask_next_metric(message.chat.id, state, idx):
        storage.save_daily(message.from_user.id, answers)
        await message.answer("✅ Записано!")
        await state.clear()

@dp.callback_query(Survey.confirm_update, F.data.startswith("mode:"))
async def handle_update_mode(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    mode = parts[1]
    metric_key = parts[2]
    
    data = await state.get_data()
    temp_value = data['temp_value']
    answers = data['answers']
    idx = data['current_idx']
    
    if mode == "add":
        existing = storage.check_today_metric(callback.from_user.id, metric_key)
        answers[metric_key] = str(float(existing or 0) + float(temp_value))
    elif mode == "overwrite":
        answers[metric_key] = temp_value
    
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    await state.set_state(Survey.waiting_for_metrics)
    await callback.message.delete()
    
    if not await ask_next_metric(callback.message.chat.id, state, idx):
        storage.save_daily(callback.from_user.id, answers)
        await callback.message.answer("✅ Записано!")
        await state.clear()

@dp.callback_query(Survey.waiting_for_metrics, F.data.startswith("metric:"))
async def handle_metrics_callback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    _, key, value = parts
    data = await state.get_data()
    answers, idx = data["answers"], data["current_idx"]
    
    answers[key] = None if value == "skip" else value
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    await callback.answer()
    if not await ask_next_metric(callback.message.chat.id, state, idx):
        storage.save_daily(callback.from_user.id, answers)
        await callback.message.answer("✅ Записано!")
        await state.clear()

# Остальные обработчики (voice/text) остаются без изменений...