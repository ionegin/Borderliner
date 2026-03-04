# menu_config.py
"""
Конфигурация меню бота.
Добавление новых кнопок = добавление элемента в соответствующий список.
"""

MENUS = {
    'main': {
        'type': 'reply',  # ReplyKeyboard (постоянная)
        'buttons': [
            {'text': '📊 ПРОЙТИ ОПРОС', 'action': 'start_daily', 'row': 0},
            {'text': '✏️ РЕДАКТИРОВАТЬ', 'action': 'open_edit', 'row': 1},
        ],
        'resize_keyboard': True,
        'one_time': False,  # Всегда видна
    },
    
    'quick_edit': {
        'type': 'inline',
        'buttons': [
            {'text': 'Сон', 'action': 'qedit:sleep_hours'},
            {'text': 'Еда', 'action': 'qedit:meals'},
            {'text': 'Медитация', 'action': 'qedit:meditate_minutes'},
            {'text': 'Йога', 'action': 'qedit:yoga'},
            {'text': 'Курил', 'action': 'qedit:smoked'},
            {'text': '❌ Отмена', 'action': 'qedit:cancel'}
        ]
    },
    
    'edit_period': {
        'type': 'inline', 
        'buttons': [
            {'text': '📅 СЕГОДНЯ', 'action': 'edit_period:today'},
            {'text': '🔙 ВЧЕРА', 'action': 'edit_period:yesterday'},
            {'text': '🔎 ВЫБРАТЬ ДЕНЬ', 'action': 'edit_period:custom'},
            {'text': '❌ Отмена', 'action': 'edit_period:cancel'},
        ],
    },
    
    'edit_metrics': {
        'type': 'inline',
        'buttons': [
            {'text': 'Сон', 'action': 'edit_met:sleep_hours'},
            {'text': 'Еда', 'action': 'edit_met:meals'},
            {'text': 'Медитация', 'action': 'edit_met:meditate_minutes'},
            {'text': 'Работа', 'action': 'edit_met:productivity_hours'},
            {'text': 'Йога', 'action': 'edit_met:yoga'},
            {'text': 'Курил', 'action': 'edit_met:smoked'},
            {'text': '❌ Отмена', 'action': 'edit_met:cancel'}
        ]
    }
}
