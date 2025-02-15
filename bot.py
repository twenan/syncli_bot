import asyncio
import requests
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
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
    "доставка": "Мы предлагаем доставку карго (10-13 дней, 15-18 дней, 25-30 дней) и авиа (от 1 дня).",
    "обрешетка": "Стоимость обрешетки - 30$ за метр кубический.",
    "оплата": "Оплата за услуги по безналичному расчету. Оплата за товар и логистику уточняется у менеджера."
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
    await message.answer("Привет! Я помогу вам с заказом. Выберите действие:", reply_markup=start_keyboard)

@dp.message(F.text == "Заполнить анкету")
async def request_consent(message: types.Message):
    await message.answer("Прежде чем продолжить, согласны ли вы с обработкой персональных данных?", reply_markup=consent_keyboard)

@dp.callback_query(F.data == "read_offer")
async def send_offer(call: types.CallbackQuery):
    await call.message.answer_document(FSInputFile("offer.pdf"), caption="📄 Оферта по обработке персональных данных")

@dp.callback_query(F.data == "consent_no")
async def reject_consent(call: types.CallbackQuery):
    await call.message.answer("Мы не передаем ваши данные третьим лицам. Это нужно лишь для обработки заказа. Согласны?", reply_markup=consent_keyboard)

@dp.callback_query(F.data == "consent_yes")
async def start_survey(call: types.CallbackQuery):
    global survey_id_counter
    chat_id = call.message.chat.id
    user_answers[chat_id] = {"id": survey_id_counter, "answers": []}
    survey_id_counter += 1
    await call.message.answer(f"📝 Ваша анкета ID {user_answers[chat_id]['id']}.", reply_markup=start_keyboard)
    await call.message.answer(questions[0])

@dp.message(F.text == "Частые вопросы")
async def show_faq(message: types.Message):
    response = "📌 Часто задаваемые вопросы:\n\n"
    for keyword in faq:
        response += f"👉 {keyword.capitalize()}\n"
    response += "\nНапишите ваш вопрос, и я попробую ответить!"
    await message.answer(response)

@dp.message(F.text == "Главное меню")
async def main_menu(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=start_keyboard)

@dp.message(F.photo | F.document)
async def handle_file(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        user_answers[chat_id]["answers"].append(file_id)
        await message.answer(f"✅ Файл получен. {questions[len(user_answers[chat_id]['answers'])]}")
    else:
        await message.answer("📎 Отправьте файл в процессе заполнения анкеты после соответствующего вопроса.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
