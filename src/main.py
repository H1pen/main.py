import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# Твои данные
TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройка логирования, чтобы видеть ошибки в консоли Render
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Напиши любую информацию касающийся нашей школы и я опубликую это в наш канал.")

@dp.message()
async def handle_user_post(message: types.Message):
    # Информация об отправителе для "разоблачения" в админ-группе
    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет юзернейма"
    info_tag = f"\n\n—\n👤 Отправитель: {user.full_name} ({username})\n🆔 ID: {user.id}"

    # Ответ пользователю (как ты просил по сценарию)
    await message.answer("Спасибо)) жди свой пост на канале. Ждём дальнейших новостей от тебя.")

    # Пересылка в твою закрытую группу
    try:
        if message.text:
            await bot.send_message(ADMIN_GROUP_ID, f"📢 Новое сообщение:\n\n{message.text}{info_tag}", parse_mode="Markdown")
        
        elif message.photo:
            caption = (message.caption or "") + info_tag
            await bot.send_photo(ADMIN_GROUP_ID, message.photo[-1].file_id, caption=caption)
        
        elif message.video:
            caption = (message.caption or "") + info_tag
            await bot.send_video(ADMIN_GROUP_ID, message.video.file_id, caption=caption)
            
        elif message.animation: # Для гифок
            caption = (message.caption or "") + info_tag
            await bot.send_animation(ADMIN_GROUP_ID, message.animation.file_id, caption=caption)
            
        elif message.document:
            caption = (message.caption or "") + info_tag
            await bot.send_document(ADMIN_GROUP_ID, message.document.file_id, caption=caption)
            
        else:
            # Для прочих медиа (голосовые, стикеры и т.д.)
            await bot.send_message(ADMIN_GROUP_ID, f"📎 Прислали файл другого типа (см. ниже):{info_tag}")
            await message.copy_to(ADMIN_GROUP_ID)
            
    except Exception as e:
        logging.error(f"Ошибка при пересылке: {e}")

async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
