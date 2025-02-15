import asyncio
import requests
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ChatType
from config import Config, load_config

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

API_TOKEN = "7262011606:AAHg4H2fqIyD6KWfLRiMnnduY5dad_NG1-U"  # Заменить на реальный токен

bot = Bot(token=API_TOKEN)
dp = Dispatcher()  # В aiogram 3.x Dispatcher создается без аргументов

ADMIN_ID = 219614301  # Telegram ID менеджера

questions = [
    "Ваше имя и фамилия",
    "Ваш ник в Telegram (через @)",
    "Напишите контактный телефон для связи",
    "Напишите наименование товара",
    "Вставьте ссылку на товар на маркетплейсах (если есть)",
    "Какое количество вам нужно?",
    "Прикрепите фото товара",
    "Напишите размеры товара и количество каждого размера",
    "Укажите цвет товара",
    "Укажите, нужны ли дополнительные элементы (например, аксессуары, инструменты, важные детали).",
    "Какая упаковка нужна? (есть ли особенности упаковки и дополнительной защиты?)",
    "Брендинг (нужно ли брендирование товара, если да, укажите место и размер)",
    "Выберите срок доставки (10-15, 15-18 или 18-25 дней)",
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

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.debug("Команда /start получена")
    await message.answer("Привет! Я помогу вам с заказом. Выберите действие:", reply_markup=start_keyboard)

@dp.message(lambda message: message.text == "Заполнить анкету")
async def start_survey(message: types.Message):
    chat_id = message.chat.id
    user_answers[chat_id] = []
    await message.answer(questions[0])

@dp.message(lambda message: message.text == "Частые вопросы")
async def show_faq(message: types.Message):
    response = "📌 Часто задаваемые вопросы:\n\n"
    for keyword in faq:
        response += f"👉 {keyword.capitalize()}\n"
    response += "\nНапишите ваш вопрос, и я попробую ответить!"
    await message.answer(response)

@dp.message(lambda message: message.photo)
async def handle_photo(message: types.Message):
    chat_id = message.chat.id

    if chat_id in user_answers and len(user_answers[chat_id]) == 6:  # 6 - индекс вопроса "Прикрепите фото товара"
        photo_file_id = message.photo[-1].file_id  # Берем фото в максимальном качестве
        user_answers[chat_id].append(photo_file_id)  # Сохраняем фото как file_id
        
        await message.answer("Фото получено. " + questions[len(user_answers[chat_id])])
    else:
        await message.answer("Отправьте фото в процессе заполнения анкеты после соответствующего вопроса.")


@dp.message()
async def collect_answers_or_faq(message: types.Message):
    chat_id = message.chat.id

    # Проверяем, есть ли текст в сообщении
    if not message.text:
        return  # Если нет текста (например, фото, документ), просто игнорируем

    text = message.text.lower()

    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.debug(f"Сообщение в группе ({message.chat.title}): {message.text}")
        for keyword, response in faq.items():
            if any(word in text for word in keyword.lower().split()):
                await message.reply(response)
                return
        return  # Если нет совпадений в FAQ, бот просто игнорирует сообщение в группе
    
    if chat_id in user_answers:
        user_answers[chat_id].append(message.text)
        if len(user_answers[chat_id]) < len(questions):
            await message.answer(questions[len(user_answers[chat_id])])
        else:
            answers_text = "\n".join([
                f"{questions[i]}: {answer}" if i != 6 else "Прикрепленное фото"
                for i, answer in enumerate(user_answers[chat_id])
            ])
            await bot.send_message(ADMIN_ID, f"📩 Новая анкета от клиента:\n\n{answers_text}")
            await message.answer("Спасибо! Мы свяжемся с вами в ближайшее время.")
            del user_answers[chat_id]
    else:
        # Поиск ответа в FAQ по ключевым словам
        for keyword, response in faq.items():
            if any(word in text for word in keyword.lower().split()):
                await message.answer(response)
                return
        if message.chat.type == ChatType.PRIVATE:
            await message.answer("Я пока не знаю ответа на этот вопрос, но передам его менеджеру!")

# Главная асинхронная функция для запуска бота
async def main():
    await dp.start_polling(bot)  # Передаем объект bot при запуске

if __name__ == '__main__':
    # Теперь запускаем бота через асинхронный вызов
    asyncio.run(main())
