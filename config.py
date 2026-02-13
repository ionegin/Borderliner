import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем папку, где лежит этот файл
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

print("\n--- ГЛУБОКАЯ ПРОВЕРКА СИСТЕМЫ ---")
print(f"Рабочая папка: {BASE_DIR}")
print(f"Список файлов в папке: {os.listdir(BASE_DIR)}")

if env_path.exists():
    print(f"Файл .env найден! Пытаюсь прочитать...")
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"❌ ФАЙЛ .env НЕ НАЙДЕН по пути {env_path}")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")
CREDENTIALS_FILE = os.getenv("CREDENTIALS_PATH") or "borderliner-credentials.json"

if BOT_TOKEN:
    print(f"✅ УСПЕХ! Токен загружен.")
else:
    print(f"❌ ТОКЕН ВСЕ ЕЩЕ НЕ ВИДЕН")
print("---------------------------------\n")

GOOGLE_SHEET_ID = "1jLufJWwCXdLARn1i9NCop0NeTYlWH5GUOf4sZLRFyMI"

# Схема метрик: key = заголовок колонки в таблице
# format: "number" (min, max) или "yes_no"
# Добавление нового показателя: добавь запись сюда — колонка и вопрос создадутся автоматически
# Пример для horny: "horny": {"question": "Horny?", "format": "number", "min": 1, "max": 10}
METRICS = {
    "sleep_hours": {"question": "Сколько часов ты спал?", "format": "number", "min": 1, "max": 24},
    "productivity_hours": {"question": "Продуктивность (часов)?", "format": "number", "min": 1, "max": 24},
    "meditate_minutes": {"question": "Сколько минут медитировал?", "format": "number", "min": 1, "max": 999},
    "energy": {"question": "Уровень энергии?", "format": "number", "min": 1, "max": 10},
    "anxiety": {"question": "Уровень тревоги?", "format": "number", "min": 1, "max": 10},
    "communication": {"question": "Качество общения?", "format": "number", "min": 1, "max": 10},
    "smoked": {"question": "Курил сегодня?", "format": "yes_no"},
    "yoga": {"question": "Йога?", "format": "yes_no"},
}
