import asyncio
import datetime
import logging
import sqlite3
import threading
import time
from flask import Flask
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ ---
app = Flask(__name__)

@app.route('/')
def home():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- НАСТРОЙКИ ---
TOKEN = "8668356633:AAHWwI4AKB1zygevOaoIuEWrodIUZiSw60U"
CHANNEL_ID = -1003742221408

# Группы для отслеживания сообщений
TRACKED_GROUPS = [-1003670917930, -5551460697]

# Единственный администратор с правом публикации
SUPER_ADMIN = "jisW69"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

waiting_for_channel_post = set()

# Кнопка удаления ТОЛЬКО для личных сообщений админа
def get_admin_delete_kb(channel_msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить этот пост из канала", callback_data=f"del_msg:{channel_msg_id}")]
        ]
    )

# --- БАЗА ДАННЫХ ДЛЯ ХРАНЕНИЯ СООБЩЕНИЙ ---
def init_db():
    with sqlite3.connect("chat_history.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                chat_title TEXT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                text TEXT,
                date_str TEXT
            )
        """)
        conn.commit()

init_db()

def save_message(chat_id: int, chat_title: str, user_id: int, username: str, full_name: str, text: str, date_str: str):
    with sqlite3.connect("chat_history.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (chat_id, chat_title, user_id, username, full_name, text, date_str)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, chat_title, user_id, username, full_name, text, date_str))
        conn.commit()

def get_user_messages(username: str, limit: int = 30):
    clean_username = username.lstrip("@").lower()
    with sqlite3.connect("chat_history.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_title, text, date_str 
            FROM messages 
            WHERE LOWER(username) = ? 
            ORDER BY id DESC 
            LIMIT ?
        """, (clean_username, limit))
        return cursor.fetchall()

# --- КУЛДАУН (1 МИН) ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ ---
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

# --- УДАЛЕНИЕ ПОСТА ПО КНОПКЕ В ЛС ---
@dp.callback_query(F.data.startswith("del_msg:"))
async def delete_channel_post(call: CallbackQuery):
    sender = (call.from_user.username or "").lower()
    if sender != SUPER_ADMIN.lower():
        return await call.answer("⛔ Доступ запрещен.", show_alert=True)

    msg_id = int(call.data.split(":")[1])
    try:
        await bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
        await call.message.edit_text("🗑 Пост полностью удален из канала.")
        await call.answer()
    except Exception as e:
        await call.answer(f"❌ Не удалось удалить: {e}", show_alert=True)

# --- ПУБЛИКАЦИЯ В КАНАЛ (100% АНОНИМНО) ---
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

    # Быстрый текстовый пост: /post Привет!
    if command.args:
        try:
            sent = await bot.send_message(chat_id=CHANNEL_ID, text=command.args)
            return await m.answer(
                "✅ Пост опубликован в канале от лица канала!",
                reply_markup=get_admin_delete_kb(sent.message_id)
            )
        except Exception as e:
            return await m.answer(f"❌ Ошибка публикации: {e}")

    # Режим ожидания любого медиа/сообщения
    waiting_for_channel_post.add(m.from_user.id)
    await m.answer(
        "📢 <b>Режим анонимной публикации:</b>\n\n"
        "Пришлите текст, фото, видео или опрос. Сообщение скопируется в канал без подписей, а в админские группы ничего отправлено не будет.\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML"
    )

# --- ПОИСК СООБЩЕНИЙ ПОЛЬЗОВАТЕЛЕЙ ИЗ ДВУХ ГРУПП ---
@dp.message(F.chat.type == "private", Command("find"))
async def search_user_history(m: types.Message, command: CommandObject):
    sender = (m.from_user.username or "").lower()
    if sender != SUPER_ADMIN.lower():
        return await m.answer("⛔ Доступ разрешен только администратору.")

    if not command.args:
        return await m.answer("Использование: `/find @username`", parse_mode="Markdown")

    target_user = command.args.strip()
    records = get_user_messages(target_user)

    if not records:
        return await m.answer(f"Сообщений от {target_user} в группах пока не найдено.")

    response = [f"📋 <b>Последние сообщения от {target_user}:</b>\n"]
    for chat_title, text, date_str in records:
        response.append(
            f"📍 <b>Чат:</b> {chat_title}\n"
            f"🕒 <b>Время:</b> {date_str}\n"
            f"💬 <b>Текст:</b> {text}\n"
            f"{'—'*20}"
        )

    full_text = "\n".join(response)
    for x in range(0, len(full_text), 4000):
        await m.answer(full_text[x:x+4000], parse_mode="HTML")

# --- СБОР СООБЩЕНИЙ ИЗ ГРУПП ---
@dp.message(F.chat.id.in_(TRACKED_GROUPS))
async def log_group_messages(m: types.Message):
    if not m.from_user:
        return

    content = m.text or m.caption or "[Файл/Медиа без текста]"
    msg_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")

    save_message(
        chat_id=m.chat.id,
        chat_title=m.chat.title or "Без названия",
        user_id=m.from_user.id,
        username=m.from_user.username or "",
        full_name=m.from_user.full_name,
        text=content,
        date_str=msg_time
    )

# --- ПРЕДЛОЖКА ДЛЯ ОБЫЧНЫХ ПОДПИСЧИКОВ ---
@dp.message(F.chat.type == "private", Command("start"))
async def start(m: types.Message):
    await m.answer("Присылай пост!")

@dp.message(F.chat.type == "private")
async def handle_private(m: types.Message):
    # 1. Анонимный пост от @jisW69
    if m.from_user.id in waiting_for_channel_post:
        waiting_for_channel_post.discard(m.from_user.id)
        try:
            # copy_message копирует контент без пометки "Переслано от кого-то"
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

    # 2. Обычные посты подписчиков (идут в канал и группу с их данными)
    prefix = "... пишет-\n\n"
    footer = "\n\n@PodslushanoMYschoolBot"
    user_info = f"\n\n👤 От: {m.from_user.full_name} (@{m.from_user.username or 'скрыто'})"

    try:
        if m.text:
            text = f"{prefix}{m.text}{footer}"
            await bot.send_message(CHANNEL_ID, text)
            await bot.send_message(TRACKED_GROUPS[1], text + user_info)
        elif m.photo:
            cap = f"{prefix}{m.caption or ''}{footer}"
            await bot.send_photo(CHANNEL_ID, m.photo[-1].file_id, caption=cap)
            await bot.send_photo(TRACKED_GROUPS[1], m.photo[-1].file_id, caption=cap + user_info)
        elif m.video:
            cap = f"{prefix}{m.caption or ''}{footer}"
            await bot.send_video(CHANNEL_ID, m.video.file_id, caption=cap)
            await bot.send_video(TRACKED_GROUPS[1], m.video.file_id, caption=cap + user_info)

        await m.answer("✅ Отправлено!")
    except Exception as e:
        logging.error(e)
        await m.answer("❌ Ошибка при отправке. Проверьте права бота.")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
