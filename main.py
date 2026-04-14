import asyncio
import logging
import time
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command

# --- СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK"
def run_flask(): app.run(host='0.0.0.0', port=10000)

# --- НАСТРОЙКИ ---
TOKEN = "8668356633:AAHWwI4AKB1zygevOaoIuEWrodIUZiSw60U"
ADMIN_GROUP_ID = -1003670917930
CHANNEL_ID = -1003742221408 

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Middleware для КД (1 мин)
class SlowModeMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_msg_times = {}
    async def __call__(self, handler, event: types.Message, data):
        if not event.from_user: return await handler(event, data)
        uid = event.from_user.id
        now = time.time()
        if uid in self.last_msg_times and now - self.last_msg_times[uid] < 60:
            return await event.answer(f"⏳ Подожди {int(60-(now-self.last_msg_times[uid]))} сек.")
        self.last_msg_times[uid] = now
        return await handler(event, data)

dp.message.middleware(SlowModeMiddleware())

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Присылай пост!")

@dp.message()
async def handle(m: types.Message):
    # Формируем части сообщения
    prefix = "... пишет-\n\n"
    footer = "\n\n@PodslushanoMYschoolBot"
    user_info = f"\n\n👤 От: {m.from_user.full_name} (@{m.from_user.username or 'скрыто'})"

    try:
        if m.text:
            text = f"{prefix}{m.text}{footer}"
            await bot.send_message(CHANNEL_ID, text)
            await bot.send_message(ADMIN_GROUP_ID, text + user_info)
        elif m.photo:
            cap = f"{prefix}{m.caption or ''}{footer}"
            await bot.send_photo(CHANNEL_ID, m.photo[-1].file_id, caption=cap)
            await bot.send_photo(ADMIN_GROUP_ID, m.photo[-1].file_id, caption=cap + user_info)
        elif m.video:
            cap = f"{prefix}{m.caption or ''}{footer}"
            await bot.send_video(CHANNEL_ID, m.video.file_id, caption=cap)
            await bot.send_video(ADMIN_GROUP_ID, m.video.file_id, caption=cap + user_info)
        
        await m.answer("✅ Отправлено!")
    except Exception as e:
        logging.error(e)
        await m.answer("❌ Ошибка. Проверь права бота в канале.")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
