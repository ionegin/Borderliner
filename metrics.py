# metrics.py

# Шаблоны измерений
MEASUREMENT_TYPES = {
    "hours": {
        "format": "number",
        "min": 0,
        "max": 24,
    },
    "minutes": {
        "format": "number",
        "min": 0,
        "max": 999,
    },
    "scale_10": {
        "format": "number",
        "min": 0,
        "max": 10,
    },
    "yes_no": {
        "format": "yes_no",
    },
    "note": {
        "format": "text",
        "optional": True,
    },
    "count": {
        "format": "number",
        "min": 0,
        "max": 20,
    },
    "time": {
        "format": "time",
    },
}

# Метрики для daily опроса
METRICS = {
    "sleep_time": {
        "question": "Во сколько лёг спать?",
        "measurement": "time"
    },
    "wake_time": {
        "question": "Во сколько проснулся?",
        "measurement": "time"
    },
    "productivity_hours": {
        "question": "Продуктивность (часов)?",
        "measurement": "hours"
    },
    "meditate_minutes": {
        "question": "Сколько минут медитировал?",
        "measurement": "minutes"
    },
    "meals": {
        "question": "Сколько раз ел?",
        "measurement": "count"
    },
    "energy": {
        "question": "Уровень энергии?",
        "measurement": "scale_10"
    },
    "anxiety": {
        "question": "Уровень тревоги?",
        "measurement": "scale_10"
    },
    "racing_thoughts": {
        "question": "Ускоренные мысли и речь?",
        "measurement": "scale_10"
    },
    "communication": {
        "question": "Раздражительность?",
        "measurement": "scale_10"
    },
    "smoked": {
        "question": "Сколько косяков?",
        "measurement": "count"
    },
    "yoga": {
        "question": "Йога?",
        "measurement": "yes_no"
    },
    "mood_note": {
        "question": "Что тебя беспокоит? (текст/войс/пропустить)",
        "measurement": "note"
    }
}


# Вспомогательная функция для получения конфига measurement
def get_measurement_config(metric_key):
    """Возвращает полный конфиг measurement для метрики."""
    metric = METRICS[metric_key]
    measurement_type = metric["measurement"]
    return MEASUREMENT_TYPES[measurement_type]
