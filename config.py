import os
from pathlib import Path
from dotenv import load_dotenv

print(f"DEBUG CREDENTIALS_CONTENT exists: {bool(os.getenv('CREDENTIALS_CONTENT'))}")
print(f"DEBUG CREDENTIALS_PATH: {os.getenv('CREDENTIALS_PATH')}")
print(f"DEBUG CREDENTIALS_FILE will be: {os.getenv('CREDENTIALS_PATH') or 'borderliner-credentials.json'}")

# Определяем папку, где лежит этот файл
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

# Загружаем .env только если он существует (для локальной разработки)
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# CREDENTIALS_CONTENT — JSON в переменной, создаём временный файл
credentials_content = os.getenv("CREDENTIALS_CONTENT")
if credentials_content:
    credentials_path = str(BASE_DIR / "secret_credentials.json")
    with open(credentials_path, "w") as f:
        f.write(credentials_content)
    os.environ["CREDENTIALS_PATH"] = credentials_path

CREDENTIALS_FILE = os.getenv("CREDENTIALS_PATH") or "borderliner-credentials.json"

# Получаем переменные окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")

# Render задаёт RENDER_EXTERNAL_URL автоматически (https://xxx.onrender.com)
WEBHOOK_BASE_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL") or os.getenv("SPACE_HOST", "")

GOOGLE_SHEET_ID = "1jLufJWwCXdLARn1i9NCop0NeTYlWH5GUOf4sZLRFyMI"

# Настройки напоминаний (время в UTC+2 Cairo)
from datetime import time
REMINDERS = [
    {'time': time(8, 0), 'type': 'morning'},   # Утреннее напоминание
    {'time': time(20, 45), 'type': 'evening'}, # Вечернее напоминание
    # Добавляй новые здесь:
    # {'time': time(14, 0), 'type': 'afternoon'},
]
