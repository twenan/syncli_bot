from aiogram import Bot, Dispatcher, executor, types

# Инициализируем ботов с разными токенами
bot1 = Bot(token='7262011606:AAH7ao4aYos9K1zyeM8nZ_6WZE3JiCaSSJE')
bot2 = Bot(token='7724546136:AAFYu5vosG_-jMt4EDlpjTxmMx246PUWbMk')

dp1 = Dispatcher(bot1)
dp2 = Dispatcher(bot2)

# Обработчики для Бота 1
@dp1.message_handler(commands=['start'])
async def start_bot1(message: types.Message):
    await message.reply("Привет от Бота 1!")

# Обработчики для Бота 2
@dp2.message_handler(commands=['start'])
async def start_bot2(message: types.Message):
    await message.reply("Привет от Бота 2!")

# Запуск обоих ботов
async def on_startup(dispatcher):
    print("Боты запущены!")

if __name__ == '__main__':
    from asyncio import get_event_loop

    loop = get_event_loop()
    dp1.start_polling(loop=loop, skip_updates=True)
    dp2.start_polling(loop=loop, skip_updates=True)
