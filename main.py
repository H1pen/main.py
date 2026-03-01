import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- ТВОИ ДАННЫЕ ---
TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930

# Настройка логирования для мониторинга в Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не было ошибки Port Scan Timeout) ---
async def handle(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render автоматически передает PORT, если его нет — используем 10000
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"--- Веб-сервер запущен на порту {port} ---")

# --- ЛОГИКА БОТА ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Напиши любую информацию касающийся нашей школы и я опубликую это в наш канал.")

@dp.message()
async def handle_user_post(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "скрыт"
    
    # Скрытая информация для админ-группы
    info_tag = f"\n\n🕵️ Данные отправителя:\nИмя: {user.full_name}\nЮзер: {username}\nID: {user.id}"

    # Ответ пользователю (по твоему сценарию)
    await message.answer("Спасибо)) жди свой пост на канале. Ждём дальнейших новостей от тебя.")

    try:
        # Пересылка текста
        if message.text:
            await bot.send_message(ADMIN_GROUP_ID, f"📝 Новое сообщение:\n\n{message.text}{info_tag}")
        
        # Пересылка фото
        elif message.photo:
            caption = (message.caption or "") + info_tag
            await bot.send_photo(ADMIN_GROUP_ID, message.photo[-1].file_id, caption=caption)
        
        # Пересылка видео
        elif message.video:
            caption = (message.caption or "") + info_tag
            await bot.send_video(ADMIN_GROUP_ID, message.video.file_id, caption=caption)
            
        # Остальные типы файлов
        else:
            await bot.send_message(ADMIN_GROUP_ID, f"📎 Прислали медиа/файл:{info_tag}")
            await message.copy_to(ADMIN_GROUP_ID)
            
    except Exception as e:
        logger.error(f"Ошибка при пересылке в группу: {e}")

async def main():
    logger.info("--- ЗАПУСК БОТА И СЕРВЕРА ---")
    # Запускаем бота и веб-сервер параллельно
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
