import asyncio
import logging
import time
import os
from typing import Any, Awaitable, Callable, Dict
from threading import Thread

from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command
from flask import Flask

# --- Настройка Flask для Render ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run_web_server():
    # Render передает порт в переменной окружения PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- Конфигурация бота ---
TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930

# --- Middleware для Антиспама (3 сообщ. = варн, 4 варна = бан) ---
class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.users = {}

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        if user_id not in self.users:
            self.users[user_id] = {'last_msg_time': 0, 'warns': 0, 'msg_count': 0, 'mute_until': 0}
        
        user = self.users[user_id]

        # 1. Проверка на бан
        if now < user['mute_until']:
            return 

        # 2. Считаем сообщения в интервале 60 секунд
        if now - user['last_msg_time'] < 60:
            user['msg_count'] += 1
        else:
            user['msg_count'] = 1 
            if user['warns'] > 0 and now - user['last_msg_time'] > 300:
                user['warns'] = 0 

        user['last_msg_time'] = now

        # 3. Логика предупреждений
        if user['msg_count'] >= 3:
            user['warns'] += 1
            
            if user['warns'] >= 4:
                user['mute_until'] = now + 300
                user['warns'] = 0
                user['msg_count'] = 0
                return await event.answer("🚫 Ты проигнорировал предупреждения. Бан на 5 минут за спам.")
            
            return await event.answer(f"⚠️ Хватит спамить! Предупреждение {user['warns']}/4. После 4-го — бан.")

        return await handler(event, data)

# --- Инициализация бота ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(AntiSpamMiddleware())

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Присылай новости школы. Не спамь: 3 мгновенных сообщения = предупреждение!")

@dp.message()
async def handle_user_post(message: types.Message):
    user = message.from_user
    info_tag = f"\n\n👤 От: {user.full_name} (@{user.username or 'id' + str(user.id)})"

    try:
        # Копируем сообщение в админку
        await message.send_copy(ADMIN_GROUP_ID)
        await bot.send_message(ADMIN_GROUP_ID, f"☝️ Источник: {info_tag}")
        await message.answer("✅ Принято, спасибо!")
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")

# --- Запуск ---
async def main():
    # Запускаем фоновый веб-сервер
    keep_alive()
    print("Веб-сервер запущен. Бот начинает опрос...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
