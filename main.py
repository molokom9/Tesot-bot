# -*- coding: utf-8 -*-
"""
Tesot-bot - автоматическое прохождение тестов (Gemini + мышь/клавиатура).

Нейронка смотрит на экран, составляет план действий, скрипт его выполняет.
Ключ Gemini лежит в api.txt рядом со скриптом (одна строка).
ESC - аварийная остановка.
"""
import os
import sys
import time
import subprocess
import threading
import base64
import io
import json
import random
import re
import queue
import traceback
import ctypes
from datetime import datetime

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk


# ---------------------------------------------------------------------
# зависимости
# ---------------------------------------------------------------------
def install_deps():
    need = [("pyautogui", "pyautogui"), ("PIL", "pillow"),
            ("requests", "requests"), ("keyboard", "keyboard")]
    for module_name, pip_name in need:
        try:
            __import__(module_name)
        except ImportError:
            print(f"[установка] ставлю {pip_name}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pip_name])
            except Exception as e:
                print(f"[ошибка] не вышло поставить {pip_name}: {e}")
                print("Поставь руками: python -m pip install "
                      "pyautogui pillow requests keyboard")
                try:
                    input("Enter чтобы закрыть...")
                except Exception:
                    pass
                sys.exit(1)
    import importlib
    importlib.invalidate_caches()


install_deps()

# на винде нужно, чтобы размер скриншота совпадал с координатами мыши
if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import pyautogui          # noqa: E402
import requests           # noqa: E402
from PIL import Image, ImageGrab, ImageDraw   # noqa: E402

try:
    import keyboard       # noqa: E402
except Exception:
    keyboard = None

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.12

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_FILE = os.path.join(SCRIPT_DIR, "api.txt")
LOG_FILE = os.path.join(SCRIPT_DIR, "bot.log")
DEBUG_IMG = os.path.join(SCRIPT_DIR, "last_scan.jpg")
DEAD_FILE = os.path.join(SCRIPT_DIR, "dead_models.json")
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")

API_BASE = "https://generativelanguage.googleapis.com/v1beta"

FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

EXCLUDE_WORDS = (
    "image", "tts", "transcribe", "embedding", "live", "audio", "customtools",
    "robotics", "computer-use", "antigravity", "deep-research", "lyria",
    "nano-banana", "argon", "omni", "imagen", "veo", "aqa",
    "learnlm", "thinking", "exp", "native", "video",
)

MAX_IMG_SIDE = 1920
JPEG_QUALITY = 75
LITE_IMG_SIDE = 1280
LITE_JPEG_QUALITY = 60
SENTINEL = "__ROBOT_EMPTY_CLIPBOARD__"
MAX_ACTIONS = 25
MAX_ITERATIONS = 600
HISTORY_KEEP = 8
HISTORY_IN_PROMPT = 5
STOP_STUCK_LEVEL = 6
LAYOUT_SHIFT = 0.06
NO_CHANGE = 0.0005
ZONE_MARGIN = 6           # пикселей запаса вокруг опасных кнопок
PARALLEL = 3              # сколько моделей спрашиваем одновременно

# сочетания клавиш, которые бот не нажимает никогда
BLOCKED_KEYS = {
    "alt+f4", "ctrl+w", "ctrl+q", "ctrl+shift+w", "ctrl+shift+delete",
    "ctrl+alt+delete", "alt+tab", "ctrl+t", "ctrl+n", "win", "ctrl+shift+n",
    "ctrl+shift+t", "f11", "f12", "ctrl+shift+i",
}

# кнопки, которые нельзя жать ни при каких условиях
DANGER_RE = re.compile(
    r"(сброс|заново|перезапуск|повторить\s*тест|reset|restart|start\s*over|"
    r"retake|выйти|выход|log\s*out|logout|sign\s*out|\bexit\b|\bquit\b|отмен|"
    r"cancel|удал|delete|remove|очист|\bclear\b|назад|\bback\b|\bclose\b|"
    r"закрыть|на\s*главную|\bhome\b|предыдущ|\bprevious\b|\bprev\b|"
    r"пропустить|\bskip\b|прерв|abort|отказ|завершить\s*попытк|"
    r"cancel\s*attempt|discard)", re.I)

# кнопки, которые можно жать (подтверждение ответа / переход дальше)
ALLOW_RE = re.compile(
    r"(?<!\w)(ответ|answer|провер|check|дале|next|продолж|continue|отправ|"
    r"submit|подтверд|confirm|готов|done|ok|ок|сохран|save|следующ|начать|"
    r"старт|start|begin|приступ|принять|apply)", re.I)

# завершение теста - только когда вопросы кончились
FINISH_RE = re.compile(
    r"(заверш|сдать|finish|end\s*test|закончить|результат)", re.I)

CLICKS = ("click", "double_click", "right_click")
SAFE_KINDS = ("option", "field", "dropdown", "dropdown_item")

METHODS = [
    ("auto", "Авто"),
    ("vision", "Экран"),
    ("text", "Текст страницы"),
]
STRATEGY_LABELS = {
    "vision": "экран",
    "text": "текст страницы",
    "vision_lite": "лёгкий экран",
}
THINK_LABELS = [("Быстро", "low"), ("Средне", "medium"), ("Глубоко", "high")]
THINK_RANK = {"low": 0, "medium": 1, "high": 2}


# ---------------------------------------------------------------------
# ввод юникода через SendInput (винда), без буфера обмена
# ---------------------------------------------------------------------
if sys.platform.startswith("win"):
    from ctypes import wintypes

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_size_t)]

    class _HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT),
                    ("hi", _HARDWAREINPUT)]

    class _INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]

    def win_send_unicode_char(ch):
        data = ch.encode("utf-16-le")
        for i in range(0, len(data), 2):
            code = int.from_bytes(data[i:i + 2], "little")
            arr = (_INPUT * 2)()
            arr[0].type = 1
            arr[0].ki = _KEYBDINPUT(0, code, 0x0004, 0, 0)
            arr[1].type = 1
            arr[1].ki = _KEYBDINPUT(0, code, 0x0004 | 0x0002, 0, 0)
            ctypes.windll.user32.SendInput(2, ctypes.byref(arr),
                                           ctypes.sizeof(_INPUT))
else:
    def win_send_unicode_char(ch):
        raise RuntimeError("SendInput есть только в Windows")


# ---------------------------------------------------------------------
# исключения
# ---------------------------------------------------------------------
class GeminiError(Exception):
    def __init__(self, status, message, retry_after=None, fatal=False):
        super().__init__(f"Gemini {status}: {message}")
        self.status = status
        self.message = message
        self.retry_after = retry_after
        self.fatal = fatal


class Stopped(Exception):
    pass


class AllModelsFailed(Exception):
    pass


class StrategyFailed(Exception):
    pass


class Blocked(Exception):
    """Действие запрещено защитой."""


# ---------------------------------------------------------------------
# ключ, мёртвые модели, настройки
# ---------------------------------------------------------------------
def load_api_key():
    if not os.path.exists(API_FILE):
        return None
    try:
        with open(API_FILE, "rb") as f:
            raw = f.read()
    except Exception:
        return None
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1251", "utf-16", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if not text:
        return None
    text = text.replace("\ufeff", "").replace("\x00", "")
    for line in text.splitlines():
        line = line.strip().strip("\"'").strip()
        if line:
            return line
    return None


def mask_key(text, key):
    if key and text:
        return str(text).replace(key, "***KEY***")
    return str(text)


def load_dead_models():
    try:
        with open(DEAD_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_dead_models(models):
    try:
        with open(DEAD_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(models), f)
    except Exception:
        pass


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------
# список моделей
# ---------------------------------------------------------------------
def list_available_models(api_key):
    url = f"{API_BASE}/models?pageSize=200"
    headers = {"x-goog-api-key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=20)
    except Exception as e:
        return None, mask_key(f"сеть: {e}", api_key)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {mask_key(r.text[:300], api_key)}"
    try:
        data = r.json()
    except Exception:
        return None, "ответ не JSON"
    models = []
    for m in data.get("models", []):
        name = m.get("name", "").replace("models/", "")
        if "generateContent" in m.get("supportedGenerationMethods", []):
            models.append(name)
    return models, None


def pick_vision_models(names):
    """Чередует flash и flash-lite, старые версии (<3) уходят в конец."""
    flash, lite, pro = [], [], []
    for n in names:
        if not n.startswith("gemini-"):
            continue
        if any(w in n for w in EXCLUDE_WORDS):
            continue
        m = re.match(r"^gemini-(\d+(?:\.\d+)?)-(flash-lite|flash|pro)"
                     r"(-preview)?$", n)
        if not m:
            continue
        version = float(m.group(1))
        key = (1 if version < 3 else 0, -version,
               1 if m.group(3) else 0, n)
        {"flash": flash, "flash-lite": lite, "pro": pro}[m.group(2)].append(key)
    flash = [k[3] for k in sorted(flash)]
    lite = [k[3] for k in sorted(lite)]
    pro = [k[3] for k in sorted(pro)]

    result = []
    for i in range(max(len(flash), len(lite))):
        if i < len(flash):
            result.append(flash[i])
        if i < len(lite):
            result.append(lite[i])
    for alias in ("gemini-flash-latest", "gemini-flash-lite-latest"):
        if alias in names and alias not in result:
            result.append(alias)
    result += pro[:2]
    gem = sorted(n for n in names
                 if re.match(r"^gemma-\d+-\d+b(?:-a\d+b)?-it$", n))
    result += gem[::-1][:2]
    return result


# ---------------------------------------------------------------------
# промпт
# ---------------------------------------------------------------------
PROMPT_TEMPLATE = """Ты проходишь тест на сайте, управляя МЫШЬЮ и КЛАВИАТУРОЙ. __INTRO__

Твоя ЕДИНСТВЕННАЯ задача - отвечать на вопросы теста. Всё остальное на странице \
(меню, шапка, подвал, служебные кнопки, реклама) - не твоё, туда не лезь.

Работаешь ПОШАГОВО: каждый раз получаешь свежий кадр, контекст прошлых шагов и \
составляешь план действий; робот его выполняет и присылает новый кадр. Сайты разные, \
порядок вариантов и положение кнопок меняются - опирайся только на текущий кадр. \
Думай внимательно, отвечай коротко.

Верни СТРОГО JSON:
{
  "reflection": "что получилось после моих прошлых действий (1 фраза; на первом шаге пусто)",
  "state": "question",
  "is_test_finished": false,
  "question": "текст текущего вопроса или пустая строка",
  "summary": "кратко: что на экране и в каком состоянии вопрос",
  "progress": {"current": 3, "total": 10},
  "answers_count": 1,
  "wrong_applied": false,
  "learned": "",
  "danger_zones": [
    {"text": "Отменить попытку", __TS__}
  ],
  "actions": [
    {"do": "click", "kind": "option", "label": "вариант B", __TS__},
    {"do": "type", "kind": "field", "label": "поле ответа", __TS__, "value": "текст", "enter": false},
    {"do": "scroll", "direction": "down", "amount": "medium", "rescan_after": true},
    {"do": "click", "kind": "button", "label": "подтверждение", "element_text": "Ответить", __TS__}
  ]
}

ПОЛЯ:
- reflection: сравни контекст прошлых шагов с тем, что видишь. Сработало ли действие?
  Если нажал не туда - скажи, как исправляешься.
- state: "question" (есть что делать), "finished" (тест завершён: итоги, результат), "other".
- is_test_finished: true только если тест реально закончен и действий не нужно.
- progress: если на странице написано «Вопрос 3 из 10» - current и total, иначе null.
- answers_count: сколько вопросов этот план отвечает (ВЫБИРАЕТ вариант / ВВОДИТ текст
  впервые). Если ответ уже выбран и ты только жмёшь «Ответить/Далее», или только
  прокручиваешь/раскрываешь список - 0.
- wrong_applied: true, если по заданию ниже ты сознательно ответил НЕПРАВИЛЬНО.
- learned: короткая заметка про этот сайт или ошибку, которую нельзя повторять
  (например «после выбора в списке жми синюю кнопку Ответить внизу»). Иначе "".
- danger_zones: ВСЕ видимые на кадре кнопки, которые нельзя жать: «Отменить попытку»,
  «Сбросить», «Начать заново», «Выйти», «Назад», «Удалить», «Закрыть», «Пропустить»,
  «На главную» и похожие. Для каждой - точная надпись и рамка. Робот не даст
  кликнуть в эти рамки. __ZONENOTE__ Если таких кнопок нет - [].
- actions: шаги по порядку (максимум 25).

ТИПЫ ДЕЙСТВИЙ ("do"):
- "click" (также "double_click", "right_click") - клик. ОБЯЗАТЕЛЬНО поле "kind":
    "option"        - вариант ответа (радиокнопка, чекбокс, карточка с текстом);
    "field"         - поле ввода;
    "dropdown"      - сам выпадающий список (закрытый или открытый заголовок);
    "dropdown_item" - пункт внутри раскрытого списка;
    "button"        - любая кнопка. Для неё ВСЕГДА пиши "element_text" - дословную
                    надпись на кнопке. Без неё или с чужой надписью робот не нажмёт.
- "type" - клик в поле и ввод текста: "value", "enter": true - нажать Enter после ввода.
  Если курсор уже в поле - цель не указывай.
- "select" - выбор пункта в ОБЫЧНОМ (нативном) списке: цель - сам список, "value" - текст
  пункта. Если сомневаешься - надёжнее click по списку и click по пункту.
- "scroll" - "direction": "down"|"up", "amount": "small"|"medium"|"large". Цель
  (необязательно) - над какой областью крутить.
- "drag" - перетащить: цель - откуда, __TO__ - куда.
- "key" - клавиша: "keys": "enter", "tab", "down", "space"...
- "wait" - "seconds" (до 5).
- Любому действию можно добавить "rescan_after": true - «после этого экран изменится,
  дальше по плану не иди, пришли новый кадр». Такое действие - последнее в плане.

ЦЕЛИ ДЕЙСТВИЙ:
__TARGET__

ПРАВИЛА:
1. Можно кликать ТОЛЬКО: варианты ответа, поля ввода, выпадающий список и его пункты,
   кнопки подтверждения и перехода («Ответить», «Проверить», «Далее», «Продолжить»,
   «Отправить», «Подтвердить», Next, Submit, Check; «Начать» - только в начале теста).
   «Завершить/Сдать/Finish» - только когда все вопросы уже отвечены. Всё остальное
   на странице - не трогай.
2. Ловушки: кнопки отмены попытки, сброса, выхода и т.п. часто стоят РЯДОМ с
   «Ответить» и рядом со списками, выглядят похоже. Перед каждым кликом по кнопке
   прочитай её надпись на кадре. Не уверен - не жми, лучше scroll или rescan_after.
3. СНАЧАЛА ОПРЕДЕЛИ СОСТОЯНИЕ вопроса:
   (а) ответ не выбран/не введён -> выбери/введи;
   (б) ответ выбран, но не подтверждён -> жми кнопку подтверждения, ответ не меняй;
   (в) ответ подтверждён, видна обратная связь -> вопрос закрыт, жми «Далее»;
   (г) тест окончен.
4. Вопрос НЕ засчитывается, пока не нажата кнопка подтверждения («Ответить» и т.п.).
   Выбрал ответ и кнопка видна - последним действием кликни её. Если после
   «Проверить» нужно ещё «Далее» - у первой кнопки "rescan_after": true. Если кнопки
   нигде нет, а ответ выбран - "key" "enter".
5. ВЫПАДАЮЩИЕ СПИСКИ - самое опасное место, делай строго так:
   - Сначала посмотри на ТЕКУЩЕЕ ЗНАЧЕНИЕ списка. Если там выбранный вариант (а не
     заглушка «Выберите...», «—», «Select») - ответ УЖЕ выбран: список не трогай,
     жми кнопку подтверждения. Значение неверное - открой список заново.
   - Открытие: одно действие click, kind "dropdown", "rescan_after": true. Больше
     ничего в этом плане.
   - Выбор: на новом кадре кликни пункт, kind "dropdown_item". Рамка ТОЛЬКО по строке
     пункта, не шире и не соседние строки. Не кликай мимо списка: клик вне списка
     закрывает его, а рядом могут быть кнопки отмены.
   - Нужного пункта не видно - scroll над списком с rescan_after.
   - После выбора убедись, что значение появилось в списке, и только потом
     подтверждай.
6. Если вопрос/варианты видны не полностью или кнопка может быть ниже - scroll down с
   "rescan_after": true. Не отвечай по обрезанным вариантам.
7. Уже выбранные варианты повторно не кликай (чекбоксы переключаются). Для «несколько
   правильных» кликай только нужные ещё не отмеченные.
8. Отвечай на ВСЕ вопросы любого типа: один вариант, несколько, текст, число, список,
   да/нет, сопоставление (drag), ползунок. Текст в "value" - кратко, по делу, на языке
   вопроса.
9. Если ни вопроса, ни кнопок нет, а тест не закончен - scroll down с rescan_after.
   Тест окончен - state "finished", is_test_finished true, actions [].

КОНТЕКСТ ПРОШЛЫХ ШАГОВ И ЗАМЕТКИ:
__CONTEXT__

ЗАДАНИЕ ПО СЧЁТЧИКУ ОТВЕТОВ:
__DIRECTIVE__

Верни ТОЛЬКО JSON, без markdown и без пояснений."""

TARGET_VISION = (
    '- Цель задаётся полем "box_2d": [ymin, xmin, ymax, xmax] (формат Gemini).\n'
    '  Значения НОРМАЛИЗОВАНЫ от 0 до 1000 относительно всего изображения:\n'
    '  y - доля высоты * 1000, x - доля ширины * 1000, (0,0) - левый верхний угол.\n'
    '- Рамка охватывает кликабельную область: радиокнопку/чекбокс вместе с текстом\n'
    '  варианта, поле ввода, кнопку, строку списка. Рамка ТОЧНО на нужном элементе,\n'
    '  а не на соседнем, и не больше самого элемента.\n'
    '- Для "drag" - "box_2d" (откуда) и "to_box_2d" (куда).\n'
    '- Всегда добавляй короткий "label".')
TARGET_TEXT = (
    '- Цель задаётся полем "find_text" - ДОСЛОВНЫЙ фрагмент текста (15-40 символов,\n'
    '  без переносов строк), который написан прямо на цели: текст варианта, надпись\n'
    '  кнопки. Скрипт найдёт его поиском браузера (Ctrl+F) и кликнет.\n'
    '- Для поля ввода без собственного текста: find_text = дословная подпись или\n'
    '  текст вопроса над полем и "tab_after": true (скрипт кликнет по подписи и\n'
    '  нажмёт Tab, чтобы попасть в поле).\n'
    '- Для "drag": "find_text" (откуда) и "to_find_text" (куда).\n'
    '- Всегда добавляй короткий "label". Прокручивать почти не нужно - поиск\n'
    '  браузера сам доскролливает до найденного текста.\n'
    '- В тексте не видно, какие варианты уже отмечены - ориентируйся на КОНТЕКСТ\n'
    '  прошлых шагов, чтобы не отвечать на один вопрос дважды.')


def build_prompt(mode, directive, context, page_text=None):
    if mode == "vision":
        intro = ("На скриншоте открыт сайт с тестом (браузер). Игнорируй всё, "
                 "что не относится к тесту (вкладки, панели, другие окна).")
        target = TARGET_VISION
        ts = '"box_2d": [ymin, xmin, ymax, xmax]'
        to = '"to_box_2d"'
        zone_note = "Рамки - в том же формате box_2d."
    else:
        intro = ("Ниже - ВЕСЬ ТЕКСТ веб-страницы, скопированный из браузера "
                 "(картинок ты не видишь; в тексте может быть мусор: меню, "
                 "подвал). Если вопросов несколько - отвечай по порядку.")
        target = TARGET_TEXT
        ts = '"find_text": "дословный текст"'
        to = '"to_find_text"'
        zone_note = ("В режиме текста рамок нет: пиши в find_text надпись кнопки "
                     "(по ней робот тоже проверит клик).")
    p = (PROMPT_TEMPLATE.replace("__INTRO__", intro)
         .replace("__TARGET__", target)
         .replace("__TS__", ts)
         .replace("__TO__", to)
         .replace("__ZONENOTE__", zone_note)
         .replace("__CONTEXT__", context)
         .replace("__DIRECTIVE__", directive))
    if mode == "text":
        p += "\n\nТЕКСТ СТРАНИЦЫ:\n<<<\n" + (page_text or "") + "\n>>>"
    return p


# ---------------------------------------------------------------------
# запрос к Gemini
# ---------------------------------------------------------------------
def call_gemini(api_key, model, parts, timeout, think="low"):
    url = f"{API_BASE}/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    gen = {"responseMimeType": "application/json", "maxOutputTokens": 16384}
    if model.startswith("gemini-3"):
        gen["thinkingConfig"] = {"thinkingLevel": think or "low"}

    for _attempt in range(4):
        payload = {"contents": [{"parts": parts}], "generationConfig": gen}
        try:
            r = requests.post(url, headers=headers, json=payload,
                              timeout=(10, timeout))
        except requests.exceptions.Timeout:
            raise GeminiError(0, "таймаут запроса")
        except requests.exceptions.RequestException as e:
            raise GeminiError(0, mask_key(f"сетевая ошибка: {e}", api_key))
        except UnicodeEncodeError:
            raise GeminiError(0, "в ключе странные символы, проверь api.txt",
                              fatal=True)

        # модель не понимает часть параметров - упрощаем и пробуем снова
        if r.status_code == 400:
            low = r.text.lower()
            if "thinking" in low and "thinkingConfig" in gen:
                if gen["thinkingConfig"].get("thinkingLevel") != "low":
                    gen["thinkingConfig"]["thinkingLevel"] = "low"
                else:
                    del gen["thinkingConfig"]
                continue
            if ("json mode" in low or "mime" in low) and "responseMimeType" in gen:
                del gen["responseMimeType"]
                continue

        if r.status_code != 200:
            body = mask_key(r.text, api_key)
            retry_after = None
            m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body)
            if m:
                retry_after = float(m.group(1))
            elif r.headers.get("Retry-After"):
                try:
                    retry_after = float(r.headers["Retry-After"])
                except Exception:
                    pass
            low = body.lower()
            fatal = (r.status_code == 401 or any(
                s in low for s in ("api key not valid", "api_key_invalid",
                                   "api key expired", "has been suspended",
                                   "reported as leaked")))
            short = re.sub(r"\s+", " ", body)[:300]
            raise GeminiError(r.status_code, short, retry_after, fatal)

        try:
            data = r.json()
        except Exception:
            raise GeminiError(200, "ответ не JSON")
        cands = data.get("candidates") or []
        if not cands:
            raise GeminiError(
                200, f"пустой ответ (promptFeedback={data.get('promptFeedback')})")
        rparts = (cands[0].get("content") or {}).get("parts") or []
        texts = [p.get("text", "") for p in rparts
                 if isinstance(p, dict) and not p.get("thought") and p.get("text")]
        text = "".join(texts).strip()
        if not text:
            raise GeminiError(
                200, f"нет текста (finishReason={cands[0].get('finishReason')})")
        return text
    raise GeminiError(400, "не удалось подобрать параметры запроса")


def parse_model_json(text):
    candidates = [text]
    t = text.strip()
    if t.startswith("```"):
        t2 = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t2 = re.sub(r"\s*```\s*$", "", t2)
        candidates.append(t2)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        candidates.append(m.group(0))
    for c in candidates:
        try:
            obj = json.loads(c)
        except Exception:
            continue
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            obj = obj[0]
        if isinstance(obj, dict):
            return obj
    return None


# ---------------------------------------------------------------------
# скриншот и сравнение кадров
# ---------------------------------------------------------------------
def capture_screen(max_side=MAX_IMG_SIDE):
    img = ImageGrab.grab()
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    big = max(w, h)
    if big > max_side:
        k = max_side / big
        img = img.resize((int(w * k), int(h * k)))
    return img


def img_to_b64(img, quality=JPEG_QUALITY):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


THUMB_SIZE = (128, 72)
_BOX = getattr(Image, "Resampling", Image).BOX


def thumb_bytes(img):
    return img.convert("L").resize(THUMB_SIZE, _BOX).tobytes()


def grab_thumb():
    try:
        return thumb_bytes(ImageGrab.grab())
    except Exception:
        return None


def frame_diff(a, b):
    """Доля заметно изменившихся ячеек между двумя кадрами (0..1)."""
    if not a or not b or len(a) != len(b):
        return None
    changed = sum(1 for x, y in zip(a, b) if abs(x - y) > 18)
    return changed / len(a)


def describe_change(d):
    if d is None:
        return "неизвестно"
    pct = d * 100
    if d < NO_CHANGE:
        return f"НЕ изменился ({pct:.2f}%), действие ничего не дало"
    if d < 0.03:
        return (f"изменилась небольшая часть ({pct:.1f}%): отметка варианта, "
                f"ввод или выбранное значение")
    return f"сильно изменился ({pct:.0f}%): новая страница, вопрос или прокрутка"


# ---------------------------------------------------------------------
# координаты
# ---------------------------------------------------------------------
def _four_floats(v):
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        return [float(x) for x in v]
    except Exception:
        return None


def get_box(obj):
    """Рамка из {"box_2d":[ymin,xmin,ymax,xmax]} или {"bbox":[x1,y1,x2,y2]}."""
    if not isinstance(obj, dict):
        return None
    b = _four_floats(obj.get("box_2d"))
    if b:
        y1, x1, y2, x2 = b
    else:
        b = _four_floats(obj.get("bbox"))
        if not b:
            return None
        x1, y1, x2, y2 = b
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return x1, y1, x2, y2


def box_to_rect(box, img_size, screen_size):
    """Рамка -> прямоугольник в пикселях экрана."""
    x1, y1, x2, y2 = box
    iw, ih = img_size
    sw, sh = screen_size
    if max(x1, y1, x2, y2) <= 1000:
        return (x1 / 1000 * sw, y1 / 1000 * sh,
                x2 / 1000 * sw, y2 / 1000 * sh)
    return x1 / iw * sw, y1 / ih * sh, x2 / iw * sw, y2 / ih * sh


def box_to_screen_point(box, img_size, screen_size, jitter=True):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    if jitter:
        cx += (x2 - x1) * random.uniform(-0.06, 0.06)
        cy += (y2 - y1) * random.uniform(-0.06, 0.06)
    left, top, right, bottom = box_to_rect((cx, cy, cx, cy), img_size,
                                           screen_size)
    sw, sh = screen_size
    px = int(min(max(left, 1), sw - 2))
    py = int(min(max(top, 1), sh - 2))
    return px, py


def save_debug_image(img, actions, zones=None, path=DEBUG_IMG):
    """Скриншот с рамками: зелёная - клик, оранжевая - ввод/список,
    розовая - drag, голубая - скролл, красная - опасные кнопки."""
    try:
        dbg = img.copy()
        d = ImageDraw.Draw(dbg)
        iw, ih = dbg.size
        colors = {"click": "lime", "double_click": "lime", "right_click": "lime",
                  "type": "orange", "select": "orange", "drag": "magenta",
                  "scroll": "cyan"}

        def rect(box, color, label):
            if not box:
                return
            x1, y1, x2, y2 = box
            if max(x1, y1, x2, y2) <= 1000:
                x1, x2 = x1 / 1000 * iw, x2 / 1000 * iw
                y1, y2 = y1 / 1000 * ih, y2 / 1000 * ih
            d.rectangle([x1, y1, x2, y2], outline=color, width=3)
            d.text((x1 + 4, y1 + 2), label, fill=color)

        for i, a in enumerate(actions):
            do = str(a.get("do", "")).lower()
            col = colors.get(do, "white")
            rect(get_box(a), col, f"{i + 1}:{do}")
            if do == "drag":
                rect(get_box({"box_2d": a.get("to_box_2d")}), col,
                     f"{i + 1}:to")
        for z in (zones or []):
            rect(get_box(z), "red", "NO: " + str(z.get("text", ""))[:20])
        dbg.save(path, format="JPEG", quality=80)
        return path
    except Exception:
        return None


# ---------------------------------------------------------------------
# поиск текста через Ctrl+F (по цвету подсветки)
# ---------------------------------------------------------------------
def make_snippets(text):
    t = re.sub(r"\s+", " ", str(text)).strip()
    stripped = re.sub(r"^[\(\[]?[A-Za-zА-Яа-я0-9]{1,2}[\)\.\]:]\s+", "", t)
    cands = [t[:60], stripped[:40], stripped[:22], stripped[-22:]]
    out = []
    for c in cands:
        c = c.strip()
        if len(c) >= 2 and c not in out:
            out.append(c)
    return out


def find_highlight_point(img):
    """Ищет цвет подсветки поиска браузера (оранжевый/жёлтый/зелёный)."""
    pix = img.load()
    w, h = img.size
    found = {"orange": [], "yellow": [], "green": []}
    step = 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = pix[x, y][:3]
            if r >= 235 and 130 <= g <= 172 and b <= 90:
                found["orange"].append((x, y))
            elif r >= 235 and g >= 235 and b <= 75:
                found["yellow"].append((x, y))
            elif r <= 95 and g >= 200 and b <= 75:
                found["green"].append((x, y))
    for color in ("orange", "green", "yellow"):
        pts = found[color]
        if len(pts) < 8:
            continue
        cell = 60
        buckets = {}
        for (x, y) in pts:
            buckets.setdefault((x // cell, y // cell), []).append((x, y))
        best_key = max(buckets, key=lambda k: len(buckets[k]))
        near = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                near += buckets.get((best_key[0] + dx, best_key[1] + dy), [])
        if len(near) < 8:
            continue
        xs = [p[0] for p in near]
        ys = [p[1] for p in near]
        return (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
    return None


# ---------------------------------------------------------------------
# мелкие помощники
# ---------------------------------------------------------------------
def norm_actions(res):
    acts = res.get("actions") if isinstance(res, dict) else None
    if not isinstance(acts, list):
        return []
    return [a for a in acts if isinstance(a, dict)][:MAX_ACTIONS]


def to_int(v):
    try:
        return int(float(v))
    except Exception:
        return None


def norm_q(text):
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()[:100]


def pos_str(a):
    b = get_box(a)
    if not b:
        return ""
    x1, y1, x2, y2 = b
    return f"@({int((x1 + x2) / 2)},{int((y1 + y2) / 2)})"


def plan_sig(res, actions):
    """Подпись плана, чтобы замечать повторы."""
    items = []
    for a in actions:
        b = get_box(a)
        pos = None
        if b:
            pos = (int(((b[0] + b[2]) / 2) // 25),
                   int(((b[1] + b[3]) / 2) // 25))
        items.append((a.get("do"), a.get("label") or a.get("find_text"),
                      a.get("value"), pos))
    return (norm_q(res.get("question"))[:100] + "|" +
            json.dumps(items, ensure_ascii=False))


def lighten(hex_color, k=0.15):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, int(c + (255 - c) * k)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------
# оформление
# ---------------------------------------------------------------------
BG = "#12141a"
PANEL = "#1b1e27"
FIELD = "#252936"
LINE = "#333848"
TEXT = "#e8eaf0"
MUTED = "#7f869a"
ACCENT = "#7c6cf0"
GREEN = "#2ecc8f"
RED = "#ef5350"
AMBER = "#f5b942"

FONT = "Segoe UI"


class Btn(tk.Label):
    """Плоская кнопка с подсветкой при наведении."""

    def __init__(self, master, text, command, bg=ACCENT, fg="#ffffff",
                 size=11, padx=18, pady=9):
        super().__init__(master, text=text, bg=bg, fg=fg, padx=padx, pady=pady,
                         font=(FONT, size, "bold"), cursor="hand2")
        self.base = bg
        self.fg0 = fg
        self.hover = lighten(bg, 0.14)
        self.cmd = command
        self.enabled = True
        self.bind("<Enter>", lambda e: self.enabled and
                  self.config(bg=self.hover))
        self.bind("<Leave>", lambda e: self.enabled and
                  self.config(bg=self.base))
        self.bind("<ButtonRelease-1>", self._click)

    def _click(self, _e):
        if self.enabled and self.cmd:
            self.cmd()

    def set_enabled(self, on):
        self.enabled = on
        if on:
            self.config(bg=self.base, fg=self.fg0, cursor="hand2")
        else:
            self.config(bg=FIELD, fg=MUTED, cursor="arrow")


class App:
    def __init__(self, root):
        self.root = root
        root.title("Tesot-bot")
        root.geometry("760x720")
        root.minsize(680, 600)
        root.configure(bg=BG)

        self.api_key = None
        self.stop_flag = threading.Event()
        self.running = False
        self.busy = False
        self.models = list(FALLBACK_MODELS)
        self.models_loaded = False
        self.models_lock = threading.Lock()
        self.dead_models = load_dead_models()
        self.last_good = None
        self.ui_queue = queue.Queue()
        self.esc_guard_until = 0.0
        self.wrong_set = set()
        self.total_est = 20
        self.think_level = "low"
        self.history = []
        self.notes = []
        self.last_counted_q = ""
        self.pending_confirm = False
        self.finish_ok = False

        self.settings = load_settings()
        self._build_ui()
        self._pump()
        root.report_callback_exception = self._tk_exception

        self.dbg(f"Python {sys.version.split()[0]}, "
                 f"экран {pyautogui.size()[0]}x{pyautogui.size()[1]}")
        self._check_api()

        if keyboard is not None:
            try:
                keyboard.add_hotkey("esc", self._on_esc)
            except Exception as e:
                self.log("ESC не включился (попробуй запустить от админа), "
                         f"жми кнопку Стоп. {e}", "warn")
        else:
            self.log("Модуль keyboard недоступен, ESC не работает. "
                     "Используй кнопку Стоп.", "warn")

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.api_key:
            threading.Thread(target=self.load_models, daemon=True).start()
        else:
            self.log("Нет ключа. Положи рядом файл api.txt и вставь туда "
                     "ключ Gemini.", "err")
            self.log(f"Искал тут: {API_FILE}", "dim")

    # ---------------- интерфейс ----------------
    def _field(self, parent, caption, var, width=6):
        box = tk.Frame(parent, bg=BG)
        tk.Label(box, text=caption, bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        e = tk.Entry(box, textvariable=var, width=width, justify="center",
                     bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat",
                     font=(FONT, 13, "bold"), highlightthickness=1,
                     highlightbackground=LINE, highlightcolor=ACCENT)
        e.pack(ipady=5, pady=(3, 0))
        return box

    def _stat(self, parent, caption):
        card = tk.Frame(parent, bg=PANEL, padx=16, pady=10)
        val = tk.Label(card, text="0", bg=PANEL, fg=TEXT,
                       font=(FONT, 22, "bold"))
        val.pack(anchor="w")
        tk.Label(card, text=caption, bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        return card, val

    def _build_ui(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("T.Horizontal.TProgressbar", troughcolor=PANEL,
                    background=ACCENT, bordercolor=PANEL, lightcolor=ACCENT,
                    darkcolor=ACCENT, thickness=6)
        s.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                    foreground=TEXT, arrowcolor=TEXT, bordercolor=LINE,
                    lightcolor=FIELD, darkcolor=FIELD, selectbackground=FIELD,
                    selectforeground=TEXT)
        s.map("TCombobox", fieldbackground=[("readonly", FIELD)],
              foreground=[("readonly", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

        # шапка
        head = tk.Frame(self.root, bg=BG, padx=22, pady=16)
        head.pack(fill="x")
        tk.Label(head, text="Tesot", bg=BG, fg=TEXT,
                 font=(FONT, 24, "bold")).pack(side="left")
        tk.Label(head, text="-bot", bg=BG, fg=ACCENT,
                 font=(FONT, 24, "bold")).pack(side="left")
        self.status_lbl = tk.Label(head, text="  ожидание", bg=PANEL,
                                   fg=MUTED, font=(FONT, 10, "bold"),
                                   padx=12, pady=5)
        self.status_lbl.pack(side="right")

        # счётчики
        stats = tk.Frame(self.root, bg=BG, padx=22)
        stats.pack(fill="x")
        for i in range(3):
            stats.columnconfigure(i, weight=1, uniform="s")
        c1, self.v_answered = self._stat(stats, "отвечено")
        c2, self.v_wrong = self._stat(stats, "ошибок дано")
        c3, self.v_step = self._stat(stats, "шаг")
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        c2.grid(row=0, column=1, sticky="ew", padx=6)
        c3.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        self.progress = ttk.Progressbar(self.root, style="T.Horizontal."
                                        "TProgressbar", maximum=100)
        self.progress.pack(fill="x", padx=22, pady=(12, 4))

        # настройки
        self.wrong_var = tk.StringVar(value=str(self.settings.get("wrong", 2)))
        self.total_var = tk.StringVar(value=str(self.settings.get("total", 20)))
        self.delay_var = tk.StringVar(value=str(self.settings.get("delay", 3)))
        method0 = self.settings.get("method", "auto")
        think0 = self.settings.get("think", "low")
        self.method_var = tk.StringVar(
            value=next((l for k, l in METHODS if k == method0), METHODS[0][1]))
        self.think_var = tk.StringVar(
            value=next((l for l, k in THINK_LABELS if k == think0),
                       THINK_LABELS[0][0]))

        row = tk.Frame(self.root, bg=BG, padx=22, pady=8)
        row.pack(fill="x")
        self._field(row, "Сколько ошибок сделать", self.wrong_var).pack(
            side="left", padx=(0, 18))
        self._field(row, "Вопросов в тесте", self.total_var).pack(side="left")
        self.more_btn = tk.Label(row, text="настройки  v", bg=BG, fg=MUTED,
                                 font=(FONT, 10), cursor="hand2")
        self.more_btn.pack(side="right", anchor="s", pady=6)
        self.more_btn.bind("<Button-1>", lambda e: self._toggle_more())

        self.more = tk.Frame(self.root, bg=PANEL, padx=22, pady=10)
        self.more_open = False
        self._field(self.more, "Пауза, сек", self.delay_var, 5).pack(
            side="left", padx=(0, 18))
        for cap, var, vals in (("Способ", self.method_var,
                                [l for _k, l in METHODS]),
                               ("Мышление", self.think_var,
                                [l for l, _k in THINK_LABELS])):
            box = tk.Frame(self.more, bg=PANEL)
            box.pack(side="left", padx=(0, 18))
            tk.Label(box, text=cap, bg=PANEL, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w")
            ttk.Combobox(box, textvariable=var, values=vals, width=14,
                         state="readonly").pack(pady=(3, 0), ipady=3)

        # лог
        logwrap = tk.Frame(self.root, bg=LINE, padx=1, pady=1)
        self.logwrap = logwrap
        logwrap.pack(fill="both", expand=True, padx=22, pady=(6, 8))
        self.log_text = scrolledtext.ScrolledText(
            logwrap, font=("Consolas", 10), bg=PANEL, fg=TEXT, relief="flat",
            wrap="word", insertbackground=TEXT, padx=10, pady=8, bd=0)
        self.log_text.pack(fill="both", expand=True)
        for tag, color in (("info", TEXT), ("dim", MUTED), ("ok", GREEN),
                           ("warn", AMBER), ("err", RED), ("head", ACCENT)):
            self.log_text.tag_config(tag, foreground=color)
        self.log_text.tag_config("head", font=("Consolas", 10, "bold"))
        self.log_text.config(state="disabled")

        # низ
        bottom = tk.Frame(self.root, bg=BG, padx=22, pady=4)
        bottom.pack(fill="x")
        self.start_btn = Btn(bottom, "СТАРТ", self.start, bg=GREEN,
                             fg="#0b1a14", size=13, pady=12)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.scan_btn = Btn(bottom, "Проверка", self.test_scan, bg=FIELD,
                            fg=TEXT, size=11, pady=12)
        self.scan_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = Btn(bottom, "СТОП", self.stop, bg=RED, size=13,
                            pady=12, padx=26)
        self.stop_btn.pack(side="left")
        self.stop_btn.set_enabled(False)
        tk.Label(self.root, text="ESC - аварийная остановка. Браузер с тестом "
                 "держи на главном мониторе.", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(pady=(4, 12))

    def _toggle_more(self):
        if self.more_open:
            self.more.pack_forget()
            self.more_btn.config(text="настройки  v")
        else:
            self.more.pack(fill="x", padx=22, pady=(0, 4),
                           before=self.logwrap)
            self.more_btn.config(text="настройки  ^")
        self.more_open = not self.more_open

    def set_status(self, text, color=MUTED):
        self.ui(lambda: self.status_lbl.config(text="  " + text,
                                               fg=color))

    def set_stats(self, answered, wrong_given, step):
        def f():
            self.v_answered.config(text=str(answered))
            self.v_wrong.config(text=str(wrong_given))
            self.v_step.config(text=str(step))
            total = max(self.total_est, 1)
            self.progress["value"] = min(100, answered / total * 100)
        self.ui(f)

    # ---------------- потокобезопасный GUI ----------------
    def _pump(self):
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                try:
                    fn()
                except Exception:
                    pass
        except queue.Empty:
            pass
        try:
            self.root.after(50, self._pump)
        except Exception:
            pass

    def ui(self, fn):
        self.ui_queue.put(fn)

    def dbg(self, msg):
        """Только в файл bot.log."""
        stamp = datetime.now().strftime("%H:%M:%S")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {msg}\n")
        except Exception:
            pass

    def log(self, msg, kind="info"):
        """В окно и в файл."""
        self.dbg(msg)
        stamp = datetime.now().strftime("%H:%M:%S")
        self.ui(lambda: self._log(stamp, msg, kind))

    def _log(self, stamp, msg, kind):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, stamp + "  ", "dim")
        self.log_text.insert(tk.END, msg + "\n", kind)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _tk_exception(self, exc, val, tb):
        self.dbg("ошибка интерфейса: " + "".join(
            traceback.format_exception(exc, val, tb)))

    # ---------------- буфер обмена ----------------
    def clip_set(self, text):
        done = threading.Event()

        def f():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update_idletasks()
            except Exception:
                pass
            finally:
                done.set()
        self.ui(f)
        done.wait(3)

    def clip_get(self):
        holder = [""]
        done = threading.Event()

        def f():
            try:
                holder[0] = self.root.clipboard_get()
            except Exception:
                holder[0] = ""
            finally:
                done.set()
        self.ui(f)
        done.wait(3)
        return holder[0] or ""

    # ---------------- вспомогательное ----------------
    def nap(self, sec):
        """Пауза, которую можно прервать. При стопе кидает Stopped."""
        if self.stop_flag.wait(sec):
            raise Stopped()

    def _mod(self):
        return "command" if sys.platform == "darwin" else "ctrl"

    def _read_float(self, var, default, lo, hi):
        try:
            v = float(str(var.get()).replace(",", ".").strip())
        except Exception:
            return default
        return min(max(v, lo), hi)

    def _method_key(self):
        label = self.method_var.get()
        for k, l in METHODS:
            if l == label:
                return k
        return "auto"

    def _think_key(self):
        label = self.think_var.get()
        for l, k in THINK_LABELS:
            if l == label:
                return k
        return "low"

    def _check_api(self):
        self.api_key = load_api_key()
        if self.api_key:
            self.dbg(f"ключ загружен ({len(self.api_key)} симв.)")
        return bool(self.api_key)

    def _save_settings(self):
        save_settings({
            "wrong": int(self._read_float(self.wrong_var, 2, 0, 999)),
            "total": int(self._read_float(self.total_var, 20, 1, 500)),
            "delay": self._read_float(self.delay_var, 3, 0.5, 120),
            "method": self._method_key(),
            "think": self._think_key(),
        })

    # ---------------- ESC / стоп ----------------
    def _on_esc(self):
        # свои же Esc (закрытие поиска) пропускаем
        if time.time() < self.esc_guard_until:
            return
        if self.running or self.busy:
            self.log("ESC - стоп", "warn")
            self.stop_flag.set()

    def press_esc(self):
        self.esc_guard_until = time.time() + 0.8
        pyautogui.press("esc")

    def stop(self):
        if not self.stop_flag.is_set() and (self.running or self.busy):
            self.log("Останавливаюсь...", "warn")
            self.set_status("остановка", AMBER)
        self.stop_flag.set()

    def _on_close(self):
        self.stop_flag.set()
        self._save_settings()
        if keyboard is not None:
            try:
                keyboard.remove_all_hotkeys()
            except Exception:
                pass
        self.root.destroy()

    # ---------------- модели ----------------
    def load_models(self):
        """Берёт у Google список моделей и выбирает подходящие."""
        with self.models_lock:
            if self.models_loaded or not self.api_key:
                return
            names, err = list_available_models(self.api_key)
            if err:
                self.log(f"Список моделей не получен: {err[:160]}. "
                         f"Работаю со встроенным.", "warn")
                return
            picked = [m for m in pick_vision_models(names)
                      if m not in self.dead_models]
            if picked:
                self.models = picked
                self.models_loaded = True
                self.log(f"Моделей подобрано: {len(picked)} "
                         f"(главная: {picked[0]})", "dim")
                self.dbg("модели: " + ", ".join(picked))
            else:
                self.log("Подходящих моделей не нашёл, беру встроенный "
                         "список.", "warn")

    # ---------------- запрос к моделям ----------------
    def race(self, models, parts, deadline, parallel):
        """Шлёт запрос пачками моделей, берёт первый нормальный JSON."""
        pending = [m for m in models if m not in self.dead_models]
        if not pending:
            raise AllModelsFailed("нет доступных моделей")
        last_err = "нет ответа"
        rate_waits = 0
        think = self.think_level
        while pending:
            self.nap(0)
            remaining = deadline - time.time()
            if remaining < 4:
                raise AllModelsFailed(f"время вышло ({last_err})")
            batch = pending[:parallel]
            pending = pending[parallel:]
            per_timeout = max(8, min(60, remaining))
            q = queue.Queue()

            def run(m):
                try:
                    q.put((m, call_gemini(self.api_key, m, parts, per_timeout,
                                          think), None))
                except BaseException as e:      # noqa: BLE001
                    q.put((m, None, e))

            self.dbg(f"запрос к {', '.join(batch)} (мышление {think})")
            for m in batch:
                threading.Thread(target=run, args=(m,), daemon=True).start()

            t_end = time.time() + per_timeout + 2
            got = 0
            n429 = 0
            retry_wait = 0
            while got < len(batch):
                self.nap(0)
                if time.time() > t_end:
                    self.dbg("пачка не ответила вовремя")
                    last_err = "таймаут моделей"
                    break
                try:
                    m, text, err = q.get(timeout=0.2)
                except queue.Empty:
                    continue
                got += 1
                if err is None:
                    parsed = parse_model_json(text)
                    if parsed is not None:
                        self.dbg(f"ответила {m}")
                        return parsed, m
                    self.dbg(f"{m}: ответ не JSON: "
                             f"{text[:150].replace(chr(10), ' ')}")
                    last_err = f"{m}: ответ не JSON"
                    continue
                if isinstance(err, GeminiError):
                    last_err = f"{m}: {err.status}"
                    self.dbg(f"{m}: {err.status} {err.message[:150]}")
                    if err.fatal:
                        raise err
                    if err.status == 404 or "no longer available" in err.message:
                        self.dead_models.add(m)
                        save_dead_models(self.dead_models)
                        self.log(f"Модель {m} отключена Google, больше "
                                 f"не беру.", "dim")
                    elif err.status == 429:
                        n429 += 1
                        retry_wait = max(retry_wait, err.retry_after or 15)
                else:
                    last_err = f"{m}: {err}"
                    self.dbg(f"{m}: {err}")

            if n429 and n429 >= len(batch) and rate_waits < 2:
                rate_waits += 1
                wait = min(max(retry_wait, 5), 25)
                self.log(f"Лимит запросов, жду {wait:.0f} с", "warn")
                self.nap(wait)
                pending = batch + pending
        raise AllModelsFailed(last_err)

    def model_order(self, prefer_lite=False):
        models = list(self.models)
        if prefer_lite:
            models.sort(key=lambda m: 0 if "lite" in m else 1)
        return [m for m in models if m not in self.dead_models]

    # ---------------- способы чтения экрана ----------------
    def strategy_vision(self, deadline, directive, context, lite=False):
        if lite:
            img = capture_screen(LITE_IMG_SIDE)
            b64 = img_to_b64(img, LITE_JPEG_QUALITY)
        else:
            img = capture_screen()
            b64 = img_to_b64(img)
        self.dbg(f"скриншот {img.size[0]}x{img.size[1]}, "
                 f"{len(b64) * 3 // 4 // 1024} КБ")
        parts = [{"text": build_prompt("vision", directive, context)},
                 {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]
        res, used = self.race(self.model_order(lite), parts, deadline,
                              PARALLEL)
        return res, {"mode": "vision", "img": img, "model": used}

    def read_page_text(self):
        """Ctrl+A, Ctrl+C и чтение буфера. None - если не вышло."""
        mod = self._mod()
        for attempt in (1, 2):
            if attempt == 2:
                _sw, sh = pyautogui.size()
                self.dbg("фокус не на странице, кликаю в левое поле и "
                         "повторяю")
                pyautogui.click(8, sh // 2)
                self.nap(0.3)
            self.clip_set(SENTINEL)
            pyautogui.hotkey(mod, "a")
            self.nap(0.35)
            pyautogui.hotkey(mod, "c")
            self.nap(0.7)
            txt = self.clip_get().strip()
            looks_url = (" " not in txt and "\n" not in txt and
                         ("://" in txt or txt.startswith("www.")))
            if txt and txt != SENTINEL and not looks_url and len(txt) >= 20:
                return txt
            self.dbg(f"попытка {attempt}: текст не скопировался")
        return None

    def strategy_text(self, deadline, directive, context):
        txt = self.read_page_text()
        if not txt:
            raise StrategyFailed("текст страницы не скопировался")
        self.dbg(f"скопировано {len(txt)} симв.")
        if len(txt) > 14000:
            txt = txt[:14000]
        parts = [{"text": build_prompt("text", directive, context, txt)}]
        res, used = self.race(self.model_order(), parts, deadline, PARALLEL)
        return res, {"mode": "text", "img": None, "model": used}

    def acquire(self, method, budget, directive, context):
        """Пробует способы по очереди. Возвращает (res, ctx) или (None, None)."""
        if method == "auto":
            order = ["vision", "text", "vision_lite"]
            if self.last_good in order:
                order.remove(self.last_good)
                order.insert(0, self.last_good)
        elif method == "text":
            order = ["text"]
        else:
            order = ["vision"]

        for name in order:
            self.nap(0)
            self.dbg(f"способ: {STRATEGY_LABELS[name]} (лимит {budget:.0f} с)")
            t0 = time.time()
            deadline = t0 + budget
            try:
                if name == "text":
                    res, ctx = self.strategy_text(deadline, directive, context)
                else:
                    res, ctx = self.strategy_vision(
                        deadline, directive, context,
                        lite=(name == "vision_lite"))
                ctx["strategy"] = name
                self.last_good = name
                self.dbg(f"способ сработал за {time.time() - t0:.1f} с "
                         f"({ctx['model']})")
                return res, ctx
            except (Stopped, GeminiError):
                raise
            except (AllModelsFailed, StrategyFailed) as e:
                self.log(f"Способ «{STRATEGY_LABELS[name]}» не сработал: {e}",
                         "warn")
            except Exception as e:
                self.log(f"Ошибка способа: {e}", "err")
                self.dbg(traceback.format_exc())
        return None, None

    # ---------------- опасные зоны ----------------
    def parse_zones(self, res, ctx):
        """Опасные кнопки, которые нейронка отметила на кадре."""
        zones = []
        raw = res.get("danger_zones")
        if not isinstance(raw, list) or ctx.get("img") is None:
            return zones
        sw, sh = pyautogui.size()
        for z in raw:
            box = get_box(z)
            if not box:
                continue
            rect = box_to_rect(box, ctx["img"].size, (sw, sh))
            area = max(rect[2] - rect[0], 0) * max(rect[3] - rect[1], 0)
            # слишком большая рамка - нейронка ошиблась, иначе заблокирует всё
            if area > 0.15 * sw * sh or area <= 0:
                continue
            zones.append((rect, str(z.get("text") or "кнопка")[:40]))
        return zones

    def check_zone(self, pt, ctx):
        x, y = pt
        for (x1, y1, x2, y2), text in ctx.get("zones", []):
            if (x1 - ZONE_MARGIN <= x <= x2 + ZONE_MARGIN and
                    y1 - ZONE_MARGIN <= y <= y2 + ZONE_MARGIN):
                raise Blocked(f"точка клика попадает на кнопку «{text}»")

    def check_action(self, do, a):
        """Проверка по тексту: можно ли вообще жать эту кнопку."""
        if do not in CLICKS:
            return
        kind = str(a.get("kind") or "").lower()
        if kind in SAFE_KINDS:
            return          # варианты ответа и списки - по тексту не судим
        el = str(a.get("element_text") or "").strip()
        text = el or " ".join(str(a.get(k) or "") for k in
                              ("label", "find_text", "text"))
        m = DANGER_RE.search(text)
        if m:
            raise Blocked(f"опасная кнопка («{m.group(0)}»)")
        if kind == "button" or el:
            if not el:
                raise Blocked("у кнопки нет надписи, не могу проверить")
            if FINISH_RE.search(el):
                if not self.finish_ok:
                    raise Blocked(f"«{el}»: тест ещё не закончился")
                return
            if not ALLOW_RE.search(el):
                raise Blocked(f"«{el}» не кнопка ответа")

    # ---------------- действия мышью и клавиатурой ----------------
    def click_point(self, px, py, kind="click"):
        pyautogui.moveTo(px, py, duration=random.uniform(0.15, 0.35))
        if kind == "double_click":
            pyautogui.doubleClick(px, py)
        elif kind == "right_click":
            pyautogui.rightClick(px, py)
        else:
            pyautogui.click(px, py)

    def type_text(self, text, clear=True):
        mod = self._mod()
        if clear:
            pyautogui.hotkey(mod, "a")
            self.nap(0.12)
            pyautogui.press("backspace")
            self.nap(0.12)
        if not text:
            return
        if sys.platform.startswith("win") and len(text) <= 600:
            try:
                for ch in text:
                    self.nap(0)
                    if ch == "\r":
                        continue
                    if ch == "\n":
                        pyautogui.press("enter")
                    else:
                        win_send_unicode_char(ch)
                    time.sleep(random.uniform(0.008, 0.03))
                return
            except Stopped:
                raise
            except Exception as e:
                self.dbg(f"печать не сработала ({e}), вставляю из буфера")
        self.clip_set(text)
        self.nap(0.2)
        pyautogui.hotkey(mod, "v")
        self.nap(0.2)

    def press_keys(self, keys):
        keys = str(keys or "").lower().replace(" ", "")
        if not keys:
            return False
        if keys in BLOCKED_KEYS:
            self.log(f"Сочетание {keys} запрещено, пропускаю", "warn")
            return False
        parts = [("command" if p == "ctrl" and sys.platform == "darwin" else p)
                 for p in keys.split("+") if p]
        if not parts:
            return False
        if len(parts) == 1:
            if parts[0] in ("esc", "escape"):
                self.press_esc()
            else:
                pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)
        return True

    def scroll_page(self, direction="down", amount="medium", at=None):
        sw, sh = pyautogui.size()
        px, py = at if at else (sw // 2, sh // 2)
        clicks = {"small": 300, "medium": 600, "large": 1000}.get(
            str(amount).lower(), 600)
        if str(direction).lower() in ("up", "вверх"):
            clicks = abs(clicks)
        else:
            clicks = -abs(clicks)
        pyautogui.moveTo(px, py, duration=0.15)
        pyautogui.scroll(clicks)

    def locate_text_on_screen(self, text):
        """Ищет текст через Ctrl+F по цвету подсветки. (x, y) или None."""
        mod = self._mod()
        sw, sh = pyautogui.size()
        for sn in make_snippets(text):
            self.nap(0)
            self.clip_set(sn)
            pyautogui.hotkey(mod, "f")
            self.nap(0.4)
            pyautogui.hotkey(mod, "a")
            pyautogui.hotkey(mod, "v")
            self.nap(0.7)
            img = ImageGrab.grab()
            pt = find_highlight_point(img)
            self.press_esc()
            self.nap(0.2)
            if pt:
                x = int(pt[0] * sw / img.size[0])
                y = int(pt[1] * sh / img.size[1])
                self.dbg(f"нашёл «{sn[:30]}» поиском браузера ({x},{y})")
                return x, y
            self.dbg(f"«{sn[:30]}» не найден, пробую короче")
        return None

    def point_for(self, obj, ctx, jitter=True):
        if not isinstance(obj, dict):
            return None
        box = get_box(obj)
        if box and ctx.get("img") is not None:
            sw, sh = pyautogui.size()
            return box_to_screen_point(box, ctx["img"].size, (sw, sh), jitter)
        txt = obj.get("find_text") or obj.get("text")
        if txt:
            return self.locate_text_on_screen(str(txt))
        return None

    def has_target(self, a):
        return bool(get_box(a) or a.get("find_text") or a.get("text"))

    def do_action(self, do, a, ctx, label):
        """Одно действие. True - получилось."""
        kind = str(a.get("kind") or "").lower()

        if do in CLICKS:
            pt = self.point_for(a, ctx, jitter=(kind != "dropdown_item"))
            if not pt:
                self.log(f"Не нашёл «{label}», пропускаю", "warn")
                return False
            self.check_zone(pt, ctx)
            self.click_point(pt[0], pt[1], do)
            self.dbg(f"{do} «{label}» ({pt[0]},{pt[1]})")
            if a.get("tab_after"):
                self.nap(0.2)
                pyautogui.press("tab")
            return True

        if do == "type":
            value = a.get("value")
            if value is None:
                value = a.get("input") or a.get("answer") or ""
            value = str(value)
            if self.has_target(a):
                pt = self.point_for(a, ctx)
                if not pt:
                    self.log(f"Не нашёл поле «{label}», ввод пропущен", "warn")
                    return False
                self.check_zone(pt, ctx)
                self.click_point(pt[0], pt[1])
                if a.get("tab_after"):
                    self.nap(0.2)
                    pyautogui.press("tab")
                self.nap(0.35)
            self.type_text(value, clear=bool(a.get("clear", True)))
            self.dbg(f"введено «{value[:80]}»")
            if a.get("enter"):
                self.nap(0.2)
                pyautogui.press("enter")
            return True

        if do == "select":
            value = str(a.get("value") or "")
            pt = self.point_for(a, ctx)
            if not pt:
                self.log(f"Не нашёл список «{label}», пропускаю", "warn")
                return False
            self.check_zone(pt, ctx)
            self.click_point(pt[0], pt[1])
            self.nap(0.6)
            if value:
                self.type_text(value[:14], clear=False)
                self.nap(0.3)
            pyautogui.press("enter")
            self.dbg(f"выбран пункт «{value[:40]}» (набор + Enter)")
            return True

        if do == "scroll":
            at = self.point_for(a, ctx, jitter=False) \
                if self.has_target(a) else None
            self.scroll_page(a.get("direction", "down"),
                             a.get("amount", "medium"), at)
            self.nap(0.5)
            return True

        if do == "drag":
            p1 = self.point_for(a, ctx)
            p2 = self.point_for({"box_2d": a.get("to_box_2d"),
                                 "find_text": a.get("to_find_text")}, ctx)
            if not p1 or not p2:
                self.log(f"Не нашёл цели перетаскивания «{label}»", "warn")
                return False
            self.check_zone(p1, ctx)
            pyautogui.moveTo(p1[0], p1[1], duration=0.25)
            pyautogui.mouseDown()
            self.nap(0.15)
            pyautogui.moveTo(p2[0], p2[1], duration=0.6)
            self.nap(0.15)
            pyautogui.mouseUp()
            return True

        if do == "key":
            return self.press_keys(a.get("keys") or a.get("key"))

        if do == "wait":
            sec = min(max(self._num(a.get("seconds"), 1.0), 0.2), 5.0)
            self.nap(sec)
            return True

        self.dbg(f"неизвестное действие «{do}», пропускаю")
        return False

    @staticmethod
    def _num(v, default):
        try:
            return float(v)
        except Exception:
            return default

    def exec_actions(self, actions, ctx):
        """
        Выполняет план. Возвращает словарь: done / failed / blocked / rescan /
        interrupted / confirmed / trace / base0.
        """
        stats = {"done": 0, "failed": 0, "blocked": 0, "rescan": False,
                 "interrupted": False, "confirmed": False, "trace": [],
                 "base0": grab_thumb()}
        base = stats["base0"]
        vision = ctx.get("img") is not None
        for i, a in enumerate(actions):
            self.nap(0)
            do = str(a.get("do") or a.get("action") or "").lower().strip()
            kind = str(a.get("kind") or "").lower()
            label = str(a.get("label") or a.get("element_text") or
                        a.get("find_text") or a.get("text") or "")[:50]
            tag = f"{do}/{kind or '?'} «{label}»{pos_str(a)}"
            if a.get("value") is not None and do in ("type", "select"):
                tag += f" value=«{str(a.get('value'))[:40]}»"

            try:
                self.check_action(do, a)
                ok = self.do_action(do, a, ctx, label)
            except Stopped:
                raise
            except Blocked as b:
                self.log(f"Заблокировано: {label or do} - {b}", "err")
                stats["blocked"] += 1
                stats["failed"] += 1
                stats["trace"].append(
                    tag + f" ЗАБЛОКИРОВАНО защитой ({b}). Эту кнопку не жми")
                self.add_note(f"кнопка/зона «{label}» запрещена, не нажимать")
                break
            except Exception as e:
                self.log(f"Ошибка действия {do}: {e}", "err")
                self.dbg(traceback.format_exc())
                ok = False

            if not ok:
                stats["failed"] += 1
                stats["trace"].append(tag + " не удалось (цель не найдена)")
                self.dbg("дальше по плану не иду, пересканирую")
                break
            stats["done"] += 1
            stats["trace"].append(tag + " ok")

            if do in CLICKS and (kind == "button" or a.get("element_text")):
                stats["confirmed"] = True
                self.log(f"Нажал «{a.get('element_text') or label}»", "dim")
            elif do in CLICKS or do in ("type", "select", "drag"):
                self.log(f"{do}: {label}", "dim")

            if a.get("rescan_after") or kind == "dropdown":
                stats["rescan"] = True
                break
            if i < len(actions) - 1:
                self.nap(random.uniform(0.25, 0.6))
                # раскладка могла сдвинуться, старые координаты опасны
                if vision and do in CLICKS + ("type", "select", "drag", "key"):
                    cur = grab_thumb()
                    d = frame_diff(base, cur)
                    if d is not None and d > LAYOUT_SHIFT:
                        self.log(f"Экран изменился на {d * 100:.0f}%, остаток "
                                 f"плана отложен", "dim")
                        stats["rescan"] = True
                        stats["interrupted"] = True
                        stats["trace"].append(
                            "экран сдвинулся, остальные шаги отложены")
                        break
                    if cur:
                        base = cur
        return stats

    # ---------------- память ----------------
    def add_history(self, it, res, plan_str, result):
        q = re.sub(r"\s+", " ", str(res.get("question", "")).strip())
        self.history.append({
            "it": it,
            "q": q[:80],
            "summary": re.sub(r"\s+", " ", str(res.get("summary", "")))[:140],
            "plan": plan_str[:420],
            "result": result[:240],
        })
        self.history = self.history[-HISTORY_KEEP:]

    def add_note(self, text):
        t = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(t) < 6:
            return
        t = t[:220]
        if any(t.lower() == n.lower() for n in self.notes):
            return
        self.notes.append(t)
        self.notes = self.notes[-8:]
        self.log(f"Заметка: {t}", "dim")

    def stuck_hint(self, level):
        if level <= 0:
            return ""
        s = (f"ВНИМАНИЕ: прошлые действия не дали результата (экран не менялся, "
             f"цель не нашлась, кнопка заблокирована или план повторился) уже "
             f"{level} раз подряд. НЕ повторяй те же клики и не кликай в те же "
             f"координаты. ")
        if level == 1:
            s += ("Проверь: возможно, ответ УЖЕ выбран (в списке показано "
                  "значение) - тогда нужна кнопка подтверждения, а не новый клик "
                  "по списку. Или нужная кнопка ниже - прокрути.")
        elif level == 2:
            s += ("Переосмысли экран: какое состояние у вопроса, какая кнопка "
                  "ведёт дальше? Попробуй другое: scroll, клавиши (tab/enter), "
                  "другой элемент.")
        else:
            s += ("КРИТИЧНО: ты зациклился. Сделай принципиально другое: scroll "
                  "вниз/вверх, key enter, клик по другой кнопке перехода. Если "
                  "вопросов больше нет и видны итоги - state \"finished\".")
        return s

    def build_context(self, stuck):
        lines = []
        if self.history:
            lines.append("ПРОШЛЫЕ ШАГИ (от старых к новым):")
            for h in self.history[-HISTORY_IN_PROMPT:]:
                lines.append(f"  #{h['it']} | вопрос: «{h['q']}» | видел: "
                             f"{h['summary']} | сделал: {h['plan']} | итог: "
                             f"{h['result']}")
        if self.notes:
            lines.append("ЗАМЕТКИ ОБ ЭТОМ САЙТЕ (учитывай):")
            for n in self.notes:
                lines.append(f"  - {n}")
        if self.pending_confirm:
            lines.append("ВАЖНО: ответ на текущий вопрос уже выбран/введён, но "
                         "кнопка подтверждения ещё НЕ нажата, вопрос не "
                         "засчитан. Ответ не меняй, найди кнопку подтверждения "
                         "(«Ответить», «Проверить» и т.п.) и нажми её.")
        hint = self.stuck_hint(stuck)
        if hint:
            lines.append(hint)
        if not lines:
            return "Это первый шаг, истории ещё нет."
        return "\n".join(lines)

    # ---------------- план неправильных ответов ----------------
    def plan_wrong(self, count, answered, total):
        pool = list(range(answered + 1, max(total, answered + 1) + 1))
        k = min(max(count, 0), len(pool))
        self.wrong_set = set(random.sample(pool, k)) if k else set()
        if self.wrong_set:
            self.log(f"Ошибки будут в вопросах: {sorted(self.wrong_set)} "
                     f"(из ~{total})", "dim")

    def make_directive(self, answered):
        base = (f"Счётчик: полностью отвечено вопросов: {answered}. Вопрос, на "
                f"который ты отвечаешь следующим, имеет номер {answered + 1}, "
                f"затем {answered + 2} и т.д. answers_count считай только за "
                f"вопросы, на которые ответ ВЫБИРАЕТСЯ/ВВОДИТСЯ в этом плане "
                f"(не за подтверждение уже выбранного ответа).")
        nums = sorted(n for n in self.wrong_set
                      if answered < n <= answered + 15)
        if nums:
            base += (f"\nНЕПРАВИЛЬНО (выбери правдоподобный, но заведомо неверный "
                     f"вариант / впиши неверный ответ) нужно ответить на "
                     f"вопросы с номерами: {nums}. На остальные - ПРАВИЛЬНО. "
                     f"Если в этом плане ты сознательно ответил неверно - "
                     f"wrong_applied=true.")
        else:
            base += "\nВсе вопросы отвечай ПРАВИЛЬНО, wrong_applied=false."
        return base

    # ---------------- вывод плана ----------------
    def log_plan(self, res, actions):
        refl = str(res.get("reflection") or "").strip()
        if refl:
            self.log(refl[:200], "dim")
        q = str(res.get("question", "")).strip()
        if q:
            self.log(f"Вопрос: {q[:140]}", "head")
        self.dbg(f"state={res.get('state')} summary={res.get('summary')} "
                 f"progress={res.get('progress')} "
                 f"answers_count={res.get('answers_count')} "
                 f"wrong_applied={res.get('wrong_applied')}")
        for i, a in enumerate(actions, 1):
            extra = ""
            if a.get("value") is not None:
                extra += f" value=«{str(a.get('value'))[:60]}»"
            if a.get("rescan_after"):
                extra += " [rescan]"
            tgt = a.get("box_2d") or a.get("find_text") or ""
            el = a.get("element_text")
            el_s = f" [кнопка: «{el}»]" if el else ""
            self.dbg(f"  {i}. {a.get('do')}/{a.get('kind', '?')} "
                     f"«{a.get('label', '')}»{el_s} {tgt}{extra}")

    # ---------------- пробный кадр ----------------
    def test_scan(self):
        if self.busy or self.running:
            return
        if not self._check_api():
            messagebox.showerror("Tesot-bot", "Нет ключа в api.txt")
            return
        self.busy = True
        self.stop_flag.clear()
        self.scan_btn.set_enabled(False)
        self.start_btn.set_enabled(False)
        method = self._method_key()
        budget = 40
        self.think_level = self._think_key()
        self.set_status("проверка", AMBER)
        self.root.iconify()

        def worker():
            try:
                self.log("Проверка: через 3 секунды смотрю экран, ничего не "
                         "нажимаю. Переключись на тест.", "head")
                self.load_models()
                self.nap(3)
                directive = ("Счётчик: отвечено вопросов: 0. Все вопросы "
                             "отвечай ПРАВИЛЬНО, wrong_applied=false.")
                res, ctx = self.acquire(method, budget, directive,
                                        "Пробный кадр, истории нет.")
                if res is None:
                    self.log("Ни один способ не сработал. Подробности в "
                             "bot.log", "err")
                    return
                actions = norm_actions(res)
                ctx["zones"] = self.parse_zones(res, ctx)
                self.log_plan(res, actions)
                for i, a in enumerate(actions, 1):
                    self.log(f"  {i}. {a.get('do')} ({a.get('kind', '?')}): "
                             f"{a.get('element_text') or a.get('label', '')}",
                             "info")
                zl = [t for _r, t in ctx["zones"]]
                if zl:
                    self.log("Опасные кнопки на экране: " + ", ".join(zl),
                             "warn")
                img = ctx.get("img") or capture_screen()
                if ctx["mode"] == "vision":
                    p = save_debug_image(img, actions,
                                         raw_zones(res))
                    if p:
                        self.log("Рамки сохранены в last_scan.jpg", "dim")
                self.log("Проверка готова. Если план верный - жми СТАРТ.",
                         "ok")
            except Stopped:
                self.log("Проверка прервана", "warn")
            except GeminiError as e:
                self.log(f"{e}", "err")
            except Exception as e:
                self.log(f"Ошибка проверки: {e}", "err")
                self.dbg(traceback.format_exc())
            finally:
                self.busy = False
                self.set_status("ожидание", MUTED)
                self.ui(self.root.deiconify)
                self.ui(lambda: self.scan_btn.set_enabled(True))
                self.ui(lambda: self.start_btn.set_enabled(True))

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- старт ----------------
    def start(self):
        if self.running or self.busy:
            return
        if not self._check_api():
            messagebox.showerror("Tesot-bot", "Нет ключа в api.txt")
            return
        self._save_settings()
        delay = self._read_float(self.delay_var, 3, 0.5, 120)
        wrong = int(self._read_float(self.wrong_var, 2, 0, 999))
        total = int(self._read_float(self.total_var, 20, 1, 500))
        method = self._method_key()
        think_base = self._think_key()

        self.running = True
        self.stop_flag.clear()
        self.start_btn.set_enabled(False)
        self.scan_btn.set_enabled(False)
        self.stop_btn.set_enabled(True)
        self.set_status("работает", GREEN)
        self.set_stats(0, 0, 0)
        self.root.iconify()
        threading.Thread(
            target=self.worker,
            args=(delay, wrong, total, method, think_base),
            daemon=True).start()

    def worker(self, delay, wrong, total, method, think_base):
        budget = 40
        answered = 0
        wrong_given = 0
        fails = 0
        empty_screens = 0
        finished_hits = 0
        same_plan = 0       # подряд повторов плана без эффекта
        no_effect = 0       # подряд планов, не изменивших экран
        prev_sig = None
        synced = False
        it = 0
        MAX_FAILS = 4
        self.history = []
        self.notes = []
        self.last_counted_q = ""
        self.pending_confirm = False
        try:
            self.total_est = total
            self.load_models()
            self.log(f"Старт. Вопросов ~{total}, ошибок: {wrong}. "
                     f"Не трогай мышь и клавиатуру.", "head")
            self.plan_wrong(wrong, answered, total)
            for i in range(3, 0, -1):
                self.nap(1)

            while not self.stop_flag.is_set():
                it += 1
                if it > MAX_ITERATIONS:
                    self.log("Лимит итераций, стоп", "warn")
                    break

                stuck = max(same_plan, no_effect)
                if stuck >= STOP_STUCK_LEVEL:
                    self.log("Слишком много безрезультатных попыток подряд, "
                             "останавливаюсь. Смотри last_scan.jpg и bot.log",
                             "err")
                    break

                # при зацикливании мышление растёт само
                bump = "low" if stuck == 0 else ("medium" if stuck == 1
                                                 else "high")
                self.think_level = max(
                    (think_base, bump), key=lambda k: THINK_RANK[k])
                budget_eff = budget + (20 if stuck >= 2 else 0)

                self.set_stats(answered, wrong_given, it)
                self.log(f"Шаг {it}" + (f"  (застряли: {stuck})" if stuck
                                        else ""), "dim")

                directive = self.make_directive(answered)
                context = self.build_context(stuck)
                try:
                    res, ctx = self.acquire(method, budget_eff, directive,
                                            context)
                except GeminiError as e:
                    self.log(f"{e}", "err")
                    self.log("Скорее всего проблема с ключом (api.txt)", "err")
                    break

                if res is None:
                    fails += 1
                    self.log(f"Нет ответа от нейронки ({fails}/{MAX_FAILS}), "
                             f"пауза 5 с", "warn")
                    if fails >= MAX_FAILS:
                        self.log("Слишком много неудач, останавливаюсь.", "err")
                        break
                    self.nap(5)
                    continue
                fails = 0

                actions = norm_actions(res)
                ctx["zones"] = self.parse_zones(res, ctx)
                self.log_plan(res, actions)
                self.add_note(res.get("learned"))
                if ctx.get("img") is not None:
                    save_debug_image(ctx["img"], actions, raw_zones(res))

                # прогресс «вопрос N из M» со страницы
                prog = res.get("progress")
                cur = tot = None
                if isinstance(prog, dict):
                    cur, tot = to_int(prog.get("current")), to_int(
                        prog.get("total"))
                replan = False
                if tot and 1 <= tot <= 500 and tot != self.total_est:
                    self.log(f"На странице указано вопросов: {tot}", "dim")
                    self.total_est = tot
                    replan = True
                if not synced:
                    synced = True
                    if cur and cur > 1 and answered == 0:
                        answered = cur - 1
                        self.log(f"Тест начат с вопроса {cur}, "
                                 f"подгоняю счётчик", "dim")
                        self.plan_wrong(wrong - wrong_given, answered,
                                        self.total_est)
                        continue
                if replan:
                    self.plan_wrong(wrong - wrong_given, answered,
                                    self.total_est)

                # «Завершить» разрешаем только на последнем вопросе
                self.finish_ok = bool(
                    answered >= self.total_est - 1 or
                    (cur and tot and cur >= tot) or
                    str(res.get("state", "")).lower() == "finished")

                # конец теста
                finished = (bool(res.get("is_test_finished")) or
                            str(res.get("state", "")).lower() == "finished")
                if finished and not actions:
                    finished_hits += 1
                    if finished_hits >= 2:
                        self.log("Тест завершён", "ok")
                        break
                    self.nap(2)
                    continue
                finished_hits = 0

                # пустой план - крутим вниз
                if not actions:
                    empty_screens += 1
                    self.log(f"План пуст ({empty_screens}/4), прокручиваю вниз",
                             "dim")
                    self.add_history(it, res, "план пуст, робот прокрутил вниз",
                                     "-")
                    if empty_screens >= 4:
                        self.log("Ничего не нашлось 4 раза подряд, считаю тест "
                                 "завершённым", "ok")
                        break
                    self.scroll_page("down", "medium")
                    self.nap(1.0)
                    continue
                empty_screens = 0

                # тот же план при застревании не выполняем
                sig = plan_sig(res, actions)
                repeat = (sig == prev_sig)
                if repeat and stuck >= 3:
                    self.log("Нейронка предлагает то же самое, не выполняю, "
                             "прокручиваю вниз", "warn")
                    self.add_history(
                        it, res, "повтор прошлого плана, робот НЕ выполнил, "
                                 "прокрутил вниз",
                        "ты зациклился: сделай ДРУГОЕ действие")
                    self.scroll_page("down", "medium")
                    same_plan += 1
                    self.nap(1.0)
                    continue

                # выполняем
                stats = self.exec_actions(actions, ctx)

                # считаем вопросы
                n = to_int(res.get("answers_count")) or 0
                qn = norm_q(res.get("question"))
                if n > 0 and qn and qn == self.last_counted_q:
                    n = 0
                good = (stats["failed"] == 0 and stats["done"] > 0)
                if n > 0 and good:
                    if qn:
                        self.last_counted_q = qn
                    applied = bool(res.get("wrong_applied"))
                    hits = [k for k in range(answered + 1, answered + n + 1)
                            if k in self.wrong_set]
                    if hits and applied:
                        wrong_given += len(hits)
                        self.log(f"Ошибка дана в вопросе {hits} "
                                 f"({wrong_given}/{wrong})", "dim")
                    elif hits and not applied:
                        # модель не ошиблась - переносим ошибку на другой вопрос
                        self.wrong_set.difference_update(hits)
                        pool = [k for k in range(answered + n + 1,
                                                 self.total_est + 1)
                                if k not in self.wrong_set]
                        for _ in hits:
                            if pool:
                                nk = random.choice(pool)
                                pool.remove(nk)
                                self.wrong_set.add(nk)
                    answered += n
                    self.log(f"Ответ выбран (всего {answered})", "ok")
                    if not stats["confirmed"]:
                        self.pending_confirm = True
                if stats["confirmed"] and not stats["blocked"]:
                    self.pending_confirm = False
                self.set_stats(answered, wrong_given, it)

                # пауза и проверка: изменился ли экран
                self.nap(0.9 if stats["rescan"] else delay)
                after = grab_thumb()
                d = frame_diff(stats.get("base0"), after)

                parts = [f"выполнено {stats['done']}/{len(actions)}"]
                if stats["blocked"]:
                    parts.append("робот ЗАБЛОКИРОВАЛ опасную кнопку")
                elif stats["failed"]:
                    parts.append("действие не удалось (цель не найдена)")
                if stats["interrupted"]:
                    parts.append("план прерван: экран сдвинулся")
                parts.append("экран после действий: " + describe_change(d))
                result = "; ".join(parts)
                self.dbg(f"итог шага: {result}")
                self.add_history(it, res, " -> ".join(stats["trace"]) or "-",
                                 result)

                # счётчики застревания
                screen_same = (d is not None and d < NO_CHANGE)
                if stats["blocked"] or (stats["failed"] and not stats["done"]):
                    no_effect += 1
                elif stats["done"] > 0 and screen_same:
                    no_effect += 1
                else:
                    no_effect = 0
                if repeat and (d is None or d < 0.05):
                    same_plan += 1
                else:
                    same_plan = 0
                prev_sig = sig

            self.log(f"Готово. Шагов: {it}, отвечено: {answered}, "
                     f"ошибок дано: {wrong_given}", "ok")
            self.set_status("готово", GREEN)

        except Stopped:
            self.log("Остановлено", "warn")
            self.set_status("остановлено", RED)
        except Exception as e:
            self.log(f"Критическая ошибка: {e}", "err")
            self.dbg(traceback.format_exc())
            self.set_status("ошибка", RED)
        finally:
            self.running = False
            self.set_stats(answered, wrong_given, it)
            self.ui(self.root.deiconify)
            self.ui(lambda: self.start_btn.set_enabled(True))
            self.ui(lambda: self.scan_btn.set_enabled(True))
            self.ui(lambda: self.stop_btn.set_enabled(False))


def raw_zones(res):
    z = res.get("danger_zones") if isinstance(res, dict) else None
    return [x for x in z if isinstance(x, dict)] if isinstance(z, list) else []


# ---------------------------------------------------------------------
# запуск
# ---------------------------------------------------------------------
def main():
    root = tk.Tk()
    App(root)
    try:
        root.mainloop()
    finally:
        if keyboard is not None:
            try:
                keyboard.remove_all_hotkeys()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        print(err)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(err + "\n")
        except Exception:
            pass
        try:
            input("Критическая ошибка (см. выше). Enter...")
        except Exception:
            pass