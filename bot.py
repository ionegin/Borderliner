import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, METRICS, WEBHOOK_BASE_URL
from storage.sheets import GoogleSheetsStorage
from services.transcription import transcribe_voice

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
storage = GoogleSheetsStorage()
scheduler = AsyncIOScheduler()

class Survey(StatesGroup):
    waiting_for_metrics = State()


def get_yes_no_keyboard(metric_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"metric:{metric_key}:yes"),
            InlineKeyboardButton(text="Нет", callback_data=f"metric:{metric_key}:no"),
        ]
    ])


async def ask_next_metric(chat_id: int, state: FSMContext, idx: int):
    """Отправляет следующий вопрос (текстом или с кнопками)."""
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    if idx >= len(metrics_to_ask):
        return False
    key = metrics_to_ask[idx]
    cfg = METRICS[key]
    question = cfg["question"]
    if cfg.get("format") == "yes_no":
        await bot.send_message(
            chat_id,
            f"📊 {question}",
            reply_markup=get_yes_no_keyboard(key),
        )
    else:
        rng = f" ({cfg['min']}-{cfg['max']})" if cfg.get("min") is not None else ""
        await bot.send_message(chat_id, f"📊 {question}{rng}")
    return True


async def send_reminder(chat_id: int):
    await bot.send_message(
        chat_id,
        "🔔 Напоминание: Ты еще не заполнил метрики за сегодня! Нажми /daily, чтобы сделать это сейчас.",
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🧠 **Borderliner System Online**\n\n"
        "Выбери действие:\n"
        "1️⃣ /daily — Заполнить метрики (сон, работа, состояние)\n"
        "2️⃣ /edit — Редактировать записи (в разработке)\n"
        "3️⃣ /analyse — Получить отчет (в разработке)\n\n"
        "🎙 Также ты можешь прислать голосовое или текст для быстрой заметки.",
    )
    scheduler.add_job(send_reminder, "cron", hour=21, minute=0, args=[message.chat.id])
    if not scheduler.running:
        scheduler.start()


@dp.message(Command("daily"))
async def start_daily(message: types.Message, state: FSMContext):
    metrics_to_ask = list(METRICS.keys())
    await state.update_data(metrics_to_ask=metrics_to_ask, answers={}, current_idx=0)
    await state.set_state(Survey.waiting_for_metrics)
    await ask_next_metric(message.chat.id, state, 0)


@dp.message(Command("edit"))
async def cmd_edit(message: types.Message):
    await message.answer("🛠 Функция редактирования будет доступна после настройки базы данных SQLite. Пока пиши новые данные.")


@dp.message(Command("analyse"))
async def cmd_analyse(message: types.Message):
    await message.answer("📈 Аналитика: на данный момент я собираю данные в Sheets. Скоро я научусь строить графики прямо здесь!")


def _validate_number(value: str, cfg: dict) -> "tuple[bool, str]":
    """Возвращает (ok, error_message)."""
    try:
        n = int(value)
    except ValueError:
        return False, "Введи число."
    lo, hi = cfg.get("min"), cfg.get("max")
    if lo is not None and n < lo:
        return False, f"Минимум {lo}."
    if hi is not None and n > hi:
        return False, f"Максимум {hi}."
    return True, ""


@dp.message(Survey.waiting_for_metrics, F.text)
async def handle_metrics_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    answers = data["answers"]
    idx = data["current_idx"]
    if idx >= len(metrics_to_ask):
        return
    key = metrics_to_ask[idx]
    cfg = METRICS[key]
    if cfg.get("format") == "yes_no":
        await message.answer("Используй кнопки ↑")
        return
    ok, err = _validate_number(message.text.strip(), cfg)
    if not ok:
        await message.answer(f"❌ {err}")
        return
    answers[key] = message.text.strip()
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    if idx < len(metrics_to_ask):
        await ask_next_metric(message.chat.id, state, idx)
    else:
        created_at = datetime.now()
        storage.save_daily(
            message.from_user.id,
            answers,
            created_at=created_at,
            uploaded_at=created_at,
        )
        await message.answer("✅ Метрики записаны в Google Sheets! Увидимся завтра.")
        await state.clear()


@dp.callback_query(Survey.waiting_for_metrics, F.data.startswith("metric:"))
async def handle_metrics_callback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, key, value = parts
    if key not in METRICS or value not in ("yes", "no"):
        await callback.answer()
        return
    data = await state.get_data()
    metrics_to_ask = data["metrics_to_ask"]
    answers = data["answers"]
    idx = data["current_idx"]
    if idx >= len(metrics_to_ask) or metrics_to_ask[idx] != key:
        await callback.answer()
        return
    answers[key] = value
    idx += 1
    await state.update_data(answers=answers, current_idx=idx)
    await callback.answer()
    if idx < len(metrics_to_ask):
        await ask_next_metric(callback.message.chat.id, state, idx)
    else:
        created_at = datetime.now()
        storage.save_daily(
            callback.from_user.id,
            answers,
            created_at=created_at,
            uploaded_at=created_at,
        )
        await callback.message.answer("✅ Метрики записаны в Google Sheets! Увидимся завтра.")
        await state.clear()


@dp.message(F.voice)
async def handle_voice(message: types.Message):
    msg_wait = await message.answer("🎙 Расшифровываю...")
    if not os.path.exists("temp"):
        os.makedirs("temp")
    file_info = await bot.get_file(message.voice.file_id)
    file_path = f"temp/{message.voice.file_id}.ogg"
    await bot.download_file(file_info.file_path, file_path)

    text = await transcribe_voice(file_path)
    telegram_ts = message.date
    uploaded_at = datetime.utcnow()

    storage.save_note(
        message.from_user.id,
        text,
        is_voice=True,
        duration=message.voice.duration,
        telegram_ts=telegram_ts,
        uploaded_at=uploaded_at,
    )

    await msg_wait.edit_text(f"📝 **Заметка:**\n{text}")
    if os.path.exists(file_path):
        os.remove(file_path)


@dp.message(F.text)
async def handle_text_note(message: types.Message):
    if not message.text.startswith("/"):
        telegram_ts = message.date
        uploaded_at = datetime.utcnow()
        storage.save_note(
            message.from_user.id,
            message.text,
            is_voice=False,
            telegram_ts=telegram_ts,
            uploaded_at=uploaded_at,
        )
        await message.answer("✅ Сохранил в заметки.")


async def on_startup(bot: Bot) -> None:
    """Устанавливает webhook при запуске (для Render)."""
    webhook_url = f"{WEBHOOK_BASE_URL.rstrip('/')}/webhook"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook set: {webhook_url}")


if __name__ == "__main__":
    if WEBHOOK_BASE_URL:
        from aiohttp import web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        async def _on_startup(app: web.Application) -> None:
            await on_startup(bot)
            if not scheduler.running:
                scheduler.start()

        app = web.Application()

        async def health(_):
            return web.Response(text="Borderliner Bot OK")

        app.router.add_get("/", health)
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
        setup_application(app, dp, bot=bot)
        app.on_startup.append(_on_startup)

        port = int(os.getenv("PORT", 8080))
        web.run_app(app, host="0.0.0.0", port=port)
    else:
        if not scheduler.running:
            scheduler.start()
        dp.run_polling(bot)
