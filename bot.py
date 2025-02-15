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

faq = {
    "доставка": "Мы предлагаем доставку карго (10-13 дней, 15-18 дней, 25-30 дней) и авиа (от 1 дня). По белой доставке обратитесь к менеджеру.",
    "обрешетка": "Стоимость обрешетки - 30$ за метр кубический.",
    "оплата": "Мы принимаем оплату за наши услуги по безналичному расчету. Оплата за товар и логистику уточняется у менеджера."
}

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Заполнить анкету")],
        [KeyboardButton(text="Частые вопросы")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no")],
        [InlineKeyboardButton(text="📄 Прочитать оферту", callback_data="read_offer")]
    ]
)

delivery_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="10-13 дней", callback_data="10-13")],
        [InlineKeyboardButton(text="15-18 дней", callback_data="15-18")],
        [InlineKeyboardButton(text="25-30 дней", callback_data="25-30")],
        [InlineKeyboardButton(text="Авиа", callback_data="avia")]
    ]
)

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.debug("Команда /start получена")
    await message.answer("Привет! Я помогу вам с заказом. Выберите действие:", reply_markup=start_keyboard)

@dp.message(lambda message: message.text == "Заполнить анкету")
async def ask_consent(message: types.Message):
    await message.answer(
        "Перед началом анкеты, пожалуйста, дайте согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

@dp.callback_query(lambda call: call.data == "consent_yes")
async def consent_yes(call: types.CallbackQuery):
    global survey_id_counter
    chat_id = call.message.chat.id
    user_answers[chat_id] = {
        "id": survey_id_counter,
        "answers": []
    }
    survey_id_counter += 1
    await call.message.answer(f"📝 Ваша анкета ID {user_answers[chat_id]['id']}.")
    await call.message.answer(questions[0])
    await call.answer()

@dp.callback_query(lambda call: call.data == "consent_no")
async def consent_no(call: types.CallbackQuery):
    await call.message.answer(
        "Мы не собираемся передавать ваши персональные данные третьим лицам. Они нужны только для обработки вашего заказа менеджером.\n\n"
        "❓ Все равно не согласны? Тогда мы просим вас связаться напрямую с менеджером: @your_manager"
    )
    await call.answer()

@dp.callback_query(lambda call: call.data == "read_offer")
async def send_offer(call: types.CallbackQuery):
    with open("offer.pdf", "rb") as file:
        await call.message.answer_document(file, caption="📄 Оферта на обработку персональных данных")
    await call.answer()

@dp.callback_query()
async def delivery_selected(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(call.data)
        await call.message.answer("✅ Срок доставки выбран. " + questions[len(user_answers[chat_id]['answers'])])
    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
