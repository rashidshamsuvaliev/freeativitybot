import os
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
import openai

load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID    = os.getenv("ASSISTANT_ID")
ADMIN_CHAT_ID   = os.getenv("ADMIN_CHAT_ID")   # число, без «@»

if not all([BOT_TOKEN, OPENAI_API_KEY, ASSISTANT_ID, ADMIN_CHAT_ID]):
    raise RuntimeError("Missing env vars: BOT_TOKEN / OPENAI_API_KEY / ASSISTANT_ID / ADMIN_CHAT_ID")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(bot)

# храним ID thread’ов для каждого пользователя
threads: dict[int, str] = {}

async def ask_marina(user_id: int, text: str) -> str:
    """Отправляем текст ассистенту и возвращаем его ответ"""
    thread_id = threads.get(user_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        threads[user_id] = thread_id

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        messages=[{"role": "user", "content": text}]
    )

    # ждём завершения Run
    while run.status not in ("completed", "failed", "cancelled"):
        await asyncio.sleep(1)
        run = openai.beta.threads.runs.retrieve(thread_id, run.id)

    if run.status != "completed":
        return "Извините, произошла ошибка. Попробуйте ещё раз."

    msgs = openai.beta.threads.messages.list(thread_id)
    return msgs.data[0].content[0].text.value


@dp.message_handler(commands="start")
async def cmd_start(m: types.Message):
    await m.answer("Привет! Я Марина, HR‑ассистент студии. Расскажи, что тебя заинтересовало в вакансии?")

@dp.message_handler()
async def chat(m: types.Message):
    reply = await ask_marina(m.from_user.id, m.text)
    await m.reply(reply)

    if "@" in m.text and m.chat.type == 'private':
        note = f"👤 <b>Новая кандидатка</b> @{m.from_user.username or 'без ника'}:\n{m.text}"
        await bot.send_message(int(ADMIN_CHAT_ID), note)


# ----  ключевой фикс: очищаем старый webhook/polling перед стартом ----
async def on_startup(dp):
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook cleared, polling starts…")

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
