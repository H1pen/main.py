import asyncio
import logging
import time
import threading
from flask import Flask
from typing import Any, Awaitable, Callable, Dict
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command

# --- ВСТРОЕННЫЙ СЕРВЕР ДЛЯ UPTIMEROBOT ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- НАСТРОЙКИ БОТА ---
TOKEN = "8668356633:AAHWwI4AKB1zygevOaoIuEWrodIUZiSw60U"
ADMIN_GROUP_ID = -1003670917930
CHANNEL_ID = -1003742221408 

# Middleware для КД (1 сообщение в минуту)
class SlowModeMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_msg_times = {}

    async def __call__(self, handler, event: types.Message, data):
        if not event.from_user:
            return await handler(event, data)
        user_id = event.from_user.id
        now = time.time()
        if user_id in self.last_msg_times and now - self.last_msg_times[user_id] < 60:
            left = int(60 - (now - self.last_msg_times[user_id]))
            return await event.answer(f"⏳ КД! Подожди {left} сек.")
        self.last_msg_times[user_id] = now
        return await handler(event, data)

bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(SlowModeMiddleware())
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Присылай текст, фото или видео для публикации.")

@dp.message()
async def handle_post(message: types.Message):
    user = message.from_user
    prefix = "... пищет-\n\n"
    user_info = f"\n\n👤 Отправил: {user.full_name} (@{user.username or 'скрыто'})"
    
    try:
        if message.text:
            await bot.send_message(CHANNEL_ID, prefix + message.text)
            await bot.send_message(ADMIN_GROUP_ID, prefix + message.text + user_info)
        elif message.photo:
            photo_id = message.photo[-1].file_id
            cap = prefix + (message.caption or "")
            await bot.send_photo(CHANNEL_ID, photo=photo_id, caption=cap)
            await bot.send_photo(ADMIN_GROUP_ID, photo=photo_id, caption=cap + user_info)
        elif message.video:
            video_id = message.video.file_id
            cap = prefix + (message.caption or "")
            await bot.send_video(CHANNEL_ID, video=video_id, caption=cap)
            await bot.send_video(ADMIN_GROUP_ID, video=video_id, caption=cap + user_info)
        else:
            return await message.answer("❌ Только текст, фото или видео!")

        await message.answer("✅ Отправлено в канал!")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка. Проверь, что бот — админ в канале.")

async def main():
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
