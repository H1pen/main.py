import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- НАСТРОЙКИ (Все данные уже вписаны) ---
TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930 
CHANNEL_ID = "@WeSchoolPodslyshano"  # Твой канал из скриншота

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Присылай пост, я опубликую его в канале анонимно!")

@dp.message()
async def handle_post(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else f"id{user.id}"
    
    try:
        # 1. ОТПРАВКА В КАНАЛ (Без данных автора)
        # Мы используем copy_to, чтобы сообщение выглядело как оригинальное
        await message.copy_to(chat_id=CHANNEL_ID)
        
        # 2. ОТПРАВКА В ГРУППУ АДМИНОВ (С данными автора)
        await message.copy_to(chat_id=ADMIN_GROUP_ID)
        await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"👤 **Отправил:** {user.full_name} ({username})",
            parse_mode="Markdown"
        )
        
        await message.answer("✅ Сообщение успешно опубликовано в канале!")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        # Если будет ошибка, бот напишет её причину
        await message.answer(f"❌ Ошибка отправки. Убедись, что бот — АДМИН в канале.\nОшибка: {e}")

async def main():
    # Удаляем старые сообщения, чтобы бот не спамил при запуске
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
