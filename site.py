import sys
import subprocess
import importlib
import time
import random
import threading
import webbrowser

# --- АВТОУСТАНОВКА БИБЛИОТЕК ---
def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package,
                                   "--quiet", "--disable-pip-version-check"])
        except Exception:
            pass

install_and_import('flask')

from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'moodle_natc_secret_key_2024_x9'
app.config['PROPAGATE_EXCEPTIONS'] = False
app.config['TRAP_HTTP_EXCEPTIONS'] = False

LANGUAGES = ['ru', 'uk', 'en']
DEFAULT_LANG = 'ru'

# ============================================================
#  UI ПЕРЕВОДЫ
# ============================================================
UI = {
    'ru': {
        'site_brand': '🎓 Учебно-информационный портал',
        'menu_courses': '📚 Мои курсы',
        'menu_calendar': '📅 Календарь',
        'menu_profile': '👤 Профиль',
        'menu_settings': '⚙️ Настройки',
        'menu_help': '❓ Справка',
        'nav_home': 'Главная',
        'nav_disciplines': 'Мои дисциплины',
        'nav_testing': 'Тестирование',
        'nav_gradebook': 'Журнал оценок',
        'nav_messages': 'Сообщения',
        'breadcrumb_home': 'Главная',
        'breadcrumb_programming': 'Программирование',
        'breadcrumb_final_test': 'Итоговый тест',
        'test_navigation': 'Навигация по тесту',
        'question_x_of_y': 'Вопрос {q} из {total}',
        'duration': 'Длительность:',
        'duration_value': '30 мин',
        'attempt': 'Попытка:',
        'attempt_value': '1 из 3',
        'grading_method': 'Метод оценивания:',
        'grading_value': 'Последняя попытка',
        'start_over': '↻ Начать заново',
        'question_prefix': 'Вопрос ',
        'select_one': 'Выберите один правильный ответ:',
        'multiple_hint': '⚠ В этом вопросе НЕСКОЛЬКО правильных ответов. Отметьте все.',
        'select_from_list': 'Выберите правильный вариант из списка:',
        'enter_answer': 'Введите ответ:',
        'select_placeholder': '-- Выберите вариант --',
        'answer_placeholder': 'Ваш ответ...',
        'btn_answer': 'Ответить',
        'btn_flag': 'Отметить для просмотра',
        'btn_draft': 'Сохранить черновик',
        'btn_cancel': 'Отменить попытку',
        'my_subjects': 'Мои предметы',
        'tools': 'Инструменты',
        'gradebook_tool': '📊 Журнал оценок',
        'my_works': '📝 Мои работы',
        'messages_tool': '🔔 Сообщения',
        'course_files': '📎 Файлы курса',
        'footer_portal': 'Учебно-информационный портал © 2024',
        'privacy': 'Политика конфиденциальности',
        'help': 'Справка',
        'contacts': 'Контакты',
        'result_title': 'Результат тестирования',
        'result_nav': '📊 Результат тестирования',
        'test_completed': 'Тестирование завершено',
        'your_result': 'Ваш результат:',
        'completion_time': 'Время прохождения:',
        'answer_review': 'Разбор ответов:',
        'question_label': 'Вопрос:',
        'your_answer': 'Ваш ответ:',
        'correct_answer_label': 'Правильный ответ:',
        'take_again': 'Пройти снова',
        'nothing_selected': '[ничего не выбрано]',
        'hp_email': 'Email подтверждения',
        'hp_website': 'Веб-сайт',
        'hp_search': 'Поисковый запрос',
        'hp_captcha': 'Код капчи',
        'hp_newsletter': 'Email для подписки',
        'hp_robot': 'Я не робот',
        'hp_submit': 'Отправить',
    },
    'uk': {
        'site_brand': '🎓 Навчально-інформаційний портал',
        'menu_courses': '📚 Мої курси',
        'menu_calendar': '📅 Календар',
        'menu_profile': '👤 Профіль',
        'menu_settings': '⚙️ Налаштування',
        'menu_help': '❓ Довідка',
        'nav_home': 'Головна',
        'nav_disciplines': 'Мої дисципліни',
        'nav_testing': 'Тестування',
        'nav_gradebook': 'Журнал оцінок',
        'nav_messages': 'Повідомлення',
        'breadcrumb_home': 'Головна',
        'breadcrumb_programming': 'Програмування',
        'breadcrumb_final_test': 'Підсумковий тест',
        'test_navigation': 'Навігація по тесту',
        'question_x_of_y': 'Питання {q} з {total}',
        'duration': 'Тривалість:',
        'duration_value': '30 хв',
        'attempt': 'Спроба:',
        'attempt_value': '1 з 3',
        'grading_method': 'Метод оцінювання:',
        'grading_value': 'Остання спроба',
        'start_over': '↻ Розпочати спочатку',
        'question_prefix': 'Питання ',
        'select_one': 'Оберіть одну правильну відповідь:',
        'multiple_hint': '⚠ У цьому питанні ДЕКІЛЬКА правильних відповідей. Позначте всі.',
        'select_from_list': 'Оберіть правильний варіант зі списку:',
        'enter_answer': 'Введіть відповідь:',
        'select_placeholder': '-- Оберіть варіант --',
        'answer_placeholder': 'Ваша відповідь...',
        'btn_answer': 'Відповісти',
        'btn_flag': 'Позначити для перегляду',
        'btn_draft': 'Зберегти чернетку',
        'btn_cancel': 'Скасувати спробу',
        'my_subjects': 'Мої предмети',
        'tools': 'Інструменти',
        'gradebook_tool': '📊 Журнал оцінок',
        'my_works': '📝 Мої роботи',
        'messages_tool': '🔔 Повідомлення',
        'course_files': '📎 Файли курсу',
        'footer_portal': 'Навчально-інформаційний портал © 2024',
        'privacy': 'Політика конфіденційності',
        'help': 'Довідка',
        'contacts': 'Контакти',
        'result_title': 'Результат тестування',
        'result_nav': '📊 Результат тестування',
        'test_completed': 'Тестування завершено',
        'your_result': 'Ваш результат:',
        'completion_time': 'Час проходження:',
        'answer_review': 'Розбір відповідей:',
        'question_label': 'Питання:',
        'your_answer': 'Ваша відповідь:',
        'correct_answer_label': 'Правильна відповідь:',
        'take_again': 'Пройти знову',
        'nothing_selected': '[нічого не обрано]',
        'hp_email': 'Email підтвердження',
        'hp_website': 'Веб-сайт',
        'hp_search': 'Пошуковий запит',
        'hp_captcha': 'Код капчі',
        'hp_newsletter': 'Email для підписки',
        'hp_robot': 'Я не робот',
        'hp_submit': 'Надіслати',
    },
    'en': {
        'site_brand': '🎓 Educational Information Portal',
        'menu_courses': '📚 My courses',
        'menu_calendar': '📅 Calendar',
        'menu_profile': '👤 Profile',
        'menu_settings': '⚙️ Settings',
        'menu_help': '❓ Help',
        'nav_home': 'Home',
        'nav_disciplines': 'My disciplines',
        'nav_testing': 'Testing',
        'nav_gradebook': 'Gradebook',
        'nav_messages': 'Messages',
        'breadcrumb_home': 'Home',
        'breadcrumb_programming': 'Programming',
        'breadcrumb_final_test': 'Final test',
        'test_navigation': 'Test navigation',
        'question_x_of_y': 'Question {q} of {total}',
        'duration': 'Duration:',
        'duration_value': '30 min',
        'attempt': 'Attempt:',
        'attempt_value': '1 of 3',
        'grading_method': 'Grading method:',
        'grading_value': 'Last attempt',
        'start_over': '↻ Start over',
        'question_prefix': 'Question ',
        'select_one': 'Choose one correct answer:',
        'multiple_hint': '⚠ This question has MULTIPLE correct answers. Mark all.',
        'select_from_list': 'Choose the correct option from the list:',
        'enter_answer': 'Enter your answer:',
        'select_placeholder': '-- Select an option --',
        'answer_placeholder': 'Your answer...',
        'btn_answer': 'Answer',
        'btn_flag': 'Flag for review',
        'btn_draft': 'Save draft',
        'btn_cancel': 'Cancel attempt',
        'my_subjects': 'My subjects',
        'tools': 'Tools',
        'gradebook_tool': '📊 Gradebook',
        'my_works': '📝 My works',
        'messages_tool': '🔔 Messages',
        'course_files': '📎 Course files',
        'footer_portal': 'Educational Information Portal © 2024',
        'privacy': 'Privacy Policy',
        'help': 'Help',
        'contacts': 'Contacts',
        'result_title': 'Test result',
        'result_nav': '📊 Test result',
        'test_completed': 'Testing completed',
        'your_result': 'Your result:',
        'completion_time': 'Completion time:',
        'answer_review': 'Review of answers:',
        'question_label': 'Question:',
        'your_answer': 'Your answer:',
        'correct_answer_label': 'Correct answer:',
        'take_again': 'Take again',
        'nothing_selected': '[nothing selected]',
        'hp_email': 'Confirmation email',
        'hp_website': 'Website',
        'hp_search': 'Search query',
        'hp_captcha': 'Captcha code',
        'hp_newsletter': 'Newsletter email',
        'hp_robot': 'I am not a robot',
        'hp_submit': 'Submit',
    }
}

# --- СПИСКИ ПРЕДМЕТОВ ---
SUBJECTS = {
    'ru': ['Математика', 'Украинский язык', 'История Украины', 'Физика',
           'Программирование', 'Информатика', 'Английский язык', 'Химия',
           'Биология', 'География', 'Экономика', 'Философия'],
    'uk': ['Математика', 'Українська мова', 'Історія України', 'Фізика',
           'Програмування', 'Інформатика', 'Англійська мова', 'Хімія',
           'Біологія', 'Географія', 'Економіка', 'Філософія'],
    'en': ['Mathematics', 'Ukrainian language', 'History of Ukraine', 'Physics',
           'Programming', 'Computer Science', 'English language', 'Chemistry',
           'Biology', 'Geography', 'Economics', 'Philosophy']
}

# ============================================================
#  БАНК ВОПРОСОВ (id одинаковые во всех языках)
# ============================================================
QUESTION_POOL = {
    'ru': [
        {"id": 1, "text": "Что выведет следующий код? print(type(1/2))", "type": "choice",
         "options": ["class 'int'", "class 'float'", "class 'double'", "Ошибка"], "correct": "class 'float'"},
        {"id": 2, "text": "Какой оператор в Python выполняет целочисленное деление?", "type": "choice",
         "options": ["/", "//", "%", "**"], "correct": "//"},
        {"id": 3, "text": "Какой тип данных в Python является неизменяемым (immutable)?", "type": "dropdown",
         "options": ["list", "dict", "set", "tuple", "bytearray"], "correct": "tuple"},
        {"id": 4, "text": "Какая функция используется для открытия файла в Python?", "type": "text",
         "correct": "open"},
        {"id": 5, "text": "Какой метод добавляет элемент в конец списка в Python?", "type": "choice",
         "options": ["add", "insert", "append", "push"], "correct": "append"},
        {"id": 6, "text": "Что выведет print(len(\"hello\"))?", "type": "choice",
         "options": ["4", "5", "6", "Ошибка"], "correct": "5"},
        {"id": 7, "text": "Что выведет print(bool([]))?", "type": "choice",
         "options": ["True", "False", "None", "Ошибка"], "correct": "False"},
        {"id": 8, "text": "Какая функция округляет число в Python?", "type": "text",
         "correct": "round"},
        {"id": 9, "text": "Что такое f-strings в Python?", "type": "choice",
         "options": ["Форматированные строки", "Файловые строки", "Функциональные строки", "Циклы"], "correct": "Форматированные строки"},
        {"id": 10, "text": "Что выведет print(2 ** 3)?", "type": "choice",
         "options": ["6", "8", "9", "5"], "correct": "8"},
        {"id": 11, "text": "Какова сложность алгоритма бинарного поиска (Big O)?", "type": "dropdown",
         "options": ["O(n)", "O(n log n)", "O(log n)", "O(1)", "O(n^2)"], "correct": "O(log n)"},
        {"id": 12, "text": "Какой принцип ООП позволяет скрывать внутреннюю реализацию объекта?", "type": "choice",
         "options": ["Наследование", "Полиморфизм", "Инкапсуляция", "Абстракция"], "correct": "Инкапсуляция"},
        {"id": 13, "text": "Что такое 'Deadlock' в многопоточности?", "type": "choice",
         "options": ["Ускорение работы", "Взаимная блокировка потоков", "Потеря данных", "Ошибка памяти"], "correct": "Взаимная блокировка потоков"},
        {"id": 14, "text": "Какая структура данных работает по принципу LIFO?", "type": "choice",
         "options": ["Очередь", "Стек", "Список", "Дерево"], "correct": "Стек"},
        {"id": 15, "text": "Что такое API?", "type": "choice",
         "options": ["Application Programming Interface", "Automatic Program Installer", "Advanced Python Interface", "Applied Programming Index"], "correct": "Application Programming Interface"},
        {"id": 16, "text": "Какие из перечисленных языков являются объектно-ориентированными?", "type": "multiple",
         "options": ["Python", "Java", "C", "C++", "Pascal"], "correct": ["Python", "Java", "C++"]},
        {"id": 17, "text": "Какие структуры данных относятся к линейным?", "type": "multiple",
         "options": ["Массив", "Стек", "Очередь", "Дерево", "Граф"], "correct": ["Массив", "Стек", "Очередь"]},
        {"id": 18, "text": "Какой метод HTTP используется для частичного обновления ресурса?", "type": "dropdown",
         "options": ["PUT", "POST", "PATCH", "GET", "DELETE"], "correct": "PATCH"},
        {"id": 19, "text": "Что означает аббревиатура SQL?", "type": "text",
         "correct": "Structured Query Language"},
        {"id": 20, "text": "Что такое JSON?", "type": "choice",
         "options": ["JavaScript Object Notation", "Java Standard Object Name", "Just Simple Output Node", "JavaScript Order Notation"], "correct": "JavaScript Object Notation"},
        {"id": 21, "text": "Какая библиотека Python используется для HTTP-запросов?", "type": "text",
         "correct": "requests"},
        {"id": 22, "text": "Какие из перечисленных методов HTTP являются идемпотентными?", "type": "multiple",
         "options": ["GET", "PUT", "POST", "DELETE", "PATCH"], "correct": ["GET", "PUT", "DELETE"]},
        {"id": 23, "text": "Что такое DNS?", "type": "choice",
         "options": ["Domain Name System", "Data Network Service", "Dynamic Node System", "Direct Naming Server"], "correct": "Domain Name System"},
        {"id": 24, "text": "Какие из перечисленных протоколов являются прикладного уровня (OSI)?", "type": "multiple",
         "options": ["HTTP", "FTP", "TCP", "SMTP", "IP"], "correct": ["HTTP", "FTP", "SMTP"]},
        {"id": 25, "text": "Какое уравнение описывает движение тела в вязкой среде при малых скоростях?", "type": "choice",
         "options": ["F = ma", "F = -kx", "F = -bv (сила Стокса)", "F = GmM/r²"], "correct": "F = -bv (сила Стокса)"},
        {"id": 26, "text": "Чему равна постоянная Планка (приближённо)?", "type": "dropdown",
         "options": ["6.626 × 10⁻³⁴ Дж·с", "3.14 × 10⁻³¹ Дж·с", "9.81 × 10⁻³⁴ Дж·с", "1.6 × 10⁻¹⁹ Дж·с", "8.31 × 10⁻³⁴ Дж·с"],
         "correct": "6.626 × 10⁻³⁴ Дж·с"},
        {"id": 27, "text": "Какие из перечисленных величин сохраняются при упругом столкновении двух тел?", "type": "multiple",
         "options": ["Импульс (количество движения)", "Кинетическая энергия", "Потенциальная энергия", "Температура", "Момент импульса"],
         "correct": ["Импульс (количество движения)", "Кинетическая энергия", "Момент импульса"]},
        {"id": 28, "text": "Какое явление описывает эффект Комптона?", "type": "choice",
         "options": ["Рассеяние рентгеновских лучей на свободных электронах с изменением длины волны",
                     "Испускание электронов при нагревании металла",
                     "Искривление света под действием гравитации",
                     "Изменение частоты света при движении источника"],
         "correct": "Рассеяние рентгеновских лучей на свободных электронах с изменением длины волны"},
        {"id": 29, "text": "Чему равно ускорение свободного падения на поверхности Земли (приближённо)?", "type": "text",
         "correct": "9.81"},
        {"id": 30, "text": "Какие из перечисленных частиц являются фермионами?", "type": "multiple",
         "options": ["Электрон", "Протон", "Фотон", "Нейтрон", "Бозон Хиггса"],
         "correct": ["Электрон", "Протон", "Нейтрон"]},
        {"id": 31, "text": "Что описывает уравнение Шрёдингера?", "type": "choice",
         "options": ["Движение планет вокруг Солнца", "Эволюцию квантовой системы во времени", "Тепловое движение молекул", "Электрическое поле точечного заряда"],
         "correct": "Эволюцию квантовой системы во времени"},
        {"id": 32, "text": "Какая формула описывает давление идеального газа?", "type": "dropdown",
         "options": ["P = nRT/V", "P = mgh", "P = F/S", "P = ρv²/2", "P = I²R"], "correct": "P = nRT/V"},
        {"id": 33, "text": "Какие из перечисленных законов относятся к законам сохранения?", "type": "multiple",
         "options": ["Закон сохранения энергии", "Закон сохранения импульса", "Закон сохранения массы", "Закон сохранения момента импульса", "Закон всемирного тяготения"],
         "correct": ["Закон сохранения энергии", "Закон сохранения импульса", "Закон сохранения момента импульса"]},
        {"id": 34, "text": "Чему равна скорость света в вакууме (приближённо)?", "type": "dropdown",
         "options": ["3 × 10⁸ м/с", "3 × 10⁶ м/с", "3 × 10¹⁰ м/с", "3 × 10⁵ м/с", "3 × 10⁹ м/с"], "correct": "3 × 10⁸ м/с"},
        {"id": 35, "text": "Какие из перечисленных явлений подтверждают волновую природу света?", "type": "multiple",
         "options": ["Интерференция", "Дифракция", "Поляризация", "Фотоэффект", "Эффект Комптона"],
         "correct": ["Интерференция", "Дифракция", "Поляризация"]},
        {"id": 36, "text": "Какая единица измерения сопротивления в системе SI?", "type": "text",
         "correct": "Ом"},
        {"id": 37, "text": "Что такое энтропия в термодинамике?", "type": "choice",
         "options": ["Мера беспорядка (неупорядоченности) системы", "Количество теплоты, переданной телу", "Внутренняя энергия системы", "Температура тела"],
         "correct": "Мера беспорядка (неупорядоченности) системы"},
        {"id": 38, "text": "Какие из перечисленных утверждений о фотоне являются правильными?", "type": "multiple",
         "options": ["Фотон не имеет массы покоя", "Фотон движется со скоростью света", "Фотон имеет электрический заряд", "Энергия фотона равна hν", "Фотон является фермионом"],
         "correct": ["Фотон не имеет массы покоя", "Фотон движется со скоростью света", "Энергия фотона равна hν"]},
        {"id": 39, "text": "Какое уравнение описывает закон Ома для полной цепи?", "type": "choice",
         "options": ["I = U/R", "I = ε/(R + r)", "U = IR", "P = UI"], "correct": "I = ε/(R + r)"},
        {"id": 40, "text": "Какие силы называются консервативными?", "type": "multiple",
         "options": ["Сила тяжести", "Сила упругости", "Сила трения", "Электростатическая сила", "Сила сопротивления воздуха"],
         "correct": ["Сила тяжести", "Сила упругости", "Электростатическая сила"]},
        {"id": 41, "text": "Искусство составления и рассказывания увлекательных историй", "type": "choice",
         "options": ["Сторителлинг", "режиссура", "писательство", "сказительство"], "correct": "Сторителлинг"},
        {"id": 42, "text": "Какой принцип SOLID отвечает за единственную ответственность класса?", "type": "choice",
         "options": ["Open/Closed", "Single Responsibility", "Liskov Substitution", "Interface Segregation"], "correct": "Single Responsibility"},
    ],
    'uk': [
        {"id": 1, "text": "Що виведе наступний код? print(type(1/2))", "type": "choice",
         "options": ["class 'int'", "class 'float'", "class 'double'", "Помилка"], "correct": "class 'float'"},
        {"id": 2, "text": "Який оператор у Python виконує цілочисельне ділення?", "type": "choice",
         "options": ["/", "//", "%", "**"], "correct": "//"},
        {"id": 3, "text": "Який тип даних у Python є незмінним (immutable)?", "type": "dropdown",
         "options": ["list", "dict", "set", "tuple", "bytearray"], "correct": "tuple"},
        {"id": 4, "text": "Яка функція використовується для відкриття файлу в Python?", "type": "text",
         "correct": "open"},
        {"id": 5, "text": "Який метод додає елемент у кінець списку в Python?", "type": "choice",
         "options": ["add", "insert", "append", "push"], "correct": "append"},
        {"id": 6, "text": "Що виведе print(len(\"hello\"))?", "type": "choice",
         "options": ["4", "5", "6", "Помилка"], "correct": "5"},
        {"id": 7, "text": "Що виведе print(bool([]))?", "type": "choice",
         "options": ["True", "False", "None", "Помилка"], "correct": "False"},
        {"id": 8, "text": "Яка функція округлює число в Python?", "type": "text",
         "correct": "round"},
        {"id": 9, "text": "Що таке f-strings у Python?", "type": "choice",
         "options": ["Форматовані рядки", "Файлові рядки", "Функціональні рядки", "Цикли"], "correct": "Форматовані рядки"},
        {"id": 10, "text": "Що виведе print(2 ** 3)?", "type": "choice",
         "options": ["6", "8", "9", "5"], "correct": "8"},
        {"id": 11, "text": "Яка складність алгоритму бінарного пошуку (Big O)?", "type": "dropdown",
         "options": ["O(n)", "O(n log n)", "O(log n)", "O(1)", "O(n^2)"], "correct": "O(log n)"},
        {"id": 12, "text": "Який принцип ООП дозволяє приховувати внутрішню реалізацію об'єкта?", "type": "choice",
         "options": ["Наслідування", "Поліморфізм", "Інкапсуляція", "Абстракція"], "correct": "Інкапсуляція"},
        {"id": 13, "text": "Що таке 'Deadlock' у багатопоточності?", "type": "choice",
         "options": ["Прискорення роботи", "Взаємне блокування потоків", "Втрата даних", "Помилка пам'яті"], "correct": "Взаємне блокування потоків"},
        {"id": 14, "text": "Яка структура даних працює за принципом LIFO?", "type": "choice",
         "options": ["Черга", "Стек", "Список", "Дерево"], "correct": "Стек"},
        {"id": 15, "text": "Що таке API?", "type": "choice",
         "options": ["Application Programming Interface", "Automatic Program Installer", "Advanced Python Interface", "Applied Programming Index"], "correct": "Application Programming Interface"},
        {"id": 16, "text": "Які з перелічених мов є об'єктно-орієнтованими?", "type": "multiple",
         "options": ["Python", "Java", "C", "C++", "Pascal"], "correct": ["Python", "Java", "C++"]},
        {"id": 17, "text": "Які структури даних відносяться до лінійних?", "type": "multiple",
         "options": ["Масив", "Стек", "Черга", "Дерево", "Граф"], "correct": ["Масив", "Стек", "Черга"]},
        {"id": 18, "text": "Який метод HTTP використовується для часткового оновлення ресурсу?", "type": "dropdown",
         "options": ["PUT", "POST", "PATCH", "GET", "DELETE"], "correct": "PATCH"},
        {"id": 19, "text": "Що означає абревіатура SQL?", "type": "text",
         "correct": "Structured Query Language"},
        {"id": 20, "text": "Що таке JSON?", "type": "choice",
         "options": ["JavaScript Object Notation", "Java Standard Object Name", "Just Simple Output Node", "JavaScript Order Notation"], "correct": "JavaScript Object Notation"},
        {"id": 21, "text": "Яка бібліотека Python використовується для HTTP-запитів?", "type": "text",
         "correct": "requests"},
        {"id": 22, "text": "Які з перелічених методів HTTP є ідемпотентними?", "type": "multiple",
         "options": ["GET", "PUT", "POST", "DELETE", "PATCH"], "correct": ["GET", "PUT", "DELETE"]},
        {"id": 23, "text": "Що таке DNS?", "type": "choice",
         "options": ["Domain Name System", "Data Network Service", "Dynamic Node System", "Direct Naming Server"], "correct": "Domain Name System"},
        {"id": 24, "text": "Які з перелічених протоколів є прикладного рівня (OSI)?", "type": "multiple",
         "options": ["HTTP", "FTP", "TCP", "SMTP", "IP"], "correct": ["HTTP", "FTP", "SMTP"]},
        {"id": 25, "text": "Яке рівняння описує рух тіла у в'язкому середовищі при малих швидкостях?", "type": "choice",
         "options": ["F = ma", "F = -kx", "F = -bv (сила Стокса)", "F = GmM/r²"], "correct": "F = -bv (сила Стокса)"},
        {"id": 26, "text": "Чому дорівнює постійна Планка (наближено)?", "type": "dropdown",
         "options": ["6.626 × 10⁻³⁴ Дж·с", "3.14 × 10⁻³¹ Дж·с", "9.81 × 10⁻³⁴ Дж·с", "1.6 × 10⁻¹⁹ Дж·с", "8.31 × 10⁻³⁴ Дж·с"],
         "correct": "6.626 × 10⁻³⁴ Дж·с"},
        {"id": 27, "text": "Які з перелічених величин зберігаються при пружному зіткненні двох тіл?", "type": "multiple",
         "options": ["Імпульс (кількість руху)", "Кінетична енергія", "Потенціальна енергія", "Температура", "Момент імпульсу"],
         "correct": ["Імпульс (кількість руху)", "Кінетична енергія", "Момент імпульсу"]},
        {"id": 28, "text": "Яке явище описує ефект Комптона?", "type": "choice",
         "options": ["Розсіювання рентгенівських променів на вільних електронах із зміною довжини хвилі",
                     "Випускання електронів при нагріванні металу",
                     "Викривлення світла під дією гравітації",
                     "Зміна частоти світла при русі джерела"],
         "correct": "Розсіювання рентгенівських променів на вільних електронах із зміною довжини хвилі"},
        {"id": 29, "text": "Чому дорівнює прискорення вільного падіння на поверхні Землі (наближено)?", "type": "text",
         "correct": "9.81"},
        {"id": 30, "text": "Які з перелічених частинок є ферміонами?", "type": "multiple",
         "options": ["Електрон", "Протон", "Фотон", "Нейтрон", "Бозон Хіггса"],
         "correct": ["Електрон", "Протон", "Нейтрон"]},
        {"id": 31, "text": "Що описує рівняння Шредінгера?", "type": "choice",
         "options": ["Рух планет навколо Сонця", "Еволюцію квантової системи у часі", "Тепловий рух молекул", "Електричне поле точкового заряду"],
         "correct": "Еволюцію квантової системи у часі"},
        {"id": 32, "text": "Яка формула описує тиск ідеального газу?", "type": "dropdown",
         "options": ["P = nRT/V", "P = mgh", "P = F/S", "P = ρv²/2", "P = I²R"], "correct": "P = nRT/V"},
        {"id": 33, "text": "Які з перелічених законів належать до законів збереження?", "type": "multiple",
         "options": ["Закон збереження енергії", "Закон збереження імпульсу", "Закон збереження маси", "Закон збереження моменту імпульсу", "Закон всесвітнього тяжіння"],
         "correct": ["Закон збереження енергії", "Закон збереження імпульсу", "Закон збереження моменту імпульсу"]},
        {"id": 34, "text": "Чому дорівнює швидкість світла у вакуумі (наближено)?", "type": "dropdown",
         "options": ["3 × 10⁸ м/с", "3 × 10⁶ м/с", "3 × 10¹⁰ м/с", "3 × 10⁵ м/с", "3 × 10⁹ м/с"], "correct": "3 × 10⁸ м/с"},
        {"id": 35, "text": "Які з перелічених явищ підтверджують хвильову природу світла?", "type": "multiple",
         "options": ["Інтерференція", "Дифракція", "Поляризація", "Фотоефект", "Ефект Комптона"],
         "correct": ["Інтерференція", "Дифракція", "Поляризація"]},
        {"id": 36, "text": "Яка одиниця вимірювання опору в системі SI?", "type": "text",
         "correct": "Ом"},
        {"id": 37, "text": "Що таке ентропія у термодинаміці?", "type": "choice",
         "options": ["Міра безладу (невпорядкованості) системи", "Кількість теплоти, переданої тілу", "Внутрішня енергія системи", "Температура тіла"],
         "correct": "Міра безладу (невпорядкованості) системи"},
        {"id": 38, "text": "Які з перелічених тверджень про фотон є правильними?", "type": "multiple",
         "options": ["Фотон не має маси спокою", "Фотон рухається зі швидкістю світла", "Фотон має електричний заряд", "Енергія фотона дорівнює hν", "Фотон є ферміоном"],
         "correct": ["Фотон не має маси спокою", "Фотон рухається зі швидкістю світла", "Енергія фотона дорівнює hν"]},
        {"id": 39, "text": "Яке рівняння описує закон Ома для повного кола?", "type": "choice",
         "options": ["I = U/R", "I = ε/(R + r)", "U = IR", "P = UI"], "correct": "I = ε/(R + r)"},
        {"id": 40, "text": "Які сили називаються консервативними?", "type": "multiple",
         "options": ["Сила тяжіння", "Сила пружності", "Сила тертя", "Електростатична сила", "Сила опору повітря"],
         "correct": ["Сила тяжіння", "Сила пружності", "Електростатична сила"]},
        {"id": 41, "text": "Мистецтво складання і розповідання захопливих історій", "type": "choice",
         "options": ["Сторітеллінг", "режисерство", "письменництво", "казкарство"], "correct": "Сторітеллінг"},
        {"id": 42, "text": "Який принцип SOLID відповідає за одну відповідальність класу?", "type": "choice",
         "options": ["Open/Closed", "Single Responsibility", "Liskov Substitution", "Interface Segregation"], "correct": "Single Responsibility"},
    ],
    'en': [
        {"id": 1, "text": "What will the following code output? print(type(1/2))", "type": "choice",
         "options": ["class 'int'", "class 'float'", "class 'double'", "Error"], "correct": "class 'float'"},
        {"id": 2, "text": "Which operator in Python performs integer division?", "type": "choice",
         "options": ["/", "//", "%", "**"], "correct": "//"},
        {"id": 3, "text": "Which data type in Python is immutable?", "type": "dropdown",
         "options": ["list", "dict", "set", "tuple", "bytearray"], "correct": "tuple"},
        {"id": 4, "text": "Which function is used to open a file in Python?", "type": "text",
         "correct": "open"},
        {"id": 5, "text": "Which method adds an element to the end of a list in Python?", "type": "choice",
         "options": ["add", "insert", "append", "push"], "correct": "append"},
        {"id": 6, "text": "What will print(len(\"hello\")) output?", "type": "choice",
         "options": ["4", "5", "6", "Error"], "correct": "5"},
        {"id": 7, "text": "What will print(bool([])) output?", "type": "choice",
         "options": ["True", "False", "None", "Error"], "correct": "False"},
        {"id": 8, "text": "Which function rounds a number in Python?", "type": "text",
         "correct": "round"},
        {"id": 9, "text": "What are f-strings in Python?", "type": "choice",
         "options": ["Formatted strings", "File strings", "Functional strings", "Loops"], "correct": "Formatted strings"},
        {"id": 10, "text": "What will print(2 ** 3) output?", "type": "choice",
         "options": ["6", "8", "9", "5"], "correct": "8"},
        {"id": 11, "text": "What is the complexity of binary search (Big O)?", "type": "dropdown",
         "options": ["O(n)", "O(n log n)", "O(log n)", "O(1)", "O(n^2)"], "correct": "O(log n)"},
        {"id": 12, "text": "Which OOP principle allows hiding the internal implementation of an object?", "type": "choice",
         "options": ["Inheritance", "Polymorphism", "Encapsulation", "Abstraction"], "correct": "Encapsulation"},
        {"id": 13, "text": "What is 'Deadlock' in multithreading?", "type": "choice",
         "options": ["Speedup", "Mutual blocking of threads", "Data loss", "Memory error"], "correct": "Mutual blocking of threads"},
        {"id": 14, "text": "Which data structure works on the LIFO principle?", "type": "choice",
         "options": ["Queue", "Stack", "List", "Tree"], "correct": "Stack"},
        {"id": 15, "text": "What is API?", "type": "choice",
         "options": ["Application Programming Interface", "Automatic Program Installer", "Advanced Python Interface", "Applied Programming Index"], "correct": "Application Programming Interface"},
        {"id": 16, "text": "Which of the listed languages are object-oriented?", "type": "multiple",
         "options": ["Python", "Java", "C", "C++", "Pascal"], "correct": ["Python", "Java", "C++"]},
        {"id": 17, "text": "Which data structures are linear?", "type": "multiple",
         "options": ["Array", "Stack", "Queue", "Tree", "Graph"], "correct": ["Array", "Stack", "Queue"]},
        {"id": 18, "text": "Which HTTP method is used for partial resource update?", "type": "dropdown",
         "options": ["PUT", "POST", "PATCH", "GET", "DELETE"], "correct": "PATCH"},
        {"id": 19, "text": "What does the abbreviation SQL stand for?", "type": "text",
         "correct": "Structured Query Language"},
        {"id": 20, "text": "What is JSON?", "type": "choice",
         "options": ["JavaScript Object Notation", "Java Standard Object Name", "Just Simple Output Node", "JavaScript Order Notation"], "correct": "JavaScript Object Notation"},
        {"id": 21, "text": "Which Python library is used for HTTP requests?", "type": "text",
         "correct": "requests"},
        {"id": 22, "text": "Which of the listed HTTP methods are idempotent?", "type": "multiple",
         "options": ["GET", "PUT", "POST", "DELETE", "PATCH"], "correct": ["GET", "PUT", "DELETE"]},
        {"id": 23, "text": "What is DNS?", "type": "choice",
         "options": ["Domain Name System", "Data Network Service", "Dynamic Node System", "Direct Naming Server"], "correct": "Domain Name System"},
        {"id": 24, "text": "Which of the listed protocols are application-layer (OSI)?", "type": "multiple",
         "options": ["HTTP", "FTP", "TCP", "SMTP", "IP"], "correct": ["HTTP", "FTP", "SMTP"]},
        {"id": 25, "text": "Which equation describes the motion of a body in a viscous medium at low velocities?", "type": "choice",
         "options": ["F = ma", "F = -kx", "F = -bv (Stokes force)", "F = GmM/r²"], "correct": "F = -bv (Stokes force)"},
        {"id": 26, "text": "What is Planck's constant (approximately)?", "type": "dropdown",
         "options": ["6.626 × 10⁻³⁴ J·s", "3.14 × 10⁻³¹ J·s", "9.81 × 10⁻³⁴ J·s", "1.6 × 10⁻¹⁹ J·s", "8.31 × 10⁻³⁴ J·s"],
         "correct": "6.626 × 10⁻³⁴ J·s"},
        {"id": 27, "text": "Which of the listed quantities are conserved in an elastic collision of two bodies?", "type": "multiple",
         "options": ["Momentum (quantity of motion)", "Kinetic energy", "Potential energy", "Temperature", "Angular momentum"],
         "correct": ["Momentum (quantity of motion)", "Kinetic energy", "Angular momentum"]},
        {"id": 28, "text": "Which phenomenon does the Compton effect describe?", "type": "choice",
         "options": ["Scattering of X-rays by free electrons with a change in wavelength",
                     "Emission of electrons when heating a metal",
                     "Bending of light under the action of gravity",
                     "Change in light frequency when the source moves"],
         "correct": "Scattering of X-rays by free electrons with a change in wavelength"},
        {"id": 29, "text": "What is the acceleration due to gravity on Earth's surface (approximately)?", "type": "text",
         "correct": "9.81"},
        {"id": 30, "text": "Which of the listed particles are fermions?", "type": "multiple",
         "options": ["Electron", "Proton", "Photon", "Neutron", "Higgs boson"],
         "correct": ["Electron", "Proton", "Neutron"]},
        {"id": 31, "text": "What does the Schrödinger equation describe?", "type": "choice",
         "options": ["Motion of planets around the Sun", "Evolution of a quantum system in time", "Thermal motion of molecules", "Electric field of a point charge"],
         "correct": "Evolution of a quantum system in time"},
        {"id": 32, "text": "Which formula describes the pressure of an ideal gas?", "type": "dropdown",
         "options": ["P = nRT/V", "P = mgh", "P = F/S", "P = ρv²/2", "P = I²R"], "correct": "P = nRT/V"},
        {"id": 33, "text": "Which of the listed laws are conservation laws?", "type": "multiple",
         "options": ["Law of conservation of energy", "Law of conservation of momentum", "Law of conservation of mass", "Law of conservation of angular momentum", "Law of universal gravitation"],
         "correct": ["Law of conservation of energy", "Law of conservation of momentum", "Law of conservation of angular momentum"]},
        {"id": 34, "text": "What is the speed of light in vacuum (approximately)?", "type": "dropdown",
         "options": ["3 × 10⁸ m/s", "3 × 10⁶ m/s", "3 × 10¹⁰ m/s", "3 × 10⁵ m/s", "3 × 10⁹ m/s"], "correct": "3 × 10⁸ m/s"},
        {"id": 35, "text": "Which of the listed phenomena confirm the wave nature of light?", "type": "multiple",
         "options": ["Interference", "Diffraction", "Polarization", "Photoelectric effect", "Compton effect"],
         "correct": ["Interference", "Diffraction", "Polarization"]},
        {"id": 36, "text": "What is the SI unit of resistance?", "type": "text",
         "correct": "Ohm"},
        {"id": 37, "text": "What is entropy in thermodynamics?", "type": "choice",
         "options": ["Measure of disorder (disorganization) of a system", "Amount of heat transferred to a body", "Internal energy of a system", "Body temperature"],
         "correct": "Measure of disorder (disorganization) of a system"},
        {"id": 38, "text": "Which of the listed statements about the photon are correct?", "type": "multiple",
         "options": ["Photon has no rest mass", "Photon moves at the speed of light", "Photon has electric charge", "Photon energy equals hν", "Photon is a fermion"],
         "correct": ["Photon has no rest mass", "Photon moves at the speed of light", "Photon energy equals hν"]},
        {"id": 39, "text": "Which equation describes Ohm's law for a complete circuit?", "type": "choice",
         "options": ["I = U/R", "I = ε/(R + r)", "U = IR", "P = UI"], "correct": "I = ε/(R + r)"},
        {"id": 40, "text": "Which forces are called conservative?", "type": "multiple",
         "options": ["Gravity", "Elastic force", "Friction", "Electrostatic force", "Air resistance"],
         "correct": ["Gravity", "Elastic force", "Electrostatic force"]},
        {"id": 41, "text": "The art of creating and telling engaging stories", "type": "choice",
         "options": ["Storytelling", "directing", "writing", "fairy-tale telling"], "correct": "Storytelling"},
        {"id": 42, "text": "Which SOLID principle is responsible for a single responsibility of a class?", "type": "choice",
         "options": ["Open/Closed", "Single Responsibility", "Liskov Substitution", "Interface Segregation"], "correct": "Single Responsibility"},
    ]
}

HONEYPOT_FIELDS = ['user_email_confirm', 'website_url', 'search_query', 'captcha_code', 'newsletter_email']
QUESTIONS_PER_TEST = 10

# --- ШАБЛОН ТЕСТА ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>{{ t.result_title if false else t.site_brand }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; }
        .top-navbar { background-color: #0f6cbf; color: white; padding: 0; }
        .top-navbar .brand { padding: 12px 20px; font-weight: 600; font-size: 1.1em; color: white; text-decoration: none; display: inline-block; }
        .top-navbar .menu-btn { color: white; padding: 12px 18px; text-decoration: none; display: inline-block; font-size: 0.95em; border: none; background: transparent; cursor: pointer; }
        .top-navbar .menu-btn:hover { background-color: #0d5aa7; color: white; }
        .lang-btn { color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 0.85em; border: 1px solid rgba(255,255,255,0.35); margin-left: 4px; display: inline-block; }
        .lang-btn:hover { background: rgba(255,255,255,0.2); color: white; }
        .lang-btn.active { background: white; color: #0f6cbf; font-weight: 700; border-color: white; }
        .sub-navbar { background-color: #ffffff; border-bottom: 1px solid #dee2e6; padding: 8px 0; }
        .sub-navbar .nav-link-moodle { color: #0f6cbf; text-decoration: none; padding: 6px 14px; font-size: 0.9em; border-radius: 4px; }
        .sub-navbar .nav-link-moodle:hover { background-color: #eaf3fc; }
        .container-main { max-width: 1300px; margin: 20px auto; padding: 0 15px; }
        .breadcrumbs { font-size: 0.85em; color: #6c757d; margin-bottom: 15px; }
        .breadcrumbs a { color: #0f6cbf; text-decoration: none; }
        .sidebar-left { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 18px; }
        .sidebar-left h6 { font-size: 0.85em; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
        .quiz-info-block { margin-bottom: 15px; }
        .quiz-info-block strong { color: #0f5132; }
        .progress-bar-moodle { height: 8px; background-color: #e9ecef; border-radius: 4px; margin-top: 8px; overflow: hidden; }
        .progress-bar-moodle .progress-fill { height: 100%; background-color: #0f6cbf; border-radius: 4px; transition: width 0.3s; }
        .timer-block { background: #eaf3fc; border: 1px solid #cfe2ff; border-radius: 4px; padding: 10px; text-align: center; font-size: 1.1em; color: #0f6cbf; font-weight: 600; margin-top: 12px; }
        .sidebar-right { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 18px; }
        .sidebar-right h6 { font-size: 0.85em; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
        .subject-btn { display: block; width: 100%; text-align: left; padding: 8px 12px; margin-bottom: 6px; border: 1px solid #dee2e6; background: #f8f9fa; color: #495057; border-radius: 4px; font-size: 0.9em; cursor: pointer; transition: all 0.15s; }
        .subject-btn:hover { background: #eaf3fc; border-color: #0f6cbf; color: #0f6cbf; }
        .subject-btn:active { background: #0f6cbf; color: white; }
        .question-card { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 28px; }
        .question-title { font-size: 1.15em; font-weight: 500; color: #212529; margin-bottom: 22px; line-height: 1.5; }
        .question-title::before { content: attr(data-prefix) attr(data-num) "  "; color: #0f6cbf; font-weight: 700; }
        .answer-option { display: flex; align-items: center; margin-bottom: 10px; padding: 10px 12px; border-radius: 4px; border: 1px solid transparent; transition: background 0.15s, border 0.15s; }
        .answer-option:hover { background-color: #eaf3fc; border-color: #cfe2ff; }
        .answer-option input[type="radio"], .answer-option input[type="checkbox"] { margin-right: 12px; transform: scale(1.2); cursor: pointer; }
        .answer-label { cursor: pointer; font-size: 1em; margin: 0; }
        .text-answer-input, .dropdown-select { width: 100%; padding: 12px; border: 1px solid #ced4da; border-radius: 4px; font-size: 1em; }
        .dropdown-select:focus, .text-answer-input:focus { outline: none; border-color: #0f6cbf; box-shadow: 0 0 0 3px rgba(15,108,191,0.15); }
        .btn-moodle { background-color: #0f6cbf; color: white; border: none; padding: 10px 28px; font-size: 1em; border-radius: 4px; }
        .btn-moodle:hover { background-color: #0d5aa7; color: white; }
        .btn-outline-moodle { background: white; color: #0f6cbf; border: 1px solid #0f6cbf; padding: 8px 20px; border-radius: 4px; }
        .btn-outline-moodle:hover { background-color: #0f6cbf; color: white; }
        .honeypot-trap { position: absolute !important; left: -9999px !important; top: -9999px !important; width: 1px !important; height: 1px !important; opacity: 0 !important; pointer-events: none !important; }
        .honeypot-decoy { visibility: hidden !important; height: 0 !important; overflow: hidden !important; position: absolute !important; }
        .footer-moodle { text-align: center; color: #6c757d; font-size: 0.85em; padding: 20px; margin-top: 20px; border-top: 1px solid #dee2e6; }
        .footer-moodle a { color: #0f6cbf; text-decoration: none; }
        .multi-hint { background: #fff3cd; border-left: 3px solid #ffc107; padding: 8px 12px; border-radius: 4px; font-size: 0.9em; color: #856404; margin-bottom: 12px; }
    </style>
</head>
<body>

    <div class="top-navbar">
        <div class="container-main" style="display: flex; align-items: center; justify-content: space-between; padding: 0 15px; flex-wrap: wrap; gap: 6px;">
            <div>
                <a href="/" class="brand">{{ t.site_brand }}</a>
            </div>
            <div style="display: flex; align-items: center;">
                <button class="menu-btn" onclick="return false;">{{ t.menu_courses }}</button>
                <button class="menu-btn" onclick="return false;">{{ t.menu_calendar }}</button>
                <button class="menu-btn" onclick="return false;">{{ t.menu_profile }}</button>
                <button class="menu-btn" onclick="return false;">{{ t.menu_settings }}</button>
                <button class="menu-btn" onclick="return false;">{{ t.menu_help }}</button>
                <span style="margin: 0 8px; color: rgba(255,255,255,0.4);">|</span>
                <a href="/lang/ru" class="lang-btn {% if lang == 'ru' %}active{% endif %}">RU</a>
                <a href="/lang/uk" class="lang-btn {% if lang == 'uk' %}active{% endif %}">UK</a>
                <a href="/lang/en" class="lang-btn {% if lang == 'en' %}active{% endif %}">EN</a>
            </div>
        </div>
    </div>

    <div class="sub-navbar">
        <div class="container-main" style="padding: 0 15px;">
            <a href="/" class="nav-link-moodle" onclick="return false;">{{ t.nav_home }}</a>
            <a href="/" class="nav-link-moodle" onclick="return false;">{{ t.nav_disciplines }}</a>
            <a href="/" class="nav-link-moodle" onclick="return false;">{{ t.nav_testing }}</a>
            <a href="/" class="nav-link-moodle" onclick="return false;">{{ t.nav_gradebook }}</a>
            <a href="/" class="nav-link-moodle" onclick="return false;">{{ t.nav_messages }}</a>
        </div>
    </div>

    <div class="container-main">
        <div class="breadcrumbs">
            <a href="/" onclick="return false;">{{ t.breadcrumb_home }}</a> /
            <a href="/" onclick="return false;">{{ t.breadcrumb_programming }}</a> /
            <span>{{ t.breadcrumb_final_test }}</span>
        </div>

        <div class="row g-3">
            <div class="col-lg-3 col-md-4">
                <div class="sidebar-left">
                    <h6>{{ t.test_navigation }}</h6>
                    <div class="quiz-info-block">
                        <strong>{{ t.question_x_of_y.format(q=q_num, total=total) }}</strong>
                        <div class="progress-bar-moodle">
                            <div class="progress-fill" style="width: {{ (q_num / total) * 100 }}%"></div>
                        </div>
                    </div>
                    <div class="timer-block" id="timer">⏱ 00:00</div>
                    <hr>
                    <div style="font-size: 0.85em; color: #6c757d; line-height: 1.6;">
                        <div>{{ t.duration }} <strong>{{ t.duration_value }}</strong></div>
                        <div>{{ t.attempt }} <strong>{{ t.attempt_value }}</strong></div>
                        <div>{{ t.grading_method }} <strong>{{ t.grading_value }}</strong></div>
                    </div>
                    <hr>
                    <a href="/reset" style="text-decoration: none; color: #dc3545; font-size: 0.9em;">{{ t.start_over }}</a>
                </div>
            </div>

            <div class="col-lg-6 col-md-8">
                <form method="POST" action="/" id="answerForm">
                    <div class="question-card">
                        <div class="question-title" data-num="{{ q_num }}" data-prefix="{{ t.question_prefix }}">{{ q_text|safe }}</div>

                        {% if q_type == 'choice' %}
                            <p style="color: #6c757d; font-size: 0.9em;">{{ t.select_one }}</p>
                            {% for opt in options %}
                            <div class="answer-option">
                                <input type="radio" name="answer" id="opt{{ loop.index }}" value="{{ opt }}" required>
                                <label class="answer-label" for="opt{{ loop.index }}">{{ opt|safe }}</label>
                            </div>
                            {% endfor %}

                        {% elif q_type == 'multiple' %}
                            <div class="multi-hint">{{ t.multiple_hint }}</div>
                            {% for opt in options %}
                            <div class="answer-option">
                                <input type="checkbox" name="answer" id="opt{{ loop.index }}" value="{{ opt }}">
                                <label class="answer-label" for="opt{{ loop.index }}">{{ opt|safe }}</label>
                            </div>
                            {% endfor %}

                        {% elif q_type == 'dropdown' %}
                            <p style="color: #6c757d; font-size: 0.9em;">{{ t.select_from_list }}</p>
                            <select name="answer" class="dropdown-select" required>
                                <option value="" disabled selected>{{ t.select_placeholder }}</option>
                                {% for opt in options %}
                                    <option value="{{ opt }}">{{ opt }}</option>
                                {% endfor %}
                            </select>

                        {% elif q_type == 'text' %}
                            <p style="color: #6c757d; font-size: 0.9em;">{{ t.enter_answer }}</p>
                            <input type="text" name="answer" class="text-answer-input"
                                   placeholder="{{ t.answer_placeholder }}" required autocomplete="off">
                        {% endif %}

                        <!-- HONEYPOT -->
                        <div class="honeypot-trap" aria-hidden="true">
                            <label>{{ t.hp_email }}</label>
                            <input type="text" name="user_email_confirm" tabindex="-1" autocomplete="off">
                            <label>{{ t.hp_website }}</label>
                            <input type="text" name="website_url" tabindex="-1" autocomplete="off">
                            <label>{{ t.hp_search }}</label>
                            <input type="text" name="search_query" tabindex="-1" autocomplete="off">
                            <label>{{ t.hp_captcha }}</label>
                            <input type="text" name="captcha_code" tabindex="-1" autocomplete="off">
                            <label>{{ t.hp_newsletter }}</label>
                            <input type="text" name="newsletter_email" tabindex="-1" autocomplete="off">
                        </div>
                        <div class="honeypot-trap" aria-hidden="true">
                            <label>
                                <input type="checkbox" name="robot_check" tabindex="-1" value="1">
                                {{ t.hp_robot }}
                            </label>
                        </div>
                        <div class="honeypot-decoy" aria-hidden="true">
                            <input type="radio" name="answer_decoy" value="trap_option_1">
                            <input type="radio" name="answer_decoy" value="trap_option_2">
                        </div>
                        <button type="submit" name="admin_submit" value="1" class="honeypot-trap" tabindex="-1">{{ t.hp_submit }}</button>
                    </div>

                    <div style="margin-top: 20px;">
                        <button type="submit" class="btn btn-moodle">{{ t.btn_answer }}</button>
                        <button type="button" class="btn btn-outline-moodle ms-2" onclick="return false;">{{ t.btn_flag }}</button>
                        <button type="button" class="btn btn-outline-moodle ms-2" onclick="return false;">{{ t.btn_draft }}</button>
                    </div>
                </form>

                <div style="margin-top: 15px;">
                    <a href="/reset" class="btn btn-outline-secondary btn-sm">{{ t.btn_cancel }}</a>
                </div>
            </div>

            <div class="col-lg-3 d-none d-lg-block">
                <div class="sidebar-right">
                    <h6>{{ t.my_subjects }}</h6>
                    {% for subject in subjects %}
                        <button class="subject-btn" onclick="return false;">📘 {{ subject }}</button>
                    {% endfor %}
                    <hr>
                    <h6>{{ t.tools }}</h6>
                    <button class="subject-btn" onclick="return false;">{{ t.gradebook_tool }}</button>
                    <button class="subject-btn" onclick="return false;">{{ t.my_works }}</button>
                    <button class="subject-btn" onclick="return false;">{{ t.messages_tool }}</button>
                    <button class="subject-btn" onclick="return false;">{{ t.course_files }}</button>
                </div>
            </div>
        </div>

        <div class="footer-moodle">
            {{ t.footer_portal }} |
            <a href="/" onclick="return false;">{{ t.privacy }}</a> |
            <a href="/" onclick="return false;">{{ t.help }}</a> |
            <a href="/" onclick="return false;">{{ t.contacts }}</a>
        </div>
    </div>

    <script>
        let seconds = 0;
        function updateTimer() {
            seconds++;
            let m = Math.floor(seconds / 60);
            let s = seconds % 60;
            document.getElementById('timer').innerText = `⏱ ${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
        }
        setInterval(updateTimer, 1000);

        document.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text' && !e.target.closest('.honeypot-trap')) {
                e.preventDefault();
                document.getElementById('answerForm').submit();
            }
        });
    </script>
</body>
</html>
"""

# --- ШАБЛОН РЕЗУЛЬТАТОВ ---
RESULT_LAYOUT = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t.result_title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .top-navbar { background-color: #0f6cbf; color: white; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
        .lang-btn { color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 0.85em; border: 1px solid rgba(255,255,255,0.35); margin-left: 4px; display: inline-block; }
        .lang-btn:hover { background: rgba(255,255,255,0.2); color: white; }
        .lang-btn.active { background: white; color: #0f6cbf; font-weight: 700; border-color: white; }
        .result-container { max-width: 800px; margin: 40px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .score { font-size: 3.5em; font-weight: bold; color: #0f6cbf; text-align: center; }
        .time { font-size: 1.2em; color: #6c757d; margin-top: 10px; text-align: center; }
        .review-item { margin-bottom: 15px; padding: 15px; border-radius: 5px; }
        .review-correct { background-color: #d1e7dd; border-left: 5px solid #198754; }
        .review-wrong { background-color: #f8d7da; border-left: 5px solid #dc3545; }
        .btn-moodle { background-color: #0f6cbf; color: white; border: none; padding: 12px 40px; font-size: 1.1em; border-radius: 5px; text-decoration: none; display: inline-block; }
        .btn-moodle:hover { background-color: #0d5aa7; color: white; }
    </style>
</head>
<body>
    <div class="top-navbar">
        <strong>{{ t.site_brand }}</strong>
        <div style="display: flex; align-items: center;">
            <span style="margin-right: 10px;">{{ t.result_nav }}</span>
            <a href="/lang/ru" class="lang-btn {% if lang == 'ru' %}active{% endif %}">RU</a>
            <a href="/lang/uk" class="lang-btn {% if lang == 'uk' %}active{% endif %}">UK</a>
            <a href="/lang/en" class="lang-btn {% if lang == 'en' %}active{% endif %}">EN</a>
        </div>
    </div>

    <div class="result-container">
        <h1 style="text-align: center;">{{ t.test_completed }}</h1>
        <p class="mt-4" style="text-align: center; color: #6c757d;">{{ t.your_result }}</p>
        <div class="score">{{ score }} / {{ total }}</div>
        <p class="time">{{ t.completion_time }} {{ time_str }}</p>

        <div style="margin-top: 30px;">
            <h4>{{ t.answer_review }}</h4>
            {% for ans in user_answers %}
                <div class="review-item {% if ans.is_correct %}review-correct{% else %}review-wrong{% endif %}">
                    <strong>{{ t.question_label }}</strong> {{ ans.question_text|safe }}<br>
                    <strong>{{ t.your_answer }}</strong> {{ ans.user_answer|safe }}<br>
                    {% if not ans.is_correct %}
                        <strong>{{ t.correct_answer_label }}</strong> {{ ans.correct_answer|safe }}
                    {% endif %}
                </div>
            {% endfor %}
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <a href="/reset" class="btn-moodle">{{ t.take_again }}</a>
        </div>
    </div>
</body>
</html>
"""

# --- ПРОВЕРКА ЛОВУШЕК ---
def check_honeypot():
    for field in HONEYPOT_FIELDS:
        if request.form.get(field, '').strip():
            return True
    if request.form.get('robot_check'):
        return True
    if request.form.get('admin_submit'):
        return True
    return False

def format_correct(c):
    if isinstance(c, list):
        return ", ".join(c)
    return str(c)

# --- ОБРАБОТЧИКИ ОШИБОК ---
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('index'))

@app.errorhandler(500)
def server_error(e):
    return redirect(url_for('index'))

@app.errorhandler(Exception)
def handle_exception(e):
    return redirect(url_for('index'))

# --- ПЕРЕКЛЮЧАТЕЛЬ ЯЗЫКА ---
@app.route('/lang/<code>')
def set_lang(code):
    if code in LANGUAGES:
        session['lang'] = code
    return redirect(url_for('index'))

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---
@app.route('/', methods=['GET', 'POST'])
def index():
    lang = session.get('lang', DEFAULT_LANG)
    if lang not in LANGUAGES:
        lang = DEFAULT_LANG
    t = UI[lang]

    # Инициализация сессии
    if 'test_question_ids' not in session or 'start_time' not in session:
        all_ids = [q['id'] for q in QUESTION_POOL[lang]]
        selected_ids = random.sample(all_ids, QUESTIONS_PER_TEST)
        session['test_question_ids'] = selected_ids
        session['q_index'] = 0
        session['score'] = 0
        session['start_time'] = time.time()
        session['user_answers'] = []

    q_index = session['q_index']
    test_ids = session.get('test_question_ids', [])

    # Конец теста
    if q_index >= len(test_ids):
        end_time = time.time()
        start_time = session.get('start_time', end_time)
        total_time = int(end_time - start_time)
        m = total_time // 60
        s = total_time % 60
        time_str = f"{m:02d}:{s:02d}"

        id_to_q = {q['id']: q for q in QUESTION_POOL[lang]}
        user_answers_display = []
        for ans in session.get('user_answers', []):
            q = id_to_q.get(ans['question_id'])
            if not q:
                continue
            user_answers_display.append({
                'question_text': q['text'],
                'user_answer': ans['user_answer'],
                'correct_answer': format_correct(q['correct']),
                'is_correct': ans['is_correct']
            })

        return render_template_string(RESULT_LAYOUT, t=t, lang=lang,
                                      score=session.get('score', 0),
                                      total=len(test_ids),
                                      time_str=time_str,
                                      user_answers=user_answers_display)

    current_q_id = test_ids[q_index]
    current_q = next((q for q in QUESTION_POOL[lang] if q['id'] == current_q_id), None)
    if current_q is None:
        session.clear()
        return redirect(url_for('index'))

    # Обработка ответа
    if request.method == 'POST':
        is_bot = check_honeypot()
        correct_answer = current_q['correct']

        if current_q['type'] == 'multiple':
            user_answers_list = request.form.getlist('answer')
            if isinstance(correct_answer, list):
                is_correct = set(user_answers_list) == set(correct_answer)
            else:
                is_correct = False
            user_answer_display = ", ".join(user_answers_list) if user_answers_list else t['nothing_selected']
            if is_bot:
                is_correct = False
            new_answers = list(session.get('user_answers', []))
            new_answers.append({
                'question_id': current_q_id,
                'user_answer': user_answer_display,
                'is_correct': is_correct
            })
            session['user_answers'] = new_answers
            if is_correct:
                session['score'] = session.get('score', 0) + 1
            session['q_index'] = q_index + 1
        else:
            user_answer = request.form.get('answer')
            if user_answer is not None:
                if current_q['type'] == 'text':
                    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
                else:
                    is_correct = user_answer == correct_answer
                if is_bot:
                    is_correct = False
                new_answers = list(session.get('user_answers', []))
                new_answers.append({
                    'question_id': current_q_id,
                    'user_answer': user_answer,
                    'is_correct': is_correct
                })
                session['user_answers'] = new_answers
                if is_correct:
                    session['score'] = session.get('score', 0) + 1
                session['q_index'] = q_index + 1
        return redirect(url_for('index'))

    # GET — показ вопроса
    options = current_q.get('options', [])
    if current_q['type'] in ('choice', 'dropdown', 'multiple') and options:
        options = list(options)
        random.shuffle(options)

    return render_template_string(HTML_LAYOUT,
                                  t=t, lang=lang,
                                  q_num=q_index + 1,
                                  total=len(test_ids),
                                  q_text=current_q['text'],
                                  q_type=current_q['type'],
                                  options=options,
                                  subjects=SUBJECTS[lang])

@app.route('/reset')
def reset():
    lang = session.get('lang', DEFAULT_LANG)
    session.clear()
    session['lang'] = lang
    return redirect(url_for('index'))

# --- ОТКРЫТИЕ БРАУЗЕРА ---
def open_browser():
    try:
        webbrowser.open('http://127.0.0.1:8080')
    except Exception:
        pass

if __name__ == '__main__':
    print("=" * 55)
    print("   САЙТ ЗАПУЩЕН! ОТКРОЙТЕ БРАУЗЕР ПО АДРЕСУ:")
    print("   http://127.0.0.1:8080")
    print("=" * 55)
    print()
    print("   ЯЗЫКИ: RU (по умолчанию) | UK | EN")
    print("   БАНК ВОПРОСОВ: 42 шт. на каждом языке")
    print("   В КАЖДОМ ТЕСТЕ: 10 случайных")
    print("   ТИПЫ: choice | multiple | dropdown | text")
    print()
    print("=" * 55)

    threading.Timer(1.5, open_browser).start()

    try:
        app.run(debug=False, use_reloader=False, port=8080)
    except Exception:
        pass