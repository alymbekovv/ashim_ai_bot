import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiohttp
import os
from aiohttp import web

# === 🔧 Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === 🗄️ База данных ===
def init_db():
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        message TEXT
    )
    """)
    conn.commit()
    conn.close()

# === 💬 Меню ===
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🛍 Проверить заказ")
    kb.button(text="⭐ Оставить отзыв")
    kb.button(text="📦 Отследить посылку")
    kb.button(text="💬 Поддержка")
    kb.button(text="🧺 Советы по уходу")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# === 🧠 Интеллект (Groq API) ===
async def ask_groq(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                 (
    "Ты — весёлый, дружелюбный и немного остроумный ассистент бренда ASHIM 👕. "
    "Ты знаешь всё о моде, одежде, стиле и уходе за вещами. "
    "Ты также помогаешь покупателям ASHIM на маркетплейсах (Wildberries) "
    "с вопросами про заказы, доставку, отзывы, возвраты и поддержку. "
    "Отвечай живо, позитивно и с лёгким юмором, как хороший консультант в магазине, "
    "но не переходи границы — сохраняй уважительный и профессиональный тон. "
    "Если вопрос совсем не по теме, отвечай мягко, например: "
    "'Ха, интересный вопрос! Но я эксперт по одежде и покупкам ASHIM 😊'"
)
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 512
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print("Groq API error:", resp.status, text)
                    return "⚠️ Ошибка связи с интеллектом (Groq API). Проверьте ключ или попробуйте позже."

                res = await resp.json()
                return res["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("Groq request failed:", e)
        return "⚠️ Ошибка интеллекта. Попробуйте позже."


# === 🚀 Команда /start ===
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я — ASHIM Assistant. Помогаю с заказами, отзывами и клиентами на Wildberries.",
        reply_markup=main_menu()
    )

# === 💡 Обработка всех сообщений ===
@dp.message(F.text)
async def handle_message(message: types.Message):
    user_text = message.text.strip()

    # сохраняем сообщение в базу
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (user_id, username, message) VALUES (?, ?, ?)",
                (message.from_user.id, message.from_user.username, user_text))
    conn.commit()
    conn.close()

    reply = await ask_groq(user_text)
    await message.answer(reply)


# === 🌐 Web-сервер для Render ===
async def handle_web(request):
    return web.Response(text="✅ ASHIM Assistant работает!")

async def start():
    init_db()

    # Запускаем Telegram-бота
    asyncio.create_task(dp.start_polling(bot))

    # Фейковый web-сервер, чтобы Render не ругался
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

    print("✅ Bot and web server running on port 10000")

    # держим процесс живым
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(start())
