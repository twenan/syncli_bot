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
user_answers = {}

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

# Клавиатуры
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
        [InlineKeyboardButton(text="Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="Нет", callback_data="consent_no")],
        [InlineKeyboardButton(text="Прочитать оферту", callback_data="read_offer")]
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

# Запрос согласия на обработку данных
@dp.message(Command("start"))
async def start(message: types.Message):
    logger.debug("Команда /start получена")
    await message.answer(
        "Перед заполнением анкеты, пожалуйста, подтвердите согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

@dp.callback_query(lambda call: call.data == "consent_yes")
async def consent_yes(call: types.CallbackQuery):
    global survey_id_counter
    chat_id = call.message.chat.id
    user_answers[chat_id] = {"id": survey_id_counter, "answers": []}
    survey_id_counter += 1
    await call.message.answer(f"📝 Ваша анкета ID {user_answers[chat_id]['id']}.", reply_markup=start_keyboard)
    await call.message.answer(questions[0])
    await call.answer()

@dp.callback_query(lambda call: call.data == "consent_no")
async def consent_no(call: types.CallbackQuery):
    await call.message.answer(
        "Мы не передаем ваши персональные данные третьим лицам. Это нужно, чтобы менеджер смог обработать ваш заказ.\n\n"
        "Вы готовы дать согласие на обработку данных?", reply_markup=consent_keyboard
    )
    await call.answer()

@dp.callback_query(lambda call: call.data == "read_offer")
async def read_offer(call: types.CallbackQuery):
    await call.message.answer_document(open("offer.pdf", "rb"), caption="Оферта на обработку персональных данных")
    await call.answer()

@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    await message.answer("📌 Часто задаваемые вопросы:\n\n👉 Доставка\n👉 Обрешетка\n👉 Оплата\n\nНапишите ваш вопрос, и я попробую ответить!")

@dp.message(lambda message: message.photo or message.document)
async def handle_file(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        user_answers[chat_id]["answers"].append(file_id)
        await message.answer(f"✅ Файл получен. {questions[len(user_answers[chat_id]['answers'])]}")
    else:
        await message.answer("📎 Отправьте файл в процессе заполнения анкеты после соответствующего вопроса.")

@dp.message()
async def collect_answers(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id]["answers"].append(message.text)
        if len(user_answers[chat_id]["answers"]) < len(questions):
            if len(user_answers[chat_id]["answers"]) == 12:
                await message.answer("⏳ Выберите срок доставки:", reply_markup=delivery_keyboard)
            else:
                await message.answer(questions[len(user_answers[chat_id]["answers"])])
        else:
            answers_text = "\n".join([f"{questions[i]}: {answer}" for i, answer in enumerate(user_answers[chat_id]["answers"])])
            await bot.send_message(ADMIN_ID, f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}")
            await message.answer("Спасибо! Мы свяжемся с вами в ближайшее время.")
            del user_answers[chat_id]

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
