import asyncio
import logging
import threading
import time
from flask import Flask
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

# --- СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ ---
app = Flask(__name__)

@app.route('/')
def home():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- НАСТРОЙКИ ---
TOKEN = "8668356633:AAHWwI4AKB1zygevOaoIuEWrodIUZiSw60U"
ADMIN_GROUP_ID = -5551460697
TARGET_CHANNEL = "@podslushanoMskool"  # Канал для выдачи прав и публикаций

# Список доверенных пользователей (без символа @)
ALLOWED_ADMINS = ["jisW69"]

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Middleware для КД (1 мин) — доверенные пользователи не ждут
class SlowModeMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_msg_times = {}

    async def __call__(self, handler, event: types.Message, data):
        if not event.from_user:
            return await handler(event, data)

        username = (event.from_user.username or "").lower()
        if username in [u.lower() for u in ALLOWED_ADMINS]:
            return await handler(event, data)

        uid = event.from_user.id
        now = time.time()
        if uid in self.last_msg_times and now - self.last_msg_times[uid] < 60:
            remaining = int(60 - (now - self.last_msg_times[uid]))
            return await event.answer(f"⏳ Подожди {remaining} сек.")
        self.last_msg_times[uid] = now
        return await handler(event, data)

dp.message.middleware(SlowModeMiddleware())

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Присылай пост!")

# Команда выдачи прав администратора
@dp.message(Command("get_admin"))
async def grant_channel_admin(m: types.Message):
    username = (m.from_user.username or "").lower()
    if username not in [u.lower() for u in ALLOWED_ADMINS]:
        return await m.answer("⛔ У вас нет доступа к этой команде.")

    try:
        # Проверяем собственные права бота в канале
        bot_info = await bot.get_me()
        bot_member = await bot.get_chat_member(TARGET_CHANNEL, bot_info.id)

        # Проверка: является ли бот админом и включено ли право назначать администраторов
        if not getattr(bot_member, "can_promote_members", False):
            return await m.answer(
                "❌ У меня нет прав назначать администраторов в канале "
                f"{TARGET_CHANNEL}.\nВ настройках прав бота в канале включите пункт "
                "«Добавление администраторов» (Add Admins)."
            )

        # Выдаем права пользователю
        await bot.promote_chat_member(
            chat_id=TARGET_CHANNEL,
            user_id=m.from_user.id,
            can_manage_chat=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_delete_messages=True,
            can_invite_users=True
        )
        await m.answer(f"✅ Вам успешно выданы права администратора в канале {TARGET_CHANNEL}!")

    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "not enough rights" in error_msg or "chat_admin_required" in error_msg:
            await m.answer(f"❌ У меня недостаточно прав в канале {TARGET_CHANNEL}.")
        elif "user not found" in error_msg:
            await m.answer("❌ Сначала подпишитесь на канал или откройте его, затем повторите команду.")
        else:
            await m.answer(f"❌ Ошибка Telegram: {e.message}")
    except Exception as e:
        logging.error(f"Ошибка при выдаче прав: {e}")
        await m.answer(f"❌ Произошла непредвиденная ошибка: {e}")

@dp.message()
async def handle(m: types.Message):
    prefix = "... пишет-\n\n"
    footer = "\n\n@PodslushanoMYschoolBot"
    user_info = f"\n\n👤 От: {m.from_user.full_name} (@{m.from_user.username or 'скрыто'})"

    try:
        if m.text:
            text = f"{prefix}{m.text}{footer}"
            await bot.send_message(TARGET_CHANNEL, text)
            await bot.send_message(ADMIN_GROUP_ID, text + user_info)
        elif m.photo:
            cap = f"{prefix}{m.caption or ''}{footer}"
            await bot.send_photo(TARGET_CHANNEL, m.photo[-1].file_id, caption=cap)
            await bot.send_photo(ADMIN_GROUP_ID, m.photo[-1].file_id, caption=cap + user_info)
        elif m.video:
            cap = f"{prefix}{m.caption or ''}{footer}"
            await bot.send_video(TARGET_CHANNEL, m.video.file_id, caption=cap)
            await bot.send_video(ADMIN_GROUP_ID, m.video.file_id, caption=cap + user_info)

        await m.answer("✅ Отправлено!")
    except Exception as e:
        logging.error(e)
        await m.answer("❌ Ошибка при отправке. Проверьте права бота в канале и группе.")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
