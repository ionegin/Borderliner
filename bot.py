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

SUM_METRICS = ['productivity_hours', 'meditate_minutes', 'meals', 'smoked']
YES_NO_METRICS = ['yoga']

class Survey(StatesGroup):
    waiting_for_metrics = State()

class YesNoEdit(StatesGroup):
    waiting_for_value = State()

def get_logical_date(dt: datetime):
    local = dt + timedelta(hours=2)  # UTC+2
    if local.hour < 6:
        return (local - timedelta(days=1)).strftime("%Y-%m-%d")
    return local.strftime("%Y-%m-%d")

def val_to_ru(val):
    if val == "yes": return "Да"
    if val == "no": return "Нет"
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
    is_first_survey = not existing  # первый опрос дня если existing пустой

    if cfg["format"] == "yes_no":
        if existing_val is not None:
            # повторный опрос — показываем текущее + переключатель
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"✅ Оставить ({val_to_ru(existing_val)})", callback_data=f"m:{key}:keep"),
                InlineKeyboardButton(text=f"🔄 → {opposite_ru(existing_val)}", callback_data=f"m:{key}:{opposite_val(existing_val)}"),
            ]])
        else:
            # первый опрос — без пропуска
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Да", callback_data=f"m:{key}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"m:{key}:no"),
            ]])
        await bot.send_message(chat_id, f"📊 {base_question}", reply_markup=kb)

    elif cfg["format"] == "text":
        # текстовое поле — пропуск всегда доступен
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Пропустить", callback_data=f"m:{key}:skip")
        ]])
        await bot.send_message(chat_id, f"📊 {base_question}", reply_markup=kb)

    elif cfg["format"] == "time":
        if existing_val is not None:
            question = f"{base_question}\n(Сейчас: {existing_val})"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"✅ Оставить ({existing_val})", callback_data=f"m:{key}:keep")
            ]])
            await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
        else:
            await bot.send_message(chat_id, f"📊 {base_question} (формат ЧЧ:ММ)")

    else:
        # number
        # scale_10 (energy, anxiety, communication, racing_thoughts) — обязательные, без кнопок
        is_scale = cfg.get("format") == "number" and cfg.get("max") == 10 and cfg.get("min") == 0

        if key in SUM_METRICS:
            if "hours" in key:
                unit = "ч."
            elif "minutes" in key:
                unit = "мин."
            elif key == "smoked":
                unit = "шт."
            else:
                unit = "раз"
            if existing_val is not None:
                try:
                    val_display = round(float(existing_val), 1)
                except (ValueError, TypeError):
                    val_display = existing_val
            else:
                val_display = 0
            question = f"{base_question}\n(Сейчас: {val_display} {unit}. Сколько ПРИБАВИТЬ?)"
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"✅ Оставить ({val_display})", callback_data=f"m:{key}:keep")
            ]])
            await bot.send_message(chat_id, f"📊 {question}", reply_markup=kb)
        elif is_scale:
            # обязательные — без кнопок, просто вопрос
            await bot.send_message(chat_id, f"📊 {base_question} (0–10)")
        else:
            # прочие number — с пропуском
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Пропустить", callback_data=f"m:{key}:skip")
            ]])
            await bot.send_message(chat_id, f"📊 {base_question}", reply_markup=kb)

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
            if key in SUM_METRICS:
                existing = data.get("existing", {})
                existing_val = existing.get(key)
                if existing_val is not None:
                    try:
                        current_total = float(existing_val)
                    except (ValueError, TypeError):
                        current_total = 0
                    if current_total + val < 0:
                        await message.answer(f"⚠️ Нельзя вычесть больше, чем есть ({current_total}).")
                        return
                elif val < 0:
                    await message.answer("⚠️ Первая запись не может быть отрицательной.")
                    return
                if "max" in cfg and val > cfg["max"]:
                    raise ValueError()
            else:
                if "min" in cfg and val < cfg["min"]:
                    raise ValueError()
                if "max" in cfg and val > cfg["max"]:
                    raise ValueError()
            answers[key] = str(val)
        except ValueError:
            await message.answer(f"⚠️ Введи число от {cfg.get('min', 0)} до {cfg.get('max', '∞')}.")
            return
    elif cfg["format"] == "time":
        text = message.text.strip().replace('.', ':').replace('-', ':')
        try:
            parts = text.split(':')
            if len(parts) != 2:
                raise ValueError()
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError()
            answers[key] = f"{h:02d}:{m:02d}"
        except ValueError:
            await message.answer("⚠️ Введи время в формате ЧЧ:ММ (например 23:30)")
            return
    elif cfg["format"] == "text":
        answers[key] = message.text.strip()
    else:
        # yes_no приходит через callback, не через текст — игнорируем
        await message.answer("⚠️ Используй кнопки для ответа.")
        return

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

    local_now = message.date + timedelta(hours=2)  # UTC+2
    final_row = {
        "Date": logical_day,
        "created_at": local_now.strftime("%Y-%m-%d %H:%M"),
    }
    final_row.update(data["answers"])

    # Рассчитываем sleep_hours на основе sleep_time и wake_time
    sleep_t = final_row.get("sleep_time")
    if sleep_t is None:
        sleep_t = data.get("existing", {}).get("sleep_time")
    wake_t = final_row.get("wake_time")
    if wake_t is None:
        wake_t = data.get("existing", {}).get("wake_time")
    if sleep_t and wake_t:
        try:
            sp = sleep_t.split(":")
            wp = wake_t.split(":")
            s_min = int(sp[0]) * 60 + int(sp[1])
            w_min = int(wp[0]) * 60 + int(wp[1])
            diff = (w_min - s_min) % (24 * 60)
            final_row["sleep_hours"] = str(round(diff / 60, 1))
        except (ValueError, IndexError):
            pass

    print(f"[SURVEY] final_row={final_row}")
    storage.save_daily(message.chat.id, final_row)

    await message.answer(f"✅ Данные сохранены за {logical_day}!", reply_markup=render_menu('main'))
    await state.clear()

# ─── РЕДАКТИРОВАНИЕ YES-NO ───────────────────────────────────────────────────

@dp.message(F.text == "✏️ РЕДАКТИРОВАТЬ")
async def yesno_edit_button(message: types.Message):
    await message.answer("✏️ Что редактируем?", reply_markup=render_menu('yesno_edit'))

@dp.callback_query(F.data.startswith("ynedit:"))
async def handle_yesno_edit_select(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]

    if action == "cancel":
        await callback.message.edit_text("❌ Отменено")
        await bot.send_message(callback.message.chat.id, "Главное меню", reply_markup=render_menu('main'))
        return

    metric_key = action
    logical_day = get_logical_date(callback.message.date)
    current_val = storage.check_today_metric(callback.message.chat.id, metric_key, logical_day)

    await state.update_data(metric_key=metric_key, logical_day=logical_day)
    await state.set_state(YesNoEdit.waiting_for_value)

    question = METRICS[metric_key]["question"]

    if current_val is not None:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"✅ Оставить ({val_to_ru(current_val)})", callback_data=f"yn:{opposite_val(current_val)}:keep"),
            InlineKeyboardButton(text=f"🔄 → {opposite_ru(current_val)}", callback_data=f"yn:{opposite_val(current_val)}:set"),
        ]])
        await callback.message.edit_text(f"✏️ {question}\n(Сейчас: {val_to_ru(current_val)})", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да", callback_data="yn:yes:set"),
            InlineKeyboardButton(text="Нет", callback_data="yn:no:set"),
        ]])
        await callback.message.edit_text(f"✏️ {question}\n(Записей нет)", reply_markup=kb)

@dp.callback_query(YesNoEdit.waiting_for_value, F.data.startswith("yn:"))
async def handle_yesno_edit_val(callback: CallbackQuery, state: FSMContext):
    _, value, action = callback.data.split(":")
    data = await state.get_data()
    metric_key = data["metric_key"]
    logical_day = data["logical_day"]

    if action == "keep":
        await callback.message.edit_text("✅ Без изменений.")
    else:
        storage.update_first_row_yesno(callback.message.chat.id, logical_day, metric_key, value)
        await callback.message.edit_text(f"✅ {METRICS[metric_key]['question']} → {val_to_ru(value)}")

    await bot.send_message(callback.message.chat.id, "Главное меню", reply_markup=render_menu('main'))
    await state.clear()
    await callback.answer()

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