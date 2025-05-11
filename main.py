import os, asyncio, logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv
import openai

load_dotenv()

# --- ENV ---
BOT_TOKEN       = os.getenv("BOT_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID    = os.getenv("ASSISTANT_ID")
ADMIN_CHAT_ID   = int(os.getenv("ADMIN_CHAT_ID", "0"))
WEBHOOK_HOST    = os.getenv("WEBHOOK_HOST")  # https://freeativitybot.onrender.com
WEBHOOK_PATH    = "/webhook"
WEBHOOK_URL     = WEBHOOK_HOST + WEBHOOK_PATH
PORT            = int(os.getenv("PORT", "10000"))

# --- OpenAI client with header v2 ---
client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    default_headers={"OpenAI-Beta": "assistants=v2"},
)

# --- Aiogram ---
logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
threads: dict[int, str] = {}

# --- GPT Assistant Logic ---
async def ask(user_id: int, text: str) -> str:
    thread_id = threads.get(user_id)
    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id
        threads[user_id] = thread_id

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=text
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while run.status not in ("completed", "failed", "cancelled"):
        await asyncio.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data[0].content[0].text.value

# --- Handlers ---
@dp.message_handler(commands="start")
async def cmd_start(m: types.Message):
    await m.answer("Привет, я Марина — HR-ассистент. Что тебя заинтересовало в вакансии?")

@dp.message_handler()
async def chat(m: types.Message):
    reply = await ask(m.from_user.id, m.text)
    await m.reply(reply)

    if "@" in m.text and ADMIN_CHAT_ID:
        note = f"👤 @{m.from_user.username or 'без_ника'}\n{m.text}"
        await bot.send_message(ADMIN_CHAT_ID, note)

# --- Webhook Setup ---
async def on_startup(dp):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set -> {WEBHOOK_URL}")

async def on_shutdown(dp):
    await bot.delete_webhook()

# --- Start Bot ---
if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host="0.0.0.0",
        port=PORT,
        skip_updates=True,
    )
