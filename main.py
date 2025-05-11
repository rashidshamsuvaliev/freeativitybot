import os, asyncio, logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import openai
from dotenv import load_dotenv

load_dotenv()

# ----- ENV -----
BOT_TOKEN       = os.getenv("BOT_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID    = os.getenv("ASSISTANT_ID")
ADMIN_CHAT_ID   = int(os.getenv("ADMIN_CHAT_ID", "0"))
WEBHOOK_HOST    = os.getenv("WEBHOOK_HOST")            # https://freeativitybot.onrender.com
WEBHOOK_PATH    = "/webhook"
WEBHOOK_URL     = WEBHOOK_HOST + WEBHOOK_PATH
PORT            = int(os.getenv("PORT", "10000"))      # Render сам отдаст PORT

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(bot)
threads = {}

# ----- GPT ASSISTANT -----
async def ask(user_id: int, text: str) -> str:
    th = threads.get(user_id) or openai.beta.threads.create().id
    threads[user_id] = th
    run = openai.beta.threads.runs.create(
        thread_id=th,
        assistant_id=ASSISTANT_ID,
        messages=[{"role": "user", "content": text}]
    )
    while run.status not in ("completed", "failed", "cancelled"):
        await asyncio.sleep(1)
        run = openai.beta.threads.runs.retrieve(th, run.id)
    msgs = openai.beta.threads.messages.list(th)
    return msgs.data[0].content[0].text.value

# ----- HANDLERS -----
@dp.message_handler(commands="start")
async def cmd_start(m: types.Message):
    await m.answer("Привет! Я Марина, HR‑ассистент студии. Что тебя заинтересовало в вакансии?")

@dp.message_handler()
async def chat(m: types.Message):
    reply = await ask(m.from_user.id, m.text)
    await m.reply(reply)
    if "@" in m.text and ADMIN_CHAT_ID:
        note = f"👤 Кандидат @{m.from_user.username or 'без_ника'}:\n{m.text}"
        await bot.send_message(ADMIN_CHAT_ID, note)

# ----- WEBHOOK SERVER -----
async def on_startup(_: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook set -> %s", WEBHOOK_URL)

async def on_shutdown(_: web.Application):
    await bot.delete_webhook()

def create_app():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, on_startup=on_startup, on_shutdown=on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
