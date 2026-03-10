# menu_config.py
MENUS = {
    'main': {
        'type': 'reply',
        'buttons': [
            {'text': '📊 ПРОЙТИ ОПРОС', 'action': 'start_daily', 'row': 0},
            {'text': '📝 МЕНЮ', 'action': 'open_menu', 'row': 1},
        ],
        'resize_keyboard': True,
        'one_time': False,
    },
}