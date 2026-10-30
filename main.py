import asyncio
import logging
import re
import threading
import time
from flask import Flask
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (RENDER / REPLIT) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- НАСТРОЙКИ ---
TOKEN = "8668356633:AAHWwI4AKB1zygevOaoIuEWrodIUZiSw60U"
CHANNEL_ID = -1003742221408
ADMIN_GROUP_ID = -5551460697

# Группы, где работает удаление через ответ (reply)
MANAGED_GROUPS = [-1003670917930, -5551460697]

# Главный администратор с полным доступом
SUPER_ADMIN = "jisW69"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

waiting_for_channel_post = set()

# Кнопка удаления для личных сообщений админа после публикации
def get_admin_delete_kb(channel_msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить этот пост из канала", callback_data=f"del_msg:{channel_msg_id}")]
        ]
    )

# --- КУЛДАУН (1 МИН) ДЛЯ ПРЕДЛОЖКИ ---
class SlowModeMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_msg_times = {}

    async def __call__(self, handler, event: types.Message, data):
        if not event.from_user or event.chat.type != "private":
            return await handler(event, data)

        username = (event.from_user.username or "").lower()
        if username == SUPER_ADMIN.lower():
            return await handler(event, data)

        uid = event.from_user.id
        now = time.time()
        if uid in self.last_msg_times and now - self.last_msg_times[uid] < 60:
            remaining = int(60 - (now - self.last_msg_times[uid]))
            return await event.answer(f"⏳ Подожди {remaining} сек.")
        self.last_msg_times[uid] = now
        return await handler(event, data)

dp.message.middleware(SlowModeMiddleware())

# --- УДАЛЕНИЕ ПОСТА ПО НАЖАТИЮ КНОПКИ В ЛС ---
@dp.callback_query(F.data.startswith("del_msg:"))
async def delete_channel_post_callback(call: CallbackQuery):
    sender = (call.from_user.username or "").lower()
    if sender != SUPER_ADMIN.lower():
        return await call.answer("⛔ Доступ разрешен только администратору.", show_alert=True)

    msg_id = int(call.data.split(":")[1])
    try:
        await bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
        await call.message.edit_text("🗑 Пост полностью удален из канала.")
        await call.answer()
    except Exception as e:
        await call.answer(f"❌ Ошибка удаления: {e}", show_alert=True)

# --- УДАЛЕНИЕ СООБЩЕНИЙ ПО ССЫЛКЕ ИЛИ ID (В ЛС) ---
@dp.message(F.chat.type == "private", Command("del"))
async def delete_any_message(m: types.Message, command: CommandObject):
    sender = (m.from_user.username or "").lower()
    if sender != SUPER_ADMIN.lower():
        return await m.answer("⛔ Доступ разрешен только администратору.")

    if not command.args:
        return await m.answer(
            "Укажите номер сообщения или ссылку на него.\n\n"
            "Примеры:\n"
            "• `/del 45` (удалит сообщение №45 из канала)\n"
            "• `/del https://t.me/podslushanoMskool/45`\n"
            "• `/del https://t.me/c/3742221408/45`",
            parse_mode="Markdown"
        )

    arg = command.args.strip()
    target_chat = CHANNEL_ID
    msg_id = None

    match_private_link = re.search(r"t\.me/c/(\d+)/(\d+)$", arg)
    match_public_link = re.search(r"/(\d+)$", arg)

    if match_private_link:
        target_chat = int(f"-100{match_private_link.group(1)}")
        msg_id = int(match_private_link.group(2))
    elif match_public_link:
        msg_id = int(match_public_link.group(1))
    elif arg.isdigit():
        msg_id = int(arg)
    else:
        return await m.answer("❌ Не удалось распознать ID сообщения. Проверьте ссылку.")

    try:
        await bot.delete_message(chat_id=target_chat, message_id=msg_id)
        await m.answer(f"🗑 Сообщение #{msg_id} успешно удалено!")
    except Exception as e:
        error_text = str(e).lower()
        if "message to delete not found" in error_text:
            await m.answer("❌ Сообщение не найдено (возможно, оно уже удалено).")
        elif "not enough rights" in error_text:
            await m.answer("❌ У бота нет прав на удаление сообщений в этом чате.")
        else:
            await m.answer(f"❌ Ошибка Telegram: {e}")

# --- БЫСТРОЕ УДАЛЕНИЕ В ГРУППАХ ЧЕРЕЗ REPLY ---
@dp.message(F.chat.id.in_(MANAGED_GROUPS), Command("del"))
async def delete_in_group_by_reply(m: types.Message):
    sender = (m.from_user.username or "").lower()
    if sender != SUPER_ADMIN.lower():
        return

    if not m.reply_to_message:
        return await m.reply("Ответьте этой командой на сообщение, которое нужно удалить.")

    try:
        await bot.delete_message(chat_id=m.chat.id, message_id=m.reply_to_message.message_id)
        await m.delete()
    except Exception as e:
        await m.reply(f"❌ Не удалось удалить: {e}")

# --- АНОНИМНАЯ ПУБЛИКАЦИЯ В КАНАЛ ДЛЯ @jisW69 ---
@dp.message(F.chat.type == "private", Command("cancel"))
async def cancel_post(m: types.Message):
    if m.from_user.id in waiting_for_channel_post:
        waiting_for_channel_post.discard(m.from_user.id)
        await m.answer("❌ Публикация отменена.")
    else:
        await m.answer("Нет активного режима публикации.")

@dp.message(F.chat.type == "private", Command("post"))
async def post_command(m: types.Message, command: CommandObject):
    sender = (m.from_user.username or "").lower()
    if sender != SUPER_ADMIN.lower():
        return await m.answer("⛔ Доступ разрешен только администратору.")

    if command.args:
        try:
            sent = await bot.send_message(chat_id=CHANNEL_ID, text=command.args)
            return await m.answer(
                "✅ Пост опубликован в канале от лица канала!",
                reply_markup=get_admin_delete_kb(sent.message_id)
            )
        except Exception as e:
            return await m.answer(f"❌ Ошибка публикации: {e}")

    waiting_for_channel_post.add(m.from_user.id)
    await m.answer(
        "📢 <b>Режим анонимной публикации:</b>\n\n"
        "Отправьте текст, фото, видео или опрос — бот скопирует его в канал от лица канала без меток автора.\n\n"
        "Для отмены отправьте /cancel.",
        parse_mode="HTML"
    )

# --- ПРЕДЛОЖКА И ОБРАБОТЧИК ЛС ---
@dp.message(F.chat.type == "private", Command("start"))
async def start(m: types.Message):
    await m.answer("Присылай пост!")

@dp.message(F.chat.type == "private")
async def handle_private(m: types.Message):
    # Анонимный пост от @jisW69
    if m.from_user.id in waiting_for_channel_post:
        waiting_for_channel_post.discard(m.from_user.id)
        try:
            sent = await bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=m.chat.id,
                message_id=m.message_id
            )
            return await m.answer(
                "✅ Пост опубликован в канале от лица канала!",
                reply_markup=get_admin_delete_kb(sent.message_id)
            )
        except Exception as e:
            logging.error(f"Ошибка публикации: {e}")
            return await m.answer(f"❌ Ошибка публикации: {e}")

    # Обычная предложка подписчиков
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
        await m.answer("❌ Ошибка при отправке. Проверьте права бота.")

# --- ЗАПУСК ---
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
