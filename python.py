import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import datetime
import pytz

# Объявление классов состояний
class TestStates(StatesGroup):
    answer = State()

class NotificationStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_time = State()

API_TOKEN = '8561470854:AAFXm5WTdAMuL-ZIpID0_LjTLSz2VLfN0eU'

# Создаем хранилище FSM
storage = MemoryStorage()

# Создаем бота и диспетчера с хранилищем
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Хранилище настроек уведомлений и времени
user_notifications = {}  # user_id: {'enabled': bool, 'days': list of int, 'time': 'HH:MM'}
# Хранилище для отслеживания отправленных уведомлений
last_sent = {}  # user_id: date (YYYY-MM-DD)

# Обработка команды /start
@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    await message.answer(
        "Привет! Я EngllishBoost! — помощник в улучшении английского.\n"
        "Выберите навык:\n"
        "Используйте кнопку ниже для настройки уведомлений.",
        reply_markup=main_menu_kb()
    )

def main_menu_kb():
    # Основная клавиатура с кнопками
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Письменная речь", "Устная речь")
    keyboard.add("Понимание текста", "Понимание аудио")
    # Добавляем кнопку "Уведомления"
    keyboard.add("Уведомления")
    return keyboard

# Обработка выбора навыка
@dp.message_handler(lambda message: message.text in ["Письменная речь", "Устная речь", "Понимание текста", "Понимание аудио"])
async def handle_skill_choice(message: types.Message, state: FSMContext):
    skill = message.text
    await state.update_data(skill=skill)
    # Клавиатура с "Начать тест" и "Назад"
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Начать тест")
    keyboard.add("Назад")
    await message.answer(f"Вы выбрали навык: {skill}. Что хотите сделать?", reply_markup=keyboard)

# Обработка кнопки "Начать тест"
@dp.message_handler(lambda message: message.text == "Начать тест")
async def start_skill_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'skill' not in data:
        await message.answer("Пожалуйста, выберите навык сначала.", reply_markup=main_menu_kb())
        return
    questions = get_questions_for_skill(data['skill'])
    await state.update_data(questions=questions, current_q=0, score=0)
    await ask_question(message, state)

# Обработка кнопки "Назад" — возвращает в главное меню
@dp.message_handler(lambda message: message.text == "Назад")
async def back_to_main_menu(message: types.Message):
    await message.answer("Возвращаюсь в главное меню.", reply_markup=main_menu_kb())

@dp.message_handler(commands=['test'])
async def start_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'skill' not in data:
        await message.answer("Пожалуйста, выберите навык перед началом теста.")
        return
    questions = get_questions_for_skill(data['skill'])
    await state.update_data(questions=questions, current_q=0, score=0)
    await ask_question(message, state)

async def ask_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    questions = data['questions']
    q_idx = data['current_q']
    if q_idx >= len(questions):
        await finish_test(message, state)
        return
    question = questions[q_idx]
    buttons = [types.KeyboardButton(text=opt) for opt in question['buttons']]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*buttons)
    await message.answer(question['text'], reply_markup=keyboard)
    await TestStates.answer.set()

@dp.message_handler(state=TestStates.answer)
async def handle_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_idx = data['current_q']
    question = data['questions'][q_idx]
    selected = message.text
    if selected == question['correct']:
        data['score'] += 1
    data['current_q'] += 1
    await state.update_data(current_q=data['current_q'], score=data['score'])
    await ask_question(message, state)

async def finish_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data['score']
    total = len(data['questions'])
    result_text = f"Ваш результат: {score} из {total}.\n{interpret_score(score, total)}"
    await message.answer(result_text)
    try:
        with open('guide.pdf', 'rb') as file:
            await bot.send_document(chat_id=message.chat.id, document=file)
    except FileNotFoundError:
        await message.answer("Файл guide.pdf не найден.")
    # После завершения теста — возвращаем в главное меню
    await message.answer("Возвращаю вас в главное меню.", reply_markup=main_menu_kb())
    await state.finish()

def get_questions_for_skill(skill):
    # Обновленные вопросы с 6 вопросами по 4 варианта
    if skill == "Письменная речь":
        return [
            {'text': 'Выберите правильный вариант для фразы "I ____ to the store."', 'buttons': ['go', 'went', 'gone', 'am going'], 'correct': 'go'},
            {'text': 'Выберите правильное окончание слова "Happiness"', 'buttons': ['-несс', '-фул', '-ли', '-ность'], 'correct': '-несс'},
            {'text': 'Что означает "to improve"?', 'buttons': ['улучшать', 'плохо', 'играть', 'бежать'], 'correct': 'улучшать'},
            {'text': 'Выберите правильный перевод "Друзья"', 'buttons': ['friends', 'friend', 'friendly', 'friended'], 'correct': 'friends'},
            {'text': 'Что значит "to spend"?', 'buttons': ['тратить', 'зарабатывать', 'учиться', 'спать'], 'correct': 'тратить'},
            {'text': 'Выберите правильный вариант: "She ____ a book."', 'buttons': ['reads', 'readed', 'reading', 'to read'], 'correct': 'reads'},
        ]
    elif skill == "Устная речь":
        return [
            {'text': 'Как произнести "Hello" по-английски?', 'buttons': ['Хеллоу', 'Хелли', 'Хелло', 'Хелоу'], 'correct': 'Хеллоу'},
            {'text': 'Что значит "Good morning"?', 'buttons': ['Доброе утро', 'Добрый день', 'Добрый вечер', 'Здравствуйте'], 'correct': 'Доброе утро'},
            {'text': 'Как спросить "Как дела?" на английском?', 'buttons': ['How are you?', 'What is your name?', 'Where are you?', 'How old are you?'], 'correct': 'How are you?'},
            {'text': 'Выберите правильное произношение слова "Weather"', 'buttons': ['Вэзэр', 'Видэр', 'Вэзер', 'Вэзэрр'], 'correct': 'Вэзэр'},
            {'text': 'Что значит "Can you repeat?"?', 'buttons': ['Можете повторить?', 'Можете помочь?', 'Можете идти?', 'Можете говорить?'], 'correct': 'Можете повторить?'},
            {'text': 'Как спросить "Где находится туалет?"?', 'buttons': ['Where is the toilet?', 'Where are you?', 'How much?', 'What time is it?'], 'correct': 'Where is the toilet?'},
        ]
    elif skill == "Понимание текста":
        return [
            {'text': 'Что означает слово "quick"?', 'buttons': ['Быстрый', 'Медленный', 'Громкий', 'Тихий'], 'correct': 'Быстрый'},
            {'text': 'Переведите "The cat is on the table"', 'buttons': ['Кошка на столе', 'Кошка под столом', 'Кошка рядом с столом', 'Кошка в комнате'], 'correct': 'Кошка на столе'},
            {'text': 'Что означает "happy"?', 'buttons': ['Счастливый', 'Грустный', 'Злой', 'Уставший'], 'correct': 'Счастливый'},
            {'text': 'Переведите "He is running."', 'buttons': ['Он бежит', 'Он спит', 'Он читает', 'Он ест'], 'correct': 'Он бежит'},
            {'text': 'Что означает "big"?', 'buttons': ['Большой', 'Маленький', 'Высокий', 'Низкий'], 'correct': 'Большой'},
            {'text': 'Переведите "They are playing."', 'buttons': ['Они играют', 'Они работают', 'Они спят', 'Они идут'], 'correct': 'Они играют'},
        ]
    elif skill == "Понимание аудио":
        return [
            {'text': 'Что вы услышали? "The weather is sunny today."', 'buttons': ['Погода солнечная сегодня', 'Погода дождливая', 'Погода снег', 'Погода облачная'], 'correct': 'Погода солнечная сегодня'},
            {'text': 'Что означает "She is reading a book"?', 'buttons': ['Она читает книгу', 'Она пишет книгу', 'Она слушает книгу', 'Она убирается'], 'correct': 'Она читает книгу'},
            {'text': 'Что вы услышали? "I am going to the park."', 'buttons': ['Я иду в парк', 'Я дома', 'Я работаю', 'Я сплю'], 'correct': 'Я иду в парк'},
            {'text': 'Что означает "They have finished"?', 'buttons': ['Они закончили', 'Они начали', 'Они идут', 'Они играют'], 'correct': 'Они закончили'},
            {'text': 'Что вы услышали? "It is raining now."', 'buttons': ['Идёт дождь', 'Солнце светит', 'Идёт снег', 'Ветер дует'], 'correct': 'Идёт дождь'},
            {'text': 'Что означает "He is cooking"?', 'buttons': ['Он готовит', 'Он убирается', 'Он ест', 'Он смотрит'], 'correct': 'Он готовит'},
        ]
    else:
        return []

def interpret_score(score, total):
    ratio = score / total
    if ratio >= 0.8:
        return "Отлично! Вы хорошо прокачали этот навык."
    elif ratio >= 0.5:
        return "Средний уровень. Есть куда расти!"
    else:
        return "Нужно больше практики."

# Обработка кнопки "Уведомления" для открытия меню включения/выключения с текстом
@dp.message_handler(lambda message: message.text == "Уведомления")
async def handle_notifications_button(message: types.Message):
    user_id = message.from_user.id
    # Инициализация или обновление настроек
    if user_id not in user_notifications:
        user_notifications[user_id] = {'enabled': True, 'days': [], 'time': '09:00'}
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Включить уведомления", "Выключить уведомления")
    # Добавляем кнопку "Назад" для возврата в главное меню
    keyboard.add("Назад")
    await message.answer("Это еженедельное уведомление для прохождения теста.\nВыберите действие:", reply_markup=keyboard)

# Обработка нажатий "Включить уведомления" и "Выключить уведомления"
@dp.message_handler(lambda message: message.text in ["Включить уведомления", "Выключить уведомления"])
async def toggle_notifications(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_notifications:
        user_notifications[user_id] = {'enabled': True, 'days': [], 'time': '09:00'}
    if message.text == "Включить уведомления":
        user_notifications[user_id]['enabled'] = True
        await message.answer("Уведомления включены.", reply_markup=main_menu_kb())
    else:
        user_notifications[user_id]['enabled'] = False
        await message.answer("Уведомления выключены.", reply_markup=main_menu_kb())

# Обработка получения дней
@dp.message_handler(state=NotificationStates.waiting_for_days)
async def process_days(message: types.Message, state: FSMContext):
    days_str = message.text.strip()
    try:
        days_list = list(set(int(d) for d in days_str.split() if d in ['1','2','3','4','5','6','7']))
        user_id = message.from_user.id
        # обновляем настройки
        if user_id not in user_notifications:
            user_notifications[user_id] = {'enabled': True}
        user_notifications[user_id]['days'] = days_list
        await message.answer(
            f"Дни сохранены: {', '.join(map(str, days_list))}.\n"
            "Теперь отправьте время для уведомлений по МСК в формате HH:MM (например, 14:30):"
        )
        await NotificationStates.waiting_for_time.set()
    except:
        await message.answer("Некорректный ввод. Попробуйте снова.")
        await state.finish()

# Обработка времени уведомлений
@dp.message_handler(state=NotificationStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        # Проверяем формат HH:MM
        datetime.datetime.strptime(time_str, "%H:%M")
        user_id = message.from_user.id
        if user_id not in user_notifications:
            user_notifications[user_id] = {'enabled': True}
        user_notifications[user_id]['time'] = time_str
        await message.answer(f"Настройки уведомлений сохранены. Вы будете получать уведомления по дням: {', '.join(map(str, user_notifications[user_id]['days']))} в {time_str} по МСК.")
    except:
        await message.answer("Некорректный формат времени. Попробуйте снова (HH:MM).")
    await state.finish()

# Асинхронная функция для раз в неделю
async def scheduled_notifications():
    while True:
        now = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
        current_weekday = now.isoweekday()  # 1=Понедельник, 7=Воскресенье
        today_str = now.strftime("%Y-%m-%d")
        for user_id, settings in user_notifications.items():
            if settings.get('enabled') and settings.get('days') and current_weekday in settings['days']:
                last_date = last_sent.get(user_id)
                if last_date != today_str:
                    try:
                        await bot.send_message(user_id, "Это ваше напоминание пройти тест для улучшения английского!")
                        last_sent[user_id] = today_str
                    except:
                        pass
        await asyncio.sleep(3600)  # Проверяйте каждый час

# Запуск бота и задачи уведомлений
if __name__ == '__main__':
    import threading
    import asyncio
    threading.Thread(target=asyncio.run, args=(scheduled_notifications(),), daemon=True).start()
    from aiogram import executor
    executor.start_polling(dp)