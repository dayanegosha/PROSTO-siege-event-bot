from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.filters import Command
import sqlite3
from datetime import datetime
import json
import logging
import os
import xlsxwriter
import pytz

# Bot token
BOT_TOKEN = 'your_api_token'

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Database setup
DB_FILE = "users_data.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# Проверка наличия столбцов test_date и test_time в таблице users
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]
if 'test_date' not in column_names:
    cursor.execute("ALTER TABLE users ADD COLUMN test_date TEXT;")
    conn.commit()
if 'test_time' not in column_names:
    cursor.execute("ALTER TABLE users ADD COLUMN test_time TEXT;")
    conn.commit()
if 'phone_number' not in column_names:
    cursor.execute("ALTER TABLE users ADD COLUMN phone_number TEXT;")
    conn.commit()

# Admin ID
ADMIN_ID = 1291677361

# Bot states
USER_STATES = {}

# Загружаем вопросы из файла quiz_questions.json
def load_quiz_questions():
    try:
        with open("quiz_questions.json", "r", encoding="utf-8") as f:
            questions = json.load(f)
            if not questions or not all("question" in q and "options" in q and "correct" in q for q in questions):
                logging.error("Quiz questions file is empty or contains invalid data.")
                return []
            return questions
    except FileNotFoundError:
        logging.error("Quiz questions file not found.")
        return []
    except json.JSONDecodeError:
        logging.error("Failed to decode quiz questions JSON.")
        return []

QUIZ = load_quiz_questions()  # Теперь вопросы загружаются из файла

# Template for content blocks with full file paths
CONTENT_BLOCKS = [
    ("Эвакуация", ""),
    ("Маленькие ленинградцы", ""),
    ("Театр", ""),
    ("Восстановление", "")
]

# Keyboards
def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Начнём", callback_data="start_materials")
    ]])

def next_block_keyboard(text):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, callback_data="next_block")
    ]])

def quiz_keyboard(question_index, options, answered_options, correct_options):
    buttons = []
    for i, option in enumerate(options):
        button_data = f"quiz|{question_index}|{i}"
        if i in answered_options:
            if i in correct_options:
                button = InlineKeyboardButton(text=f"✅ {option}", callback_data="answered_correct")
            else:
                button = InlineKeyboardButton(text=f"❌ {option}", callback_data="answered_incorrect")
        else:
            button = InlineKeyboardButton(text=option, callback_data=button_data)
        buttons.append([button])  # Каждая кнопка в отдельной строке
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Скачать результаты", callback_data="download_results")],
        [InlineKeyboardButton(text="Скачать результаты в файл", callback_data="download_results_file")],
        [InlineKeyboardButton(text="Удалить пользователя", callback_data="delete_user")],
        [InlineKeyboardButton(text="Удалить всю базу", callback_data="delete_all_users")]
    ])

def delete_user_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_delete_user")]
    ])

# Handlers
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    try:
        if user_id == ADMIN_ID:
            await message.answer("Добро пожаловать, администратор!", reply_markup=admin_keyboard())
            return
        
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            await message.answer("Вы уже проходили тест. Тест можно пройти только один раз.")
            return
        
        USER_STATES[user_id] = {
            "quiz_index": 0,
            "score": 0,
            "completed": False,
            "content_index": 0,
            "answers": {},  # Хранение полного текста ответов для каждого вопроса
            "answered_options": set(),  # Хранение индексов уже выбранных вариантов
            "correct_options": set(),  # Хранение индексов правильных вариантов
            "current_question_index": None,  # Индекс текущего вопроса
            "next_block_pressed": False,  # Флаг для отслеживания нажатия на кнопку "Готов перейти к следующему блоку"
            "phone_number": None
        }
        contact_button = types.KeyboardButton(text="Отправить контакт", request_contact=True)
        reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[contact_button]], one_time_keyboard=True)
        await message.reply(
            "Привет! Ты находишься на выставке «Письма, сохранившие память», посвящённой Дню снятия блокады Ленинграда. Давай знакомиться: оставь свой контакт.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.exception("An error occurred while handling /start command.")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова позже.")

@dp.message(F.content_type == ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    contact = message.contact
    USER_STATES[user_id]["phone_number"] = contact.phone_number
    await message.reply("Теперь вы можете продолжить.", reply_markup=types.ReplyKeyboardRemove())

    await message.reply("Спасибо! Этот чат-бот будет сопровождать тебя во время посещения экспозиции и поможет лучше понять события тех дней благодаря рассказам аудиогида.\n\nНа выставке ты познакомишься с письмами, которые являются символом настоящего мужества ленинградцев и раскрывают их уклад жизни во время блокады. Эти истории объединяет глубокое чувство — надежда, которая помогала пережить самые тяжёлые моменты и верить в светлое будущее.\n\nВ конце мы приготовили небольшую викторину. Если ты справишься со всеми вопросами, тебя ждет приятный бонус.\n\nНу что, начнём погружение в прошлое?", 
                        reply_markup=start_keyboard())

@dp.callback_query(lambda c: c.data == "start_materials")
async def start_materials(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id == ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этому функционалу.")
        return
    
    state = USER_STATES.get(user_id, {})
    content_index = state.get("content_index", 0)
    
    if content_index < len(CONTENT_BLOCKS):
        block_name, img_path, audio_path = CONTENT_BLOCKS[content_index]
        message_with_photo = await callback_query.message.answer_photo(
            img_path, 
            caption=block_name
        )
        await callback_query.message.answer_audio(audio_path)
        
        # Отключаем кнопки предыдущего блока
        if "previous_message_id" in USER_STATES[user_id]:
            previous_message_id = USER_STATES[user_id]["previous_message_id"]
            try:
                await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=previous_message_id, reply_markup=None)  # Отключаем кнопки предыдущего блока
            except Exception as e:
                logging.debug(f"Failed to edit message markup: {e}")
        
        if content_index + 1 < len(CONTENT_BLOCKS):
            if content_index == 0:
                text = "Далее мы расскажем тебе о том, как эвакуировали детей Ленинграда, с какими испытаниями им пришлось столкнуться и как они возвращались домой после войны. Просим тебя перейти к следующему планшету выставки «Маленькие ленинградцы»."
            elif content_index == 1:
                text = "Теперь ты узнаешь о работе ленинградских театров в годы войны и их вкладе в победу. Просим тебя перейти к следующему планшету выставки «Театр»."
            elif content_index == 2:
                text = "В конце экспозиции мы бы хотели поделиться с тобой, как ленинградцы возвращались в город и восстанавливали инфраструктуру города. Просим тебя перейти к следующему планшету выставки «Восстановление»."
            await callback_query.message.answer(text, reply_markup=next_block_keyboard("Готов перейти к следующему блоку"))
        elif content_index == len(CONTENT_BLOCKS) - 1:
            await callback_query.message.answer("Мы рады, что ты принял участие в акции и прослушал все материалы. \n\nДавай проверим, насколько хорошо получилось все запомнить? Всего будет 8 вопросов! Если правильно и с первого раза ответишь на все, то сможешь получить приятный бонус.", reply_markup=start_keyboard())
        
        USER_STATES[user_id]["previous_message_id"] = message_with_photo.message_id  # Сохраняем id сообщения с фото для последующего редактирования
        USER_STATES[user_id]["content_index"] += 1
    else:
        await start_quiz(callback_query)

@dp.callback_query(lambda c: c.data == "next_block")
async def next_block(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id == ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этому функционалу.")
        return
    
    state = USER_STATES.get(user_id, {})
    content_index = state.get("content_index", 0)
    
    if "previous_message_id" in USER_STATES[user_id]:
        previous_message_id = USER_STATES[user_id]["previous_message_id"]
        try:
            await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=previous_message_id, reply_markup=None)  # Отключаем кнопки предыдущего блока
        except Exception as e:
            logging.debug(f"Failed to edit message markup: {e}")

    if content_index < len(CONTENT_BLOCKS):
        block_name, img_path, audio_path = CONTENT_BLOCKS[content_index]
        message_with_photo = await callback_query.message.answer_photo(
            img_path, 
            caption=block_name
        )
        await callback_query.message.answer_audio(audio_path)
        
        if content_index + 1 < len(CONTENT_BLOCKS):
            if content_index == 0:
                text = "Далее мы расскажем тебе о том, как эвакуировали детей Ленинграда, с какими испытаниями им пришлось столкнуться и как они возвращались домой после войны. Просим тебя перейти к следующему планшету выставки «Маленькие ленинградцы»."
            elif content_index == 1:
                text = "Теперь ты узнаешь о работе ленинградских театров в годы войны и их вкладе в победу. Просим тебя перейти к следующему планшету выставки «Театр»."
            elif content_index == 2:
                text = "В конце экспозиции мы бы хотели поделиться с тобой, как ленинградцы возвращались в город и восстанавливали инфраструктуру города. Просим тебя перейти к следующему планшету выставки «Восстановление»."
            await callback_query.message.answer(text, reply_markup=next_block_keyboard("Готов перейти к следующему блоку"))
            USER_STATES[user_id]["previous_message_id"] = message_with_photo.message_id  # Сохраняем id сообщения с фото для последующего редактирования
        elif content_index == len(CONTENT_BLOCKS) - 1:
            await callback_query.message.answer("Мы рады, что ты принял участие в акции и прослушал все материалы. \n\nДавай проверим, насколько хорошо получилось все запомнить? Всего будет 8 вопросов! Если правильно и с первого раза ответишь на все, то сможешь получить приятный бонус.", reply_markup=start_keyboard())
        USER_STATES[user_id]["content_index"] += 1
    else:
        await start_quiz(callback_query)

async def start_quiz(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    state = USER_STATES.get(user_id, {})
    quiz_index = state.get("quiz_index", 0)
    if quiz_index < len(QUIZ):
        question_data = QUIZ[quiz_index]
        USER_STATES[user_id]["quiz_index"] += 1
        USER_STATES[user_id]["answered_options"] = set()  # Очищаем answered_options для нового вопроса
        USER_STATES[user_id]["correct_options"] = set()  # Очищаем correct_options для нового вопроса
        USER_STATES[user_id]["current_question_index"] = quiz_index  # Устанавливаем текущий вопрос
        await callback_query.message.answer(question_data["question"], reply_markup=quiz_keyboard(quiz_index, question_data["options"], state.get("answered_options", set()), state.get("correct_options", set())))
    else:
        await callback_query.message.answer("Тест завершен! Спасибо за участие.")

@dp.message(Command("help"))
async def handle_help_command(message: types.Message):
    await message.answer("В случае ошибок и вопросов образовавшихся по ходу теста - @OxGexrge")

@dp.callback_query(lambda c: c.data.startswith("quiz|"))
async def handle_quiz(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id == ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этому функционалу.")
        return
    
    parts = callback_query.data.split("|")
    if len(parts) != 3:
        await callback_query.message.answer("Некорректный ответ. Попробуйте снова.")
        return
    _, question_index_str, option_index_str = parts
    question_index = int(question_index_str)
    option_index = int(option_index_str)
    user_state = USER_STATES.get(user_id, {})
    current_question_index = user_state.get("current_question_index")
    if question_index != current_question_index:
        await callback_query.answer("Перейдите к следующему вопросу.")
        return
    logging.debug(f"Handling question {question_index} with answer index: {option_index}")
    if question_index < len(QUIZ) and option_index < len(QUIZ[question_index]["options"]):
        question_data = QUIZ[question_index]
        correct_answer = question_data["correct"]
        selected_option = question_data["options"][option_index]
        USER_STATES[user_id]["answers"][question_index] = selected_option
        USER_STATES[user_id]["answered_options"].add(option_index)
        if correct_answer == selected_option:
            USER_STATES[user_id]["score"] += 1
            USER_STATES[user_id]["correct_options"].add(option_index)
            await callback_query.message.answer("Да, всё верно!")
        else:
            await callback_query.message.answer(f"Нет, правильный ответ: {correct_answer}")
        await callback_query.message.edit_reply_markup(reply_markup=quiz_keyboard(question_index, question_data["options"], user_state.get("answered_options", set()), user_state.get("correct_options", set())))
        if question_index + 1 == len(QUIZ):
            score = user_state["score"]
            USER_STATES[user_id]["completed"] = True
            moscow_tz = pytz.timezone('Europe/Moscow')
            now_msk = datetime.now(moscow_tz)
            test_date = now_msk.strftime("%d.%m.%Y")
            test_time = now_msk.strftime("%H:%M:%S")
            cursor.execute(""" 
            INSERT INTO users (name, telegram_id, score, attempts, test_date, test_time, phone_number) 
            VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
            score = ?,
            attempts = attempts + 1,
            test_date = ?,
            test_time = ?,
            phone_number = ?;
            """, (callback_query.from_user.full_name, callback_query.from_user.id, score, test_date, test_time, USER_STATES[user_id].get("phone_number"), score, test_date, test_time, USER_STATES[user_id].get("phone_number")))
            conn.commit()
            if score == 8 and test_date <= "27.01.2024":
                await callback_query.message.answer(f"Ты правильно ответил на {score}/{len(QUIZ)} вопросов!")
                await callback_query.message.answer("Получить приз за участие можно на стойке администраторов, показав это сообщение. ❤️")
            else:
                await callback_query.message.answer(f"Ты правильно ответил на {score}/{len(QUIZ)} вопросов!")
            await callback_query.message.answer("Наше путешествие по страницам памяти подошло к концу. Рады, что мы были вместе! Будем благодарны получить обратную связь по ссылке https://www.prostospb.team/blockade/#rec852565304.")
        else:
            await next_question(callback_query)  # Переход к следующему вопросу

async def next_question(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    state = USER_STATES.get(user_id, {})
    quiz_index = state.get("quiz_index", 0)
    if quiz_index < len(QUIZ):
        question_data = QUIZ[quiz_index]
        USER_STATES[user_id]["quiz_index"] += 1
        USER_STATES[user_id]["answered_options"] = set()  # Очищаем answered_options для нового вопроса
        USER_STATES[user_id]["correct_options"] = set()  # Очищаем correct_options для нового вопроса
        USER_STATES[user_id]["current_question_index"] = quiz_index  # Устанавливаем текущий вопрос
        await callback_query.message.answer(question_data["question"], reply_markup=quiz_keyboard(quiz_index, question_data["options"], state.get("answered_options", set()), state.get("correct_options", set())))
    else:
        await callback_query.message.answer("Тест завершен! Спасибо за участие.")

@dp.callback_query(lambda c: c.data == "answered_correct")
async def already_answered_correct(callback_query: types.CallbackQuery):
    await callback_query.answer("Вы уже ответили на этот вопрос.")  # Сообщение о том, что вопрос уже был задан

@dp.callback_query(lambda c: c.data == "answered_incorrect")
async def already_answered_incorrect(callback_query: types.CallbackQuery):
    await callback_query.answer("Вы уже ответили на этот вопрос.")  # Сообщение о том, что вопрос уже был задан

@dp.callback_query(lambda c: c.data == "download_results")
async def download_results(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этой функции.")
        return
    cursor.execute("SELECT name, telegram_id, score, test_date, test_time, phone_number FROM users")
    rows = cursor.fetchall()
    results = []
    for row in rows:
        results.append(f"Имя: {row[0]}, ID: {row[1]}, Прошел тест на {row[2]}/8 {row[3]} в {row[4]} МСК, Номер телефона: {row[5]}")
    if results:
        report_text = "\n".join(results)
        await callback_query.message.answer(report_text)
    else:
        await callback_query.message.answer("Нет пользователей, прошедших тест.")

@dp.callback_query(lambda c: c.data == "download_results_file")
async def download_results_file(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этой функции.")
        return
    cursor.execute("SELECT name, telegram_id, score, test_date, test_time, phone_number FROM users")
    rows = cursor.fetchall()
    file_path = "results.xlsx"
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, "Имя в Телеграмме")
    worksheet.write(0, 1, "ID")
    worksheet.write(0, 2, "Сколько баллов")
    worksheet.write(0, 3, "Дата прохождения")
    worksheet.write(0, 4, "Время прохождения (МСК)")
    worksheet.write(0, 5, "Номер телефона")
    for idx, row in enumerate(rows, 1):
        worksheet.write(idx, 0, row[0])
        worksheet.write(idx, 1, row[1])
        worksheet.write(idx, 2, row[2])
        worksheet.write(idx, 3, row[3])
        worksheet.write(idx, 4, row[4])
        worksheet.write(idx, 5, row[5])
    workbook.close()
    await callback_query.message.answer_document(types.FSInputFile(file_path))
    os.remove(file_path)

@dp.callback_query(lambda c: c.data == "delete_user")
async def delete_user(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этой функции.")
        return
    
    await callback_query.message.answer("Введите ID пользователя, которого хотите удалить:", reply_markup=delete_user_keyboard())
    USER_STATES[ADMIN_ID] = {"awaiting_delete_user_id": True}

@dp.message(lambda m: USER_STATES.get(m.from_user.id, {}).get("awaiting_delete_user_id"))
async def handle_delete_user_id(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой функции.")
        return
    
    try:
        user_to_delete = int(message.text)
        cursor.execute("DELETE FROM users WHERE telegram_id = ?", (user_to_delete,))
        conn.commit()
        if cursor.rowcount > 0:
            await message.answer(f"Пользователь с ID {user_to_delete} удален из базы данных.")
        else:
            await message.answer(f"Пользователь с ID {user_to_delete} не найден в базе данных.")
    except ValueError:
        await message.answer("Некорректный ID. Пожалуйста, введите числовое значение.")
    finally:
        USER_STATES[ADMIN_ID].pop("awaiting_delete_user_id", None)

@dp.callback_query(lambda c: c.data == "delete_all_users")
async def delete_all_users(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этой функции.")
        return
    
    cursor.execute("DELETE FROM users")
    conn.commit()
    await callback_query.message.answer("Вся база данных очищена.")

@dp.callback_query(lambda c: c.data == "cancel_delete_user")
async def cancel_delete_user(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.message.answer("У вас нет доступа к этой функции.")
        return
    
    USER_STATES[ADMIN_ID].pop("awaiting_delete_user_id", None)
    await callback_query.message.answer("Отмена удаления пользователя.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
