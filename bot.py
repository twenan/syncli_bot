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

config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMIN_ID = 219614301  # Telegram ID менеджера
survey_id_counter = 1  # ID анкеты, начинается с 1

# Вопросы в анкете
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

# Основное меню
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

# Старт бота
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
            "Они нужны только для обработки вашего заказа. Вы уверены, что не хотите продолжить?",
            reply_markup=consent_second_keyboard  # Показываем вторую инлайн-клавиатуру
        )

    elif call.data == "final_no":
        # Если пользователь снова отказался
        await call.message.edit_text(
            "Тогда свяжитесь напрямую с менеджером: @YourManagerTelegram",
            reply_markup=None  # Убираем только инлайн-клавиатуру, но меню остается
        )

# 🔹 **СБОР ОТВЕТОВ В АНКЕТЕ**
@dp.message()
async def collect_answers_or_faq(message: types.Message):
    chat_id = message.chat.id

    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(message.text)
        if len(user_answers[chat_id]["answers"]) < len(questions):
            await message

# Частые вопросы
@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    response = "📌 Часто задаваемые вопросы:\n\n"
    for keyword in faq:
        response += f"👉 {keyword.capitalize()}\n"
    response += "\nНапишите ваш вопрос, и я попробую ответить!"
    await message.answer(response)

# Прикрепление файлов
@dp.message(lambda message: message.photo or message.document)
async def handle_file(message: types.Message):
    chat_id = message.chat.id

    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        user_answers[chat_id]["answers"].append(file_id)
        await message.answer(f"✅ Файл получен.\n\n{questions[len(user_answers[chat_id]['answers'])]}")
    else:
        await message.answer("📎 Отправьте файл в процессе заполнения анкеты после соответствующего вопроса.")

# Выбор срока доставки
@dp.callback_query()
async def delivery_selected(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(call.data)
        await call.message.answer("✅ Срок доставки выбран. " + questions[len(user_answers[chat_id]['answers'])])
    await call.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
