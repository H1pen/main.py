import asyncio
import logging
import time
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command

# --- ВСТРОЕННЫЙ СЕРВЕР ДЛЯ РАБОТЫ 24/7 ---
app = Flask(__name__)
@app.route('/')
def home(): return "Бот в сети!"
def run_flask(): app.run(host='0.0.0.0', port=10000)

# --- НАСТРОЙКИ ---
TOKEN = "8668356633:AAHWwI4AKB1zygevOaoIuEWrodIUZiSw60U"
ADMIN_GROUP_ID = -1003670917930
CHANNEL_ID = -1003742221408 

# Короткая подпись, как вы просили
FOOTER = "\n\n@PodslushanoMYschoolBot"

class SlowModeMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_msg_times = {}
    async def __call__(self, handler, event: types.Message, data):
        if not event.from_user: return await handler(event, data)
        user_id = event.from_user.id
        now = time.time()
        if user_id in self.last_msg_times and now - self.last_msg_times[user_id] < 60:
            return await event.answer(f"⏳ Подожди {int(60 - (now - self.last_msg_times[user_id]))} сек.")
        self.last_msg_times[user_id] = now
        return await handler(event, data)

bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(SlowModeMiddleware())
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Присылай пост для публикации.")

@dp.message()
async def handle_post(message: types.Message):
    user = message.from_user
    prefix = "... пишет-\n"  # Текст перед сообщением
    user_info = f"\n\n👤 Отправил: {user.full_name} (@{user.username or 'скрыто'})"
    
    try:
        # Обработка ТЕКСТА
        if message.text:
            final_text = f"{prefix}{message.text}{FOOTER}"
            await bot.send_message(CHANNEL_ID, final_text)
            await bot.send_message(ADMIN_GROUP_ID, final_text + user_info)
        
        # Обработка ФОТО
        elif message.photo:
            photo_id = message.photo[-1].file_id
            user_text = message.caption if message.caption else ""
            cap = f"{prefix}{user_text}{FOOTER}"
            await bot.send_photo(CHANNEL_ID, photo=photo_id, caption=cap)
            await bot.send_photo(ADMIN_GROUP_ID, photo=photo_id, caption=cap + user_info)
            
        # Обработка ВИДЕО
        elif message.video:
            video_id = message.video.file_id
            user_text = message.caption if message.caption else ""
            cap = f"{prefix}{user_text}{FOOTER}"
            await bot.send_video(CHANNEL_ID, video=video_id, caption=cap)
            await bot.send_video(ADMIN_GROUP_ID, video=video_id, caption=cap + user_info)
        
        await message.answer("✅ Отправлено в канал!")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка при отправке. Проверь права бота.")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
