import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

# Определяем состояния для FSM
class SurveyState(StatesGroup):
    waiting_for_consent = State()
    filling_survey = State()

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

# Клавиатура для согласия на обработку данных
consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no")],
        [InlineKeyboardButton(text="📜 Прочитать оферту", callback_data="read_offer")]
    ]
)

# Клавиатура для меню
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Заполнить анкету")],
        [KeyboardButton(text="Частые вопросы")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
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

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(SurveyState.waiting_for_consent)
    logger.debug("Команда /start получена")
    await message.answer(
        "Прежде чем продолжить, пожалуйста, подтвердите согласие на обработку персональных данных.",
        reply_markup=consent_keyboard
    )

@dp.callback_query(lambda c: c.data == "read_offer")
async def send_offer(call: types.CallbackQuery):
    await call.message.answer_document(
        types.FSInputFile("/home/anna/syncli_bot/offer.pdf"),
        caption="📜 Ознакомьтесь с офертой."
    )

@dp.callback_query(lambda c: c.data == "consent_yes")
async def consent_yes(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(SurveyState.filling_survey)
    await call.message.answer("✅ Спасибо! Теперь вы можете заполнить анкету.", reply_markup=start_keyboard)

@dp.callback_query(lambda c: c.data == "consent_no")
async def consent_no(call: types.CallbackQuery):
    await call.message.answer(
        "Мы не собираемся передавать ваши персональные данные третьим лицам. "
        "Это нужно только для обработки вашего заказа менеджером.\n\n"
        "❗ Вы уверены, что не хотите продолжить?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, согласен", callback_data="consent_yes")],
                [InlineKeyboardButton(text="❌ Нет, связаться с менеджером", callback_data="contact_manager")]
            ]
        )
    )

@dp.callback_query(lambda c: c.data == "contact_manager")
async def contact_manager(call: types.CallbackQuery):
    await call.message.answer("🔹 Свяжитесь с менеджером: @ВашМенеджер")

@dp.message(lambda message: message.text == "Заполнить анкету")
async def start_survey(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != SurveyState.filling_survey:
        await message.answer("❗ Сначала подтвердите согласие на обработку персональных данных!")
        return

    global survey_id_counter
    chat_id = message.chat.id
    user_answers[chat_id] = {
        "id": survey_id_counter,
        "answers": []
    }
    survey_id_counter += 1
    await message.answer(f"📝 Ваша анкета ID {user_answers[chat_id]['id']}.\n\n{questions[0]}")

# 📷 Обработка фото и файлов
@dp.message(lambda message: message.photo or message.document)
async def handle_file(message: types.Message):
    chat_id = message.chat.id

    if chat_id in user_answers and len(user_answers[chat_id]["answers"]) == 6:
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        user_answers[chat_id]["answers"].append(file_id)
        await message.answer(f"✅ Файл получен.\n\n{questions[len(user_answers[chat_id]['answers'])]}")
    else:
        await message.answer("📎 Отправьте файл в процессе заполнения анкеты после соответствующего вопроса.")

@dp.message()
async def collect_answers_or_faq(message: types.Message):
    chat_id = message.chat.id

    if message.text.lower() == "назад" and chat_id in user_answers and user_answers[chat_id]["answers"]:
        user_answers[chat_id]["answers"].pop()
        await message.answer(f"🔄 Введите новый ответ:\n\n{questions[len(user_answers[chat_id]['answers'])]}")
        return

    if not message.text:
        return

    text = message.text.lower()

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

            await bot.send_message(
                ADMIN_ID, 
                f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}"
            )

            if len(user_answers[chat_id]["answers"]) > 6 and user_answers[chat_id]["answers"][6]:
                await bot.send_document(
                    ADMIN_ID, 
                    user_answers[chat_id]["answers"][6], 
                    caption=f"📎 Файл к анкете ID {user_answers[chat_id]['id']}"
                )

            await message.answer("Спасибо! Мы свяжемся с вами в ближайшее время.")
            del user_answers[chat_id]

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
