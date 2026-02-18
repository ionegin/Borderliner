from groq import Groq
from config import GROQ_API_KEY

# Инициализируем клиент только если есть ключ
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

async def transcribe_voice(file_path: str):
    if not client:
        raise ValueError("GROQ_API_KEY не установлен. Проверьте переменные окружения.")
    
    # Просто открываем файл и отправляем его в нейронку Groq (Whisper)
    # Конвертация в MP3 не нужна, так как Groq понимает формат Telegram (.ogg)
    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    return transcription