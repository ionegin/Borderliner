# menu_config.py
MENUS = {
    'main': {
        'type': 'reply',
        'buttons': [
            {'text': '📊 ПРОЙТИ ОПРОС', 'action': 'start_daily', 'row': 0},
            {'text': '✏️ РЕДАКТИРОВАТЬ', 'action': 'yesno_edit', 'row': 1},
        ],
        'resize_keyboard': True,
        'one_time': False,
    },
    'yesno_edit': {
        'type': 'inline',
        'buttons': [
            {'text': '💊 Модафинил', 'action': 'ynedit:modafinil'},
            {'text': '🧘 Йога', 'action': 'ynedit:yoga'},
            {'text': '❌ Отмена', 'action': 'ynedit:cancel'},
        ],
    },
}