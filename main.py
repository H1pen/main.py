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

# Middleware для ограничения отправки (раз в 60 секунд)
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
        limit = 60 # 1 минута
        
        if user_id in self.last_msg_times:
            time_passed = now - self.last_msg_times[user_id]
            if time_passed < limit:
                left = int(limit - time_passed)
                return await event.answer(f"⏳ КД! Подожди {left} сек. перед следующей новостью.")

        self.last_msg_times[user_id] = now
        return await handler(event, data)

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(SlowModeMiddleware())
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Присылай текст, фото или видео для публикации в канале.\n\n⚠️ Лимит: 1 сообщение в минуту.")

@dp.message()
async def handle_post(message: types.Message):
    user = message.from_user
    prefix = "... — пишет:\n\n"
    user_info = f"\n\n👤 Отправил: {user.full_name} (@{user.username or 'скрыто'})"
    
    try:
        # ОБРАБОТКА ТЕКСТА
        if message.text:
            content = prefix + message.text
            # В канал (только текст)
            await bot.send_message(chat_id=CHANNEL_ID, text=content)
            # В админку (текст + автор)
            await bot.send_message(chat_id=ADMIN_GROUP_ID, text=content + user_info)
        
        # ОБРАБОТКА ФОТО
        elif message.photo:
            caption = prefix + (message.caption or "")
            photo_id = message.photo[-1].file_id
            # В канал
            await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=caption)
            # В админку
            await bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=photo_id, caption=caption + user_info)
            
        # ОБРАБОТКА ВИДЕО
        elif message.video:
            caption = prefix + (message.caption or "")
            video_id = message.video.file_id
            # В канал
            await bot.send_video(chat_id=CHANNEL_ID, video=video_id, caption=caption)
            # В админку
            await bot.send_video(chat_id=ADMIN_GROUP_ID, video=video_id, caption=caption + user_info)
        
        else:
            return await message.answer("❌ Бот принимает только текст, фото или видео.")

        await message.answer("✅ Принято! Твоя новость отправлена в канал.")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка отправки. Убедись, что бот — администратор в канале и группе.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
