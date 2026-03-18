# menu_config.py
MENUS = {
    'main': {
        'type': 'reply',
        'buttons': [
            {'text': '📊 Пройти опрос', 'row': 0},
            {'text': '💤 Прибавить сон', 'row': 1},
            {'text': '💼 Прибавить продуктивность', 'row': 2},
            {'text': '🧘 Прибавить медитацию', 'row': 3},
            {'text': '🎭 Опрос настроения', 'row': 4},
            # Раскомментируй, чтобы включить:
            # {'text': '🤖 Обсудить с ИИ', 'row': 5},
            {'text': '✏️ РЕДАКТИРОВАТЬ', 'row': 6},
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