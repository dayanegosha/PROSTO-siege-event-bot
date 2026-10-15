# .prosto

Telegram-бот для исторической выставки «Письма, сохранившие память».

Бот проводит посетителя по разделам экспозиции, показывает материалы, задаёт вопросы и сохраняет результат викторины. Организатор может посмотреть участников и выгрузить отчёт в XLSX.

## запуск

Нужен Python 3.10+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="token"
export ADMIN_ID="123456789"
python main.py
```

Разделы выставки настраиваются в `content_blocks.json`, вопросы — в `quiz_questions.json`. Фотографии и аудио можно указать локальным путём или Telegram file ID.

## проверка

```sh
python -m compileall -q main.py prosto_bot tests
python -m unittest discover -v
```

База участников и выгрузки не должны попадать в Git.

## лицензия

[MIT](LICENSE)
