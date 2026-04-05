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
    caption = prefix + (message.caption or "")
    text_content = prefix + (message.text or "")

    # Список ID для рассылки (канал и админка)
    targets = [
        {"id": CHANNEL_ID, "label": "Канал"},
        {"id": ADMIN_GROUP_ID, "label": "Админка"}
    ]

    for target in targets:
        try:
            if message.text:
                await bot.send_message(chat_id=target['id'], text=text_content)
            elif message.photo:
                await bot.send_photo(chat_id=target['id'], photo=message.photo[-1].file_id, caption=caption)
            elif message.video:
                await bot.send_video(chat_id=target['id'], video=message.video.file_id, caption=caption)
        except Exception as e:
            logging.error(f"Ошибка отправки в {target['label']}: {e}")
            await message.answer(f"❌ Ошибка в {target['label']}: {e}")

    await message.answer("✅ Обработка завершена!")

        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка отправки. Проверь, админ ли бот в канале.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
