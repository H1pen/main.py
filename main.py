import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command

TOKEN = "8668356633:AAE29U5g3PcT8r8eYOM_zhmXWtRa_QVQvQo"
ADMIN_GROUP_ID = -1003670917930

# --- Middleware для антиспама и мута ---
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self):
        self.users = {}  # Храним данные: {user_id: {'last_time': 0, 'count': 0, 'mute_until': 0}}

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()

        # Инициализируем данные пользователя, если их нет
        if user_id not in self.users:
            self.users[user_id] = {'last_time': 0, 'count': 0, 'mute_until': 0}

        user_data = self.users[user_id]

        # 1. Проверка на активный мут
        if now < user_data['mute_until']:
            remaining = int(user_data['mute_until'] - now)
            # Отвечаем только один раз, чтобы не спамить в ответ на спам
            if user_data['count'] == 4:
                user_data['count'] += 1 # Увеличим, чтобы больше не слать это сообщ.
                return await event.answer(f"🚫 Ты заблокирован за спам. Подожди еще {remaining} сек.")
            return # Просто игнорируем последующие сообщения

        # 2. Сброс счетчика, если прошло много времени (например, минута тишины)
        if now - user_data['last_time'] > 60:
            user_data['count'] = 0

        # 3. Логика антиспама (1 сообщение в минуту)
        if now - user_data['last_time'] < 60:
            user_data['count'] += 1
            user_data['last_time'] = now

            if user_data['count'] >= 4:
                user_data['mute_until'] = now + 300  # Мут на 5 минут (300 сек)
                return await event.answer("⚠️ Ты отправляешь сообщения слишком часто. Мут на 5 минут!")
            
            # Если это 2-е или 3-е сообщение за минуту
            wait_time = int(60 - (now - user_data['last_time']))
            return await event.answer(f"⏳ Не части. Подожди {wait_time} сек. (Предупреждение {user_data['count']}/4)")

        # Если всё хорошо, обновляем время и пропускаем к обработчику
        user_data['last_time'] = now
        user_data['count'] = 1
        return await handler(event, data)

# --- Настройка бота ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(ThrottlingMiddleware())

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Напиши любую информацию о школе, и я опубликую в канал.")

@dp.message()
async def handle_user_post(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет юзернейма"
    info_tag = f"\n\n—\n👤 Отправитель: {user.full_name} ({username})\n🆔 ID: {user.id}"

    await message.answer("Спасибо! Жди свой пост в канале.")

    try:
        # Универсальная отправка копии сообщения
        await message.send_copy(ADMIN_GROUP_ID)
        await bot.send_message(ADMIN_GROUP_ID, f"☝️ Выше сообщение от:{info_tag}")
    except Exception as e:
        logging.error(f"Ошибка при пересылке: {e}")

async def main():
    print("Бот запущен с защитой от спама!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
