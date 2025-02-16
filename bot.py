import asyncio
import requests
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

ADMIN_ID = 219614301  # Telegram ID менеджера
survey_id_counter = 1  # ID анкеты, начинается с 1

# Вопросы анкеты
questions = [
    "Ваше имя и фамилия",
    "Ваш ник в Telegram (через @)",
    "Напишите контактный телефон для связи",
    "Напишите наименование товара",
    "Вставьте ссылку на товар на маркетплейсах (если есть)",
    "Какое количество вам нужно?",
    "Прикрепите фото товара (или PDF, Excel-файл)",
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

# 🔹 **ИНКЛАЙН-КЛАВИАТУРА ДЛЯ ОФЕРТЫ**
consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no")],
        [InlineKeyboardButton(text="📄 Посмотреть оферту", callback_data="view_offer")]
    ]
)

# 🔹 **ИНКЛАЙН-КЛАВИАТУРА ДЛЯ ВТОРОГО ШАНСА**
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

# 🏁 Функция обработки команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    logger.debug("Команда /start получена")
    await message.answer("Привет! Я помогу вам с заказом. Выберите действие:", reply_markup=start_keyboard)

  # 🔹 **ЗАПРОС НА СОГЛАСИЕ ПЕРЕД АНКЕТОЙ**
@dp.message(lambda message: message.text == "Заполнить анкету")
async def request_consent(message: types.Message):
    await message.answer(
        "Перед заполнением анкеты, пожалуйста, дайте согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

# 🔹 **ОБРАБОТКА ВЫБОРА ПОЛЬЗОВАТЕЛЯ (ДА / НЕТ / ПОСМОТРЕТЬ ОФЕРТУ)**
@dp.callback_query(lambda call: call.data in ["consent_yes", "consent_no", "view_offer", "final_no"])
async def process_consent(call: types.CallbackQuery):
    chat_id = call.message.chat.id

    if call.data == "consent_yes":
        # Начинаем анкету
        global survey_id_counter
        user_answers[chat_id] = {
            "id": survey_id_counter,
            "answers": []
        }
        survey_id_counter += 1
        await call.message.edit_text(f"Спасибо за согласие! 📝 Ваша анкета ID {user_answers[chat_id]['id']}.\n\n{questions[0]}")
    
    elif call.data == "view_offer":
        # Отправляем оферту и снова предлагаем выбор
        await bot.send_document(chat_id, document=types.FSInputFile("/home/anna/syncli_bot/offer.pdf"), caption="📄 Оферта на обработку персональных данных")
        await call.message.edit_text("Ознакомьтесь с документом и выберите вариант.", reply_markup=consent_keyboard)

    elif call.data == "consent_no":
        # Предлагаем еще раз подумать
        await call.message.edit_text(
            "Мы не передаем ваши персональные данные третьим лицам. "
            "Они нужны только для обработки вашего заказа. Вы хотите продолжить?",
            reply_markup=consent_second_keyboard  # Показываем вторую инлайн-клавиатуру
        )

    elif call.data == "final_no":
        # Если пользователь снова отказался
        await call.message.edit_text(
            "Тогда свяжитесь напрямую с менеджером: @YourManagerTelegram",
            reply_markup=None  # Убираем только инлайн-клавиатуру, но меню остается
        )
        
# 📝 Запуск анкеты
@dp.message(lambda message: message.text == "Заполнить анкету")
async def start_survey(message: types.Message):
    global survey_id_counter
    chat_id = message.chat.id
    user_answers[chat_id] = {
        "id": survey_id_counter,
        "answers": []
    }
    survey_id_counter += 1
    await message.answer(f"📝 Ваша анкета ID {user_answers[chat_id]['id']}.\n\n{questions[0]}")

# ❓ Обработка нажатия кнопки "Частые вопросы"
@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    response = "📌 Часто задаваемые вопросы:\n\n"
    for keyword in faq:
        response += f"👉 {keyword.capitalize()}\n"
    response += "\nНапишите ваш вопрос, и я попробую ответить!"
    await message.answer(response)

# 📎 Прикрепление фото и документов
@dp.message(lambda message: message.photo or message.document)
async def handle_file(message: types.Message):
    chat_id = message.chat.id

    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        user_answers[chat_id]["answers"].append(file_id)
        await message.answer(f"✅ Файл получен.\n\n{questions[len(user_answers[chat_id]['answers'])]}")
    else:
        await message.answer("📎 Отправьте файл в процессе заполнения анкеты после соответствующего вопроса.")

# 🔄 Обработка ответов анкеты и FAQ
@dp.message()
async def collect_answers_or_faq(message: types.Message):
    chat_id = message.chat.id

    # Если пользователь хочет вернуться назад в анкете
    if message.text.lower() == "назад" and chat_id in user_answers and user_answers[chat_id]["answers"]:
        user_answers[chat_id]["answers"].pop()
        await message.answer(f"🔄 Введите новый ответ:\n\n{questions[len(user_answers[chat_id]['answers'])]}")
        return

    if not message.text:
        return

    text = message.text.lower()

    # Обработка сообщений в группах (ищем совпадения в FAQ)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.debug(f"Сообщение в группе ({message.chat.title}): {message.text}")
        for keyword, response in faq.items():
            if any(word in text for word in keyword.lower().split()):
                await message.reply(response)
                return
        return

    # Продолжение заполнения анкеты
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(message.text)

        if len(user_answers[chat_id]["answers"]) < len(questions):
            if len(user_answers[chat_id]["answers"]) == 12:  # Вопрос о сроке доставки
                await message.answer("⏳ Выберите срок доставки:", reply_markup=delivery_keyboard)
            else:
                await message.answer(questions[len(user_answers[chat_id]["answers"])])
        else:
            answers_text = "\n".join([
                f"{questions[i]}: {answer}" if i != 6 else "Прикрепленный файл"
                for i, answer in enumerate(user_answers[chat_id]["answers"])
            ])

            # Отправляем заполненную анкету админу
            await bot.send_message(
                ADMIN_ID, 
                f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}"
            )

            # Отправляем прикрепленный файл админу, если он есть
            if len(user_answers[chat_id]["answers"]) > 6 and user_answers[chat_id]["answers"][6]:
                await bot.send_document(
                    ADMIN_ID, 
                    user_answers[chat_id]["answers"][6], 
                    caption=f"📎 Файл к анкете ID {user_answers[chat_id]['id']}"
                )

            await message.answer("Спасибо! Мы свяжемся с вами в ближайшее время.")
            del user_answers[chat_id]
    else:
        for keyword, response in faq.items():
            if any(word in text for word in keyword.lower().split()):
                await message.answer(response)
                return

        if message.chat.type == ChatType.PRIVATE:
            await message.answer("Я пока не знаю ответа на этот вопрос, но передам его менеджеру!")

# ⏳ Выбор срока доставки
@dp.callback_query()
async def delivery_selected(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(call.data)
        await call.message.answer("✅ Срок доставки выбран. " + questions[len(user_answers[chat_id]['answers'])])
    await call.answer()

# 🚀 Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
