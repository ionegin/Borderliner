# metrics.py
# Схема метрик для сбора данных
# Добавление новой метрики: просто добавь новую запись в этот словарь

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
