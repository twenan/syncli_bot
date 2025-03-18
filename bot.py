import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaDocument
from aiogram.filters import Command
from aiogram.enums import ChatType
from config import Config, load_config
import aiohttp
from io import BytesIO
from openpyxl import load_workbook

# Настройка логирования для вывода отладочной информации
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Загрузка конфигурации бота из файла config.py
config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

# Инициализация бота и диспетчера для обработки сообщений
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальные переменные:
# media_groups - словарь для хранения медиагрупп (фото/документы) пользователей
# faq - словарь для хранения часто задаваемых вопросов
# YANDEX_DISK_TOKEN - токен для доступа к Яндекс.Диску
# FILE_PATH - путь к файлу faq.xlsx на Яндекс.Диске
# MANAGER_CHAT_ID - ID чата для отправки анкет менеджеру
media_groups = {}
faq = {}
YANDEX_DISK_TOKEN = "y0__xD-s5TpBxijkzYgie2UyhKmZIBRVpLHIieiT1CMAYGOMXpgHQ"  # Проверьте полный токен
FILE_PATH = "faq.xlsx"  # Убедитесь, что файл в корне Яндекс.Диска
MANAGER_CHAT_ID = -4634857148

# Функция загрузки текущего ID анкеты из файла
def load_survey_id():
    """Читает последний ID анкеты из файла survey_id.txt. Если файла нет, возвращает 1."""
    try:
        with open("survey_id.txt", "r") as f:
            return int(f.read())
    except:
        return 1

# Функция сохранения текущего ID анкеты в файл
def save_survey_id(counter):
    """Записывает новый ID анкеты в файл survey_id.txt."""
    with open("survey_id.txt", "w") as f:
        f.write(str(counter))

survey_id_counter = load_survey_id()

# Функция загрузки данных пользователей из файла
def load_users():
    """Читает данные пользователей из users.json. Если файла нет, возвращает пустой словарь."""
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

# Функция сохранения данных пользователей в файл
def save_users(users):
    """Записывает данные пользователей в users.json с поддержкой кириллицы."""
    with open("users.json", "w") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

users = load_users()

# Список вопросов анкеты
questions = [
    "Ваше имя и фамилия",
    "Ваш ник в Telegram (через @)",
    "Напишите контактный телефон для связи",
    "Напишите наименование товара",
    "Вставьте ссылку на товар на маркетплейсах (если есть)",
    "Какое количество вам нужно?",
    "Прикрепите фото товара (или PDF, Excel-файл). Если файлов несколько, отправьте их одним сообщением или по одному, затем напишите 'Готово'",
    "Напишите размеры товара и количество каждого размера",
    "Укажите цвет товара",
    "Укажите, нужны ли дополнительные элементы (например, аксессуары, инструменты, важные детали).",
    "Какая упаковка нужна? (есть ли особенности упаковки и дополнительной защиты?)",
    "Брендинг (нужно ли брендирование товара, если да, укажите место и размер)",
    "Выберите срок доставки (10-13, 15-18, 25-30 дней, Авиа)",
    "Есть ли дополнительные уточнения?",
    "Перечислите вопросы для поставщика (если есть, укажите здесь)"
]

# Словарь для хранения ответов пользователей
user_answers = {}

# Функция загрузки FAQ из файла на Яндекс.Диске
async def load_faq_from_yandex_disk():
    """Загружает файл faq.xlsx с Яндекс.Диска и парсит его в словарь FAQ."""
    url = f"https://cloud-api.yandex.net/v1/disk/resources/download?path=/{FILE_PATH}"
    headers = {"Authorization": f"OAuth {YANDEX_DISK_TOKEN}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    download_data = await response.json()
                    download_url = download_data["href"]
                    async with session.get(download_url) as file_response:
                        if file_response.status == 200:
                            xlsx_content = await file_response.read()
                            faq_dict = {}
                            workbook = load_workbook(filename=BytesIO(xlsx_content))
                            sheet = workbook.active
                            for row in sheet.iter_rows(min_row=2, values_only=True):
                                question, answer = row[0], row[1]
                                if question and answer:
                                    faq_dict[str(question).lower()] = str(answer)
                            logger.debug(f"FAQ успешно загружен: {faq_dict}")
                            return faq_dict
                        else:
                            logger.error(f"Ошибка загрузки файла: {file_response.status}")
                            return {}
                else:
                    logger.error(f"Ошибка получения ссылки: {response.status} - {await response.text()}")
                    return {}
    except Exception as e:
        logger.error(f"Исключение при загрузке FAQ: {str(e)}")
        return {}

# Функция обновления глобального словаря FAQ
async def update_faq():
    """Обновляет глобальный словарь faq данными из Яндекс.Диска, добавляет заглушку при ошибке."""
    global faq
    faq = await load_faq_from_yandex_disk()
    if not faq:
        logger.warning("FAQ пустой, использую заглушку")
        faq = {"доставка": "Информация о доставке временно недоступна"}

# Функция периодического обновления FAQ
async def periodic_faq_update():
    """Запускает обновление FAQ каждые 60 минут в фоновом режиме."""
    while True:
        await update_faq()
        logger.debug("FAQ обновлен из Яндекс.Диска")
        await asyncio.sleep(3600)

# Клавиатура главного меню
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Заполнить анкету")],
        [KeyboardButton(text="Частые вопросы")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Инлайн-клавиатура для согласия на обработку данных
consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no")],
        [InlineKeyboardButton(text="📄 Посмотреть оферту", callback_data="view_offer")]
    ]
)

# Инлайн-клавиатура для второго шанса согласия
consent_second_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="final_no")]
    ]
)

# Инлайн-клавиатура для выбора срока доставки
delivery_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="10-13 дней", callback_data="10-13")],
        [InlineKeyboardButton(text="15-18 дней", callback_data="15-18")],
        [InlineKeyboardButton(text="25-30 дней", callback_data="25-30")],
        [InlineKeyboardButton(text="Авиа", callback_data="avia")]
    ]
)

# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    """Очищает данные пользователя и показывает главное меню."""
    chat_id = message.chat.id
    if chat_id in user_answers:
        del user_answers[chat_id]
    for media_group_id, group_data in list(media_groups.items()):
        if group_data["chat_id"] == chat_id:
            del media_groups[media_group_id]
    await message.answer("Привет! Я помогу вам с заказом. Выберите действие:", reply_markup=start_keyboard)

# Обработчик кнопки "Заполнить анкету"
@dp.message(lambda message: message.text == "Заполнить анкету")
async def request_consent(message: types.Message):
    """Запрашивает согласие на обработку персональных данных."""
    await message.answer(
        "Перед заполнением анкеты, пожалуйста, дайте согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

# Обработчик callback-запросов для согласия
@dp.callback_query(lambda call: call.data in ["consent_yes", "consent_no", "view_offer", "final_no"])
async def process_consent(call: types.CallbackQuery):
    """Обрабатывает выбор пользователя по согласию на обработку данных."""
    chat_id = call.message.chat.id
    if call.data == "consent_yes":
        global survey_id_counter
        user_answers[chat_id] = {"id": survey_id_counter, "answers": [], "source_chat": call.message.chat.id}
        survey_id_counter += 1
        save_survey_id(survey_id_counter)
        if str(chat_id) in users:
            user_answers[chat_id]["answers"] = [
                users[str(chat_id)]["name"],
                users[str(chat_id)]["telegram"],
                users[str(chat_id)]["phone"]
            ]
            await call.message.edit_text(f"Спасибо за согласие! 📝 Вы уже заполняли контактные данные, начнем с товара.\n\n{questions[3]}")
        else:
            await call.message.edit_text(f"Спасибо за согласие! 📝 Начнем.\n\n{questions[0]}")
    elif call.data == "view_offer":
        try:
            await bot.send_document(chat_id, document=types.FSInputFile("/home/anna/syncli_bot/offer.pdf"), caption="📄 Оферта")
            await call.message.edit_text("Ознакомьтесь с документом и выберите вариант.", reply_markup=consent_keyboard)
        except Exception as e:
            await call.message.edit_text("Ошибка при загрузке оферты. Попробуйте позже.", reply_markup=consent_keyboard)
    elif call.data == "consent_no":
        await call.message.edit_text(
            "Мы не передаем ваши данные третьим лицам. Они нужны только для заказа. Продолжить?",
            reply_markup=consent_second_keyboard
        )
    elif call.data == "final_no":
        await call.message.edit_text("Свяжитесь с менеджером напрямую: @YourManagerTelegram", reply_markup=None)

# Обработчик файлов (фото/документы)
@dp.message(lambda message: message.photo or message.document)
async def handle_file(message: types.Message):
    """Обрабатывает отправку файлов пользователем на этапе анкеты."""
    chat_id = message.chat.id
    logger.debug(f"Получено сообщение. Chat ID: {chat_id}, Media Group ID: {message.media_group_id}, Photo: {bool(message.photo)}, Document: {bool(message.document)}")
    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        if not any(isinstance(answer, list) for answer in user_answers[chat_id]["answers"]):
            user_answers[chat_id]["answers"].append([])
            logger.debug(f"Создан новый список файлов для Chat ID: {chat_id}")
        files_list = user_answers[chat_id]["answers"][6]
        if message.media_group_id:
            if message.media_group_id not in media_groups:
                media_groups[message.media_group_id] = {"chat_id": chat_id, "files": [], "processed": False}
            file_data = None
            if message.photo:
                photo = message.photo[-1]
                file_data = {"file_id": photo.file_id, "type": "photo"}
            elif message.document:
                file_data = {"file_id": message.document.file_id, "type": "document"}
            if file_data and file_data["file_id"] not in [f["file_id"] for f in media_groups[message.media_group_id]["files"]]:
                media_groups[message.media_group_id]["files"].append(file_data)
                logger.debug(f"Добавлен файл в медиагруппу {message.media_group_id}: {file_data['file_id']}")
            if not media_groups[message.media_group_id]["processed"]:
                media_groups[message.media_group_id]["processed"] = True
                await message.answer("✅ Файл(ы) получены. Прикрепите еще или напишите 'Готово' для продолжения.")
            return
        else:
            if message.photo:
                photo = message.photo[-1]
                files_list.append({"file_id": photo.file_id, "type": "photo"})
                logger.debug(f"Добавлено одиночное фото: {photo.file_id}")
            elif message.document:
                files_list.append({"file_id": message.document.file_id, "type": "document"})
                logger.debug(f"Добавлен одиночный документ: {message.document.file_id}")
            await message.answer("✅ Файл получен. Прикрепите еще или напишите 'Готово' для продолжения.")
            logger.debug(f"Текущий список файлов для Chat ID {chat_id}: {files_list}")
        return
    await message.answer("📎 Отправьте файл только на этапе соответствующего вопроса в анкете.")

# Обработчик команды "Готово" для завершения загрузки файлов
@dp.message(lambda message: message.text and message.text.lower() == "готово")
async def handle_ready(message: types.Message):
    """Завершает этап загрузки файлов и переходит к следующему вопросу."""
    chat_id = message.chat.id
    logger.debug(f"Получено 'Готово'. Chat ID: {chat_id}, user_answers: {user_answers.get(chat_id)}")
    if chat_id in user_answers:
        if len(user_answers[chat_id]["answers"]) >= 6 and isinstance(user_answers[chat_id]["answers"][6], list):
            files_list = user_answers[chat_id]["answers"][6]
            for media_group_id, group_data in list(media_groups.items()):
                if group_data["chat_id"] == chat_id:
                    files_list.extend([f for f in group_data["files"] if f["file_id"] not in [x["file_id"] for x in files_list]])
                    del media_groups[media_group_id]
                    logger.debug(f"Перенесены файлы из медиагруппы {media_group_id} в список Chat ID {chat_id}: {files_list}")
            if len(user_answers[chat_id]["answers"]) == 7:
                await message.answer(questions[7])
            else:
                user_answers[chat_id]["answers"].append("Готово")
                await message.answer("✅ Все файлы получены. Продолжаем заполнение анкеты.")
                await message.answer(questions[7])
            logger.debug(f"После 'Готово' user_answers для Chat ID {chat_id}: {user_answers[chat_id]}")
            return

# Обработчик кнопки "Частые вопросы"
@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    """Показывает список часто задаваемых вопросов из словаря faq."""
    chat_id = message.chat.id
    if chat_id in user_answers:
        del user_answers[chat_id]
    response = "📌 Часто задаваемые вопросы:\n\n" + "\n".join(f"👉 {k.capitalize()}" for k in faq) + "\n\nНапишите ваш вопрос!"
    await message.answer(response)

# Функция завершения анкеты и отправки данных менеджеру
async def finish_survey(chat_id, message):
    """Сохраняет данные пользователя и отправляет анкету менеджеру."""
    if str(chat_id) not in users and len(user_answers[chat_id]["answers"]) >= 3:
        users[str(chat_id)] = {
            "name": user_answers[chat_id]["answers"][0],
            "telegram": user_answers[chat_id]["answers"][1],
            "phone": user_answers[chat_id]["answers"][2]
        }
        save_users(users)
    answers_text = "\n".join(f"{questions[i]}: {answer}" for i, answer in enumerate(user_answers[chat_id]["answers"]) if not isinstance(answer, list))
    try:
        files = user_answers[chat_id]["answers"][6] if len(user_answers[chat_id]["answers"]) > 6 and isinstance(user_answers[chat_id]["answers"][6], list) else []
        logger.debug(f"Отправка файлов менеджеру для Chat ID {chat_id}: {files}")
        if files:
            media_group = []
            unique_file_ids = set()
            for file in files:
                file_id = file["file_id"]
                if file_id not in unique_file_ids:
                    if file["type"] == "photo":
                        media_group.append(InputMediaPhoto(media=file_id))
                    elif file["type"] == "document":
                        media_group.append(InputMediaDocument(media=file_id))
                    unique_file_ids.add(file_id)
            if media_group:
                media_group[0].caption = f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}"
                await bot.send_media_group(MANAGER_CHAT_ID, media=media_group)
                logger.debug(f"Отправлена медиагруппа с {len(media_group)} файлами")
        else:
            await bot.send_message(MANAGER_CHAT_ID, f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}")
        await message.answer("Ваша анкета успешно отправлена! Мы свяжемся с вами в ближайшее время.")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}")
        await message.answer("Ошибка при отправке анкеты. Свяжитесь с менеджером: @YourManagerTelegram")
    for media_group_id, group_data in list(media_groups.items()):
        if group_data["chat_id"] == chat_id:
            del media_groups[media_group_id]
    del user_answers[chat_id]

# Обработчик текстовых сообщений для анкеты и FAQ
@dp.message(lambda message: message.text)
async def collect_answers_or_faq(message: types.Message):
    """Собирает ответы на анкету или отвечает на вопросы из FAQ."""
    chat_id = message.chat.id
    text = message.text.lower()
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        for keyword, response in faq.items():
            if any(word in text for word in keyword.lower().split()):
                await message.reply(response)
                return
        return
    for keyword, response in faq.items():
        if any(word in text for word in keyword.lower().split()):
            await message.answer(response)
            return
    if chat_id in user_answers:
        if text == "назад" and user_answers[chat_id]["answers"]:
            user_answers[chat_id]["answers"].pop()
            await message.answer(f"🔄 Введите новый ответ:\n\n{questions[len(user_answers[chat_id]['answers'])]}")
            return
        if text == "готово":
            await handle_ready(message)
            return
        user_answers[chat_id]["answers"].append(message.text)
        next_index = len(user_answers[chat_id]["answers"])
        if next_index < len(questions):
            if next_index == 12:
                await message.answer("⏳ Выберите срок доставки:", reply_markup=delivery_keyboard)
            else:
                await message.answer(questions[next_index])
        else:
            await finish_survey(chat_id, message)
    else:
        if message.chat.type == ChatType.PRIVATE:
            await message.answer("Я пока не знаю ответа на этот вопрос, но передам его менеджеру!")

# Обработчик выбора срока доставки
@dp.callback_query(lambda call: call.data in ["10-13", "15-18", "25-30", "avia"])
async def delivery_selected(call: types.CallbackQuery):
    """Обрабатывает выбор срока доставки из инлайн-клавиатуры."""
    chat_id = call.message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(call.data)
        next_index = len(user_answers[chat_id]["answers"])
        if next_index < len(questions):
            await call.message.answer(f"✅ Срок доставки выбран.\n\n{questions[next_index]}")
        else:
            await finish_survey(chat_id, call.message)
    await call.answer()

# Главная функция запуска бота
async def main():
    """Запускает бота: загружает FAQ, запускает обновление и начинает обработку сообщений."""
    try:
        logger.info("Запуск бота...")
        await update_faq()  # Загружаем FAQ при старте
        asyncio.create_task(periodic_faq_update())  # Запускаем периодическое обновление
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())