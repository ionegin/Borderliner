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
from handlers import handle_start
from services.transcription import transcribe_voice
import os

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()
storage = GoogleSheetsStorage()

SUM_METRICS = ['sleep_hours', 'productivity_hours', 'meditate_minutes', 'meals']
CHANGE_METRICS = ['smoked', 'yoga']

class Survey(StatesGroup):
    waiting_for_metrics = State()

class QuickEdit(StatesGroup):
    waiting_for_value = State()

def get_logical_date(dt: datetime):
    if dt.hour < 6:
        return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")

def val_to_ru(key, val):
    if val == "yes":
        return "Да"
    if val == "no":
        return "Нет"
    return val

def opposite_val(val):
    return "no" if val == "yes" else "yes"

def opposite_ru(val):
    return "Нет" if val == "yes" else "Да"

async def ask_next_metric(chat_id: int, state: FSMContext, idx: int):
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    if idx >= len(metrics_to_ask):
        return False

    key = metrics_to_ask[idx]
    metric = METRICS[key]
    cfg = get_measurement_config(key)
    base_question = metric["question"]

    existing = data.get("existing", {})
    existing_val = existing.get(key)

    if cfg["format"] == "yes_no":
        if existing_val is not None:
            val_ru = val_to_ru(key, existing_val)
            opp_ru = opposite_ru(existing_val)
            opp_val = opposite_val(existing_val)
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"✅ Оставить ({val_ru})", callback_data=f"m:{key}:keep"),
                InlineKeyboardButton(text=f"🔄 → {opp_ru}", callback_data=f"m:{key}:{opp_val}"),
            ]])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Да", callback_data=f"m:{key}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"m:{key}:no"),
            ]])
        await bot.send_message(chat_id, f"📊 {base_question}", reply_markup=kb)

    elif cfg["format"] == "text":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Пропустить", callback_data=f"m:{key}:skip")
        ]])
        await bot.send_message(chat_id, f"📊 {base_question}", reply_markup=kb)

    else:
        # number
        if existing_val is not None and key in SUM_METRICS:
            unit = "ч." if "hours" in key else ("мин." if "minutes" in key else "раз")
            try:
                val_display = round(float(existing_val), 1)
            except (ValueError, TypeError):
                val_display = existing_val
            question = f"{base_question}\n(Уже записано: {val_display} {unit}. Сколько ПРИБАВИТЬ?)"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Оставить", callback_data=f"m:{key}:keep")
            ]])
            await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
        else:
            await bot.send_message(chat_id, f"📊 {base_question}")

    return True

# ─── СТАРТ ───────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await handle_start(message)

# ─── ОПРОС ───────────────────────────────────────────────────────────────────

@dp.message(Command("daily"))
async def start_daily(message: types.Message, state: FSMContext):
    await _launch_survey(message, state)

@dp.message(F.text == "📊 ПРОЙТИ ОПРОС")
async def daily_button(message: types.Message, state: FSMContext):
    await _launch_survey(message, state)

async def _launch_survey(message: types.Message, state: FSMContext):
    l_date = get_logical_date(message.date)
    existing = storage.get_day_data(message.chat.id, l_date)
    print(f"[SURVEY] launching for {message.chat.id}, date={l_date}, existing={existing}")
    await state.update_data(
        metrics_to_ask=list(METRICS.keys()),
        answers={},
        current_idx=0,
        logical_date=l_date,
        existing=existing,
    )
    await state.set_state(Survey.waiting_for_metrics)
    await ask_next_metric(message.chat.id, state, 0)

@dp.message(Survey.waiting_for_metrics, F.text)
async def handle_metrics_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx, answers = data["current_idx"], data["answers"]
    key = data["metrics_to_ask"][idx]
    cfg = get_measurement_config(key)

    if cfg["format"] == "number":
        try:
            val = float(message.text.strip().replace(',', '.'))
            if "min" in cfg and val < cfg["min"]:
                raise ValueError()
            if "max" in cfg and val > cfg["max"]:
                raise ValueError()
            answers[key] = str(val)
        except ValueError:
            await message.answer(f"⚠️ Введи число от {cfg.get('min', 0)} до {cfg.get('max', '∞')}.")
            return
    else:
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

    answers[key] = None if value in ("keep", "skip") else value

    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    await callback.answer()
    if not await ask_next_metric(callback.message.chat.id, state, idx):
        await finish_survey(callback.message, state)

async def finish_survey(message: types.Message, state: FSMContext):
    data = await state.get_data()
    logical_day = data.get("logical_date")

    print(f"[SURVEY] logical_day={logical_day}")
    print(f"[SURVEY] raw answers={data['answers']}")

    final_row = {
        "Date": logical_day,
        "created_at": message.date.strftime("%Y-%m-%d %H:%M:%S"),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": str(message.chat.id),
    }
    final_row.update(data["answers"])

    print(f"[SURVEY] final_row={final_row}")
    storage.save_daily(message.chat.id, final_row)

    await message.answer(f"✅ Данные сохранены за {logical_day}!", reply_markup=render_menu('main'))
    await state.clear()

# ─── БЫСТРАЯ ЗАПИСЬ ──────────────────────────────────────────────────────────

@dp.message(F.text == "⚡ БЫСТРАЯ ЗАПИСЬ")
async def quick_edit_button(message: types.Message):
    await message.answer("⚡ Что записать?", reply_markup=render_menu('quick_edit'))

@dp.callback_query(F.data.startswith("qedit:"))
async def handle_quick_edit_selection(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Отменено")
        await bot.send_message(callback.message.chat.id, "Главное меню", reply_markup=render_menu('main'))
        return

    metric_key = action
    cfg = get_measurement_config(metric_key)
    question = METRICS[metric_key]["question"]

    await state.update_data(metric_key=metric_key)
    await state.set_state(QuickEdit.waiting_for_value)

    if cfg["format"] == "yes_no":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да", callback_data="qval:yes"),
            InlineKeyboardButton(text="Нет", callback_data="qval:no"),
        ]])
        await callback.message.edit_text(f"⚡ {question}", reply_markup=kb)
    else:
        await callback.message.edit_text(f"⚡ {question}")

@dp.callback_query(QuickEdit.waiting_for_value, F.data.startswith("qval:"))
async def handle_quick_edit_yesno_val(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[1]
    await finish_quick_edit(callback.message, state, val, from_callback=True)
    await callback.answer()

@dp.message(QuickEdit.waiting_for_value, F.text)
async def handle_quick_edit_text_val(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cfg = get_measurement_config(data["metric_key"])

    if cfg["format"] == "number":
        try:
            val = float(message.text.strip().replace(',', '.'))
            if "min" in cfg and val < cfg["min"]:
                raise ValueError()
            if "max" in cfg and val > cfg["max"]:
                raise ValueError()
            val = str(val)
        except ValueError:
            await message.answer(f"⚠️ Введи число от {cfg.get('min', 0)} до {cfg.get('max', '∞')}.")
            return
    else:
        val = message.text.strip()

    await finish_quick_edit(message, state, val, from_callback=False)

async def finish_quick_edit(message: types.Message, state: FSMContext, value: str, from_callback: bool):
    data = await state.get_data()
    metric_key = data.get("metric_key")
    logical_day = get_logical_date(message.date)

    final_row = {
        "Date": logical_day,
        "created_at": message.date.strftime("%Y-%m-%d %H:%M:%S"),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": str(message.chat.id),
        metric_key: value,
    }
    storage.save_daily(message.chat.id, final_row)

    text = f"✅ {METRICS[metric_key]['question']} → {val_to_ru(metric_key, value)} (за {logical_day})"
    if from_callback:
        await message.edit_text(text)
        await bot.send_message(message.chat.id, "Главное меню", reply_markup=render_menu('main'))
    else:
        await message.answer(text, reply_markup=render_menu('main'))
    await state.clear()

# ─── ГОЛОСОВЫЕ И ТЕКСТОВЫЕ ЗАМЕТКИ ──────────────────────────────────────────

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    print(f"[VOICE] received from {message.chat.id}")
    path = f"voice_{message.voice.file_id}.ogg"
    try:
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, path)
        text = await transcribe_voice(path)
        print(f"[VOICE] transcribed: {text}")
        storage.save_note(
            user_id=message.chat.id,
            text=text,
            is_voice=True,
            duration=message.voice.duration,
            telegram_ts=message.date,
            uploaded_at=datetime.now(),
        )
        await message.answer(f"🎙️ Записал заметку:\n_{text}_", parse_mode="Markdown")
    except Exception as e:
        print(f"[VOICE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Не удалось расшифровать голосовое")
    finally:
        if os.path.exists(path):
            os.remove(path)

@dp.message(F.text)
async def handle_text_note(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        text = message.text
        print(f"[NOTE] saving: {text[:50]}")
        storage.save_note(
            user_id=message.chat.id,
            text=text,
            is_voice=False,
            telegram_ts=message.date,
            uploaded_at=datetime.now(),
        )
        await message.answer("📝 Заметка сохранена.")

if __name__ == "__main__":
    dp.run_polling(bot)