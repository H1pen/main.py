import asyncio
import logging
import os
import time
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930  # Группа админов (с данными юзера)
CHANNEL_ID = -1008668356633      # Канал (только сообщение)

# --- Middleware для Антиспама ---
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
        if now < user['mute_until']:
            return 

        if now - user['last_msg_time'] < 60:
            user['msg_count'] += 1
        else:
            user['msg_count'] = 1 
            if user['warns'] > 0 and now - user['last_msg_time'] > 300:
                user['warns'] = 0 

        user['last_msg_time'] = now

        if user['msg_count'] >= 3:
            user['warns'] += 1
            if user['warns'] >= 4:
                user['mute_until'] = now + 300
                user['warns'] = 0
                user['msg_count'] = 0
                return await event.answer("🚫 Бан на 5 минут за спам.")
            return await event.answer(f"⚠️ Предупреждение {user['warns']}/4.")

        return await handler(event, data)

# --- Инициализация бота ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(AntiSpamMiddleware())

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Присылай новость, я опубликую её в канале.")

@dp.message()
async def handle_user_post(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else f"id{user.id}"
    
    try:
        # 1. В КАНАЛ (только копия контента)
        # Если здесь ошибка, бот напишет её ниже
        await message.send_copy(chat_id=CHANNEL_ID)
        
        # 2. В АДМИН-ГРУППУ
        await message.send_copy(chat_id=ADMIN_GROUP_ID)
        await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"👤 Автор: {user.full_name} ({username})"
        )
        
        await message.answer("✅ Принято!")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        # Бот ответит вам, какая именно ошибка произошла
        await message.answer(f"❌ Ошибка при отправке в канал: {e}\nУбедись, что бот админ в канале {CHANNEL_ID}")

        await message.answer("✅ Сообщение отправлено в канал!")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("⚠️ Ошибка. Убедись, что бот — админ в канале и группе.")

# --- Запуск ---
async def main():
    keep_alive()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
