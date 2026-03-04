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
            {'text': '📝 МЕНЮ', 'action': 'open_menu', 'row': 1},
            {'text': '📅 ИСТОРИЯ', 'action': 'edit_history', 'row': 1},
            {'text': '⚡ БЫСТРАЯ ЗАПИСЬ', 'action': 'quick_edit_menu', 'row': 2},
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
    
    'edit_date': {
        'type': 'inline',  # InlineKeyboard (под сообщением)
        'buttons': [
            {'text': 'Вчера', 'action': 'edit_date:-1'},
            {'text': 'Позавчера', 'action': 'edit_date:-2'},
            {'text': '3 дня назад', 'action': 'edit_date:-3'},
            {'text': '4 дня', 'action': 'edit_date:-4'},
            {'text': '5 дней', 'action': 'edit_date:-5'},
            {'text': '6 дней', 'action': 'edit_date:-6'},
            {'text': '📅 Ввести дату', 'action': 'edit_date:manual'},
            {'text': '❌ Отмена', 'action': 'cancel'},
        ],
    },
}
