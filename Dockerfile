# Используем легковесный образ Python
FROM python:3.11-slim

# Hugging Face Spaces ожидает порт 7860
EXPOSE 7860

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Hugging Face запускает контейнер от UID 1000
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Отладочная информация - ПОКАЖЕТ ЧТО HF ЗАПУСКАЕТ
RUN echo "=== DOCKER DEBUG ===" && ls -la /app && echo "=== APP.PY CONTENT ===" && head -5 /app/app.py && echo "=================="

# Принудительный запуск app.py с FORCE REBUILD флагом
CMD ["sh", "-c", "echo 'FORCE REBUILD v2.1...' && python app.py"]
