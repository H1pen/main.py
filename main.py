import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930 
CHANNEL_ID = "@WeSchoolPodslyshano" 

# --- Middleware для задержки 30 секунд (без банов) ---
class SlowModeMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_msg_times = {}

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
        
        if user_id in self.last_msg_times:
            time_passed = now - self.last_msg_times[user_id]
            if time_passed < 30:
                left = int(30 - time_passed)
                return await event.answer(f"⏳ Подожди {left} сек. перед следующей отправкой.")

        self.last_msg_times[user_id] = now
        return await handler(event, data)

# --- Инициализация ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(SlowModeMiddleware())

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Присылай новость. Она появится в канале с пометкой '... — пишет:'.\n\nОграничение: 1 пост в 30 секунд.")

@dp.message()
async def handle_post(message: types.Message):
    user = message.from_user
    prefix = "... — пишет:\n\n"
    
    try:
        # 1. Если это ТЕКСТОВОЕ сообщение
        if message.text:
            content = prefix + message.text
            # В канал
            await bot.send_message(chat_id=CHANNEL_ID, text=content)
            # В админку
            await bot.send_message(
                chat_id=ADMIN_GROUP_ID, 
                text=f"{content}\n\n👤 Автор: {user.full_name} (@{user.username or 'скрыто'})"
            )
        
        # 2. Если это ФОТО
        elif message.photo:
            caption = prefix + (message.caption or "")
            # Берем последнее фото (самое лучшее качество)
            photo_id = message.photo[-1].file_id
            await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=caption)
            await bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=photo_id, 
                                 caption=f"{caption}\n\n👤 Автор: {user.full_name}")

        # 3. Если это ВИДЕО
        elif message.video:
            caption = prefix + (message.caption or "")
            await bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=caption)
            await bot.send_video(chat_id=ADMIN_GROUP_ID, video=message.video.file_id, 
                                 caption=f"{caption}\n\n👤 Автор: {user.full_name}")
        
        else:
            return await message.answer("❌ Тип файла не поддерживается (шли текст, фото или видео).")

        await message.answer("✅ Отправлено в канал!")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Произошла ошибка. Убедись, что бот — администратор канала.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
