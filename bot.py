import asyncio
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

# Частые вопросы
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
        [KeyboardButton(text="Главное меню")]
    ],
    resize_keyboard=True
)

# Клавиатура согласия на обработку данных
consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📜 Прочитать оферту", callback_data="read_offer")],
        [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no_1")]
    ]
)

# Клавиатура выбора доставки
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
    with open("offer.pdf", "rb") as file:
        await call.message.answer_document(file, caption="📄 Ознакомьтесь с офертой и выберите один из вариантов ниже.")
    await call.answer()


@dp.callback_query(lambda call: call.data == "consent_yes")
async def consent_given(call: types.CallbackQuery):
    global survey_id_counter
    chat_id = call.message.chat.id
    user_answers[chat_id] = {
        "id": survey_id_counter,
        "answers": []
    }
    survey_id_counter += 1
    await call.message.answer(f"📝 Ваша анкета ID {user_answers[chat_id]['id']}.\n\n{questions[0]}")
    await call.answer()


@dp.callback_query(lambda call: call.data == "consent_no_1")
async def consent_denied_once(call: types.CallbackQuery):
    await call.message.answer(
        "Мы не собираемся передавать ваши персональные данные третьим лицам.\n"
        "Это лишь нужно для того, чтобы менеджер смог обработать ваш заказ.\n"
        "Вы готовы дать согласие?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="consent_yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no_2")]
            ]
        )
    )
    await call.answer()


@dp.callback_query(lambda call: call.data == "consent_no_2")
async def consent_denied_final(call: types.CallbackQuery):
    await call.message.answer(
        "Тогда мы просим вас связаться напрямую с менеджером: @manager_contact"
    )
    await call.answer()


@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    response = "📌 Часто задаваемые вопросы:\n\n"
    for keyword in faq:
        response += f"👉 {keyword.capitalize()}\n"
    response += "\nНапишите ваш вопрос, и я попробую ответить!"
    await message.answer(response)


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

    if message.text.lower() == "главное меню":
        await message.answer("🔄 Главное меню", reply_markup=start_keyboard)
        return

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
            if len(user_answers[chat_id]["answers"]) == 12:
                await message.answer("⏳ Выберите срок доставки:", reply_markup=delivery_keyboard)
            else:
                await message.answer(questions[len(user_answers[chat_id]["answers"])])
        else:
            answers_text = "\n".join([
                f"{questions[i]}: {answer}" if i != 6 else "Прикрепленный файл"
                for i, answer in enumerate(user_answers[chat_id]["answers"])
            ])
            await bot.send_message(ADMIN_ID, f"📩 Новая анкета ID {user_answers[chat_id]['id']}:\n\n{answers_text}")

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
