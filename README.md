# Tesot-bot

#ГАЙД ПО УСТАНОВКЕ
1. Python

Скачай Python 3.12 с https://python.org/downloads → при установке поставь галочку «Add to PATH».
2. Сайт (import sys.txt)
bash

# переименуй файл в app.py, открой терминал в его папке:
pip install flask
python app.py

→ откроется http://127.0.0.1:8080
3. Бот (# -- coding utf-8 --.txt)
bash

# переименуй в bot.py, открой терминал в его папке:
pip install pyautogui pillow requests keyboard
python bot.py

Перед запуском бота:

    Создай рядом api.txt, вставь туда ключ Gemini одной строкой (взять тут: https://aistudio.google.com/app/apikey)

    Браузер с тестом — на главном мониторе

    В окне бота жми СТАРТ, остановка — ESC

Если python не найден → переустанови Python с галочкой PATH.
Если pip не найден → python -m pip install ...
