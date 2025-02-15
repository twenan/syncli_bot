import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import Config, load_config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMIN_ID = 219614301
survey_id_counter = 1
user_answers = {}

questions = [
    "Ваше имя и фамилия", "Ваш ник в Telegram (через @)", "Напишите контактный телефон для связи",
    "Напишите наименование товара", "Вставьте ссылку на товар на маркетплейсах (если есть)",
    "Какое количество вам нужно?", "Прикрепите фото товара (или PDF, Excel-файл)",
    "Напишите размеры товара и количество каждого размера", "Укажите цвет товара",
    "Нужны ли дополнительные элементы?", "Какая упаковка нужна?",
    "Брендинг (нужно ли брендирование?)", "Выберите срок доставки",
    "Есть ли дополнительные уточнения?", "Перечислите вопросы для поставщика"
]

faq = {
    "доставка": "Мы предлагаем карго (10-13, 15-18, 25-30 дней) и авиа (от 1 дня).",
    "обрешетка": "Стоимость обрешетки - 30$ за метр кубический.",
    "оплата": "Мы принимаем оплату за наши услуги по безналичному расчету."
}

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Заполнить анкету")],
        [KeyboardButton(text="Частые вопросы")],
        [KeyboardButton(text="Главное меню")]
    ],
    resize_keyboard=True
)

consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📜 Прочитать оферту", callback_data="read_offer")],
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no_1")]
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
async def start_survey(message: types.Message):
    await message.answer(
        "Перед началом анкеты, пожалуйста, дайте согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

@dp.callback_query(lambda call: call.data == "read_offer")
async def send_offer(call: types.CallbackQuery):
    try:
        with open("offer.pdf", "rb") as file:
            await call.message.answer_document(file, caption="📄 Ознакомьтесь с офертой и выберите один из вариантов ниже.")
    except Exception as e:
        logger.error(f"Ошибка отправки оферты: {e}")
        await call.message.answer("Ошибка загрузки оферты. Попробуйте позже.")
    await call.answer()

@dp.callback_query(lambda call: call.data in ["10-13", "15-18", "25-30", "avia"])
async def handle_delivery_selection(call: types.CallbackQuery):
    await call.message.answer(f"Вы выбрали срок доставки: {call.data} дней")
    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
