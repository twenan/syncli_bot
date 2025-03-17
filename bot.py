import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaDocument
from aiogram.filters import Command
from aiogram.enums import ChatType
from config import Config, load_config

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Загрузка конфигурации бота
config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальный словарь для хранения медиагрупп
media_groups = {}

# ID чата с менеджерами
MANAGER_CHAT_ID = -4634857148

# Функции для работы с ID анкет
def load_survey_id():
    try:
        with open("survey_id.txt", "r") as f:
            return int(f.read())
    except:
        return 1

def save_survey_id(counter):
    with open("survey_id.txt", "w") as f:
        f.write(str(counter))

survey_id_counter = load_survey_id()

# Функции для работы с данными пользователей
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

users = load_users()

# Вопросы анкеты
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

user_answers = {}

# Часто задаваемые вопросы
faq = {
    "доставка": "Мы предлагаем доставку карго (10-13 дней, 15-18 дней, 25-30 дней) и авиа (от 1 дня). По белой доставке обратитесь к менеджеру.",
    "обрешетка": "Стоимость обрешетки - 30$ за метр кубический.",
    "оплата": "Мы принимаем оплату за наши услуги по безналичному расчету. Оплата за товар и логистику уточняется у менеджера."
}

# Главное меню
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Заполнить анкету")],
        [KeyboardButton(text="Частые вопросы")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Инлайн-клавиатура для согласия
consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no")],
        [InlineKeyboardButton(text="📄 Посмотреть оферту", callback_data="view_offer")]
    ]
)

# Инлайн-клавиатура для второго шанса
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

# Обработка команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_answers:
        del user_answers[chat_id]
    for media_group_id, group_data in list(media_groups.items()):
        if group_data["chat_id"] == chat_id:
            del media_groups[media_group_id]
    await message.answer("Привет! Я помогу вам с заказом. Выберите действие:", reply_markup=start_keyboard)

# Запрос согласия перед анкетой
@dp.message(lambda message: message.text == "Заполнить анкету")
async def request_consent(message: types.Message):
    await message.answer(
        "Перед заполнением анкеты, пожалуйста, дайте согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

# Обработка согласия
@dp.callback_query(lambda call: call.data in ["consent_yes", "consent_no", "view_offer", "final_no"])
async def process_consent(call: types.CallbackQuery):
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

# Обработка файлов
@dp.message(lambda message: message.photo or message.document)
async def handle_file(message: types.Message):
    chat_id = message.chat.id
    logger.debug(f"Получено сообщение. Chat ID: {chat_id}, Media Group ID: {message.media_group_id}, Photo: {bool(message.photo)}, Document: {bool(message.document)}")

    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        # Инициализируем список файлов, если его еще нет
        if not any(isinstance(answer, list) for answer in user_answers[chat_id]["answers"]):
            user_answers[chat_id]["answers"].append([])
            logger.debug(f"Создан новый список файлов для Chat ID: {chat_id}")

        files_list = user_answers[chat_id]["answers"][6]

        # Если это медиагруппа, сохраняем файлы во временный словарь
        if message.media_group_id:
            if message.media_group_id not in media_groups:
                media_groups[message.media_group_id] = {"chat_id": chat_id, "files": []}

            if message.photo:
                photo = message.photo[-1]  # Берем самое большое разрешение
                media_groups[message.media_group_id]["files"].append({
                    "file_id": photo.file_id,
                    "type": "photo"
                })
            elif message.document:
                media_groups[message.media_group_id]["files"].append({
                    "file_id": message.document.file_id,
                    "type": "document"
                })

            logger.debug(f"Добавлен файл в медиагруппу {message.media_group_id} для Chat ID {chat_id}")
            return  # Не отправляем ответ, пока не соберем всю группу

        # Если это одиночный файл
        else:
            if message.photo:
                photo = message.photo[-1]
                files_list.append({
                    "file_id": photo.file_id,
                    "type": "photo"
                })
            elif message.document:
                files_list.append({
                    "file_id": message.document.file_id,
                    "type": "document"
                })

            await message.answer("✅ Файл получен. Прикрепите еще или напишите 'Готово' для продолжения.")
            logger.debug(f"Текущий список файлов для Chat ID {chat_id}: {files_list}")
    else:
        await message.answer("📎 Отправьте файл только на этапе соответствующего вопроса в анкете.")

# Функция для обработки завершения медиагруппы
@dp.message(lambda message: message.text and message.text.lower() == "готово")
async def handle_ready(message: types.Message):
    chat_id = message.chat.id

    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        files_list = user_answers[chat_id]["answers"][6]

        # Добавляем файлы из медиагрупп, если они есть
        for media_group_id, group_data in media_groups.items():
            if group_data["chat_id"] == chat_id:
                files_list.extend(group_data["files"])
                del media_groups[media_group_id]  # Удаляем обработанную группу

        await message.answer("✅ Все файлы получены. Продолжаем заполнение анкеты.")
        await message.answer(questions[7])  # Переходим к следующему вопросу

# Обработка FAQ
@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_answers:
        del user_answers[chat_id]
    response = "📌 Часто задаваемые вопросы:\n\n" + "\n".join(f"👉 {k.capitalize()}" for k in faq) + "\n\nНапишите ваш вопрос!"
    await message.answer(response)

# Завершение анкеты
async def finish_survey(chat_id, message):
    if str(chat_id) not in users and len(user_answers[chat_id]["answers"]) >= 3:
        users[str(chat_id)] = {
            "name": user_answers[chat_id]["answers"][0],
            "telegram": user_answers[chat_id]["answers"][1],
            "phone": user_answers[chat_id]["answers"][2]
        }
        save_users(users)

    answers_text = "\n".join(
        f"{questions[i]}: {answer}" for i, answer in enumerate(user_answers[chat_id]["answers"])
        if not isinstance(answer, list)
    )

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
            await bot.send_message(
                MANAGER_CHAT_ID,
                f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}"
            )
        
        await message.answer("Ваша анкета успешно отправлена! Мы свяжемся с вами в ближайшее время.")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}")
        await message.answer("Ошибка при отправке анкеты. Свяжитесь с менеджером: @YourManagerTelegram")
    
    # Очистка медиагрупп
    for media_group_id, group_data in list(media_groups.items()):
        if group_data["chat_id"] == chat_id:
            del media_groups[media_group_id]
    
    del user_answers[chat_id]

# Обработка текстовых ответов анкеты и FAQ
@dp.message(lambda message: message.text)
async def collect_answers_or_faq(message: types.Message):
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

        if len(user_answers[chat_id]["answers"]) == 6:
            if text == "готово":
                user_answers[chat_id]["answers"].append(text)
                await message.answer(questions[7])
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

# Выбор срока доставки
@dp.callback_query(lambda call: call.data in ["10-13", "15-18", "25-30", "avia"])
async def delivery_selected(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(call.data)
        next_index = len(user_answers[chat_id]["answers"])
        if next_index < len(questions):
            await call.message.answer(f"✅ Срок доставки выбран.\n\n{questions[next_index]}")
        else:
            await finish_survey(chat_id, call.message)
    await call.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())