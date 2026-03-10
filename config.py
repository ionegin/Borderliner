import os
from pathlib import Path
from dotenv import load_dotenv

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
    print(f"DEBUG: created secret_credentials.json from CREDENTIALS_CONTENT")
else:
    print(f"DEBUG: CREDENTIALS_CONTENT is empty or missing!")

CREDENTIALS_FILE = os.getenv("CREDENTIALS_PATH") or "borderliner-credentials.json"

print(f"DEBUG CREDENTIALS_FILE final: {CREDENTIALS_FILE}")
print(f"DEBUG file exists: {os.path.exists(CREDENTIALS_FILE)}")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")
WEBHOOK_BASE_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL") or os.getenv("SPACE_HOST", "")
GOOGLE_SHEET_ID = "1a6fCFKO2y6r04Z2U8N495nzN1S9-SEas_21ldnqFBcY"

from datetime import time
REMINDERS = [
    {'time': time(8, 0), 'type': 'morning'},
    {'time': time(20, 45), 'type': 'evening'},
]