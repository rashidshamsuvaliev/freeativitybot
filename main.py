import os
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
import openai

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_threads = {}

async def ask_marina(user_id: int, user_text: str) -> str:
    thread_id = user_threads.get(user_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[user_id] = thread_id

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        messages=[{"role": "user", "content": user_text}]
    )

    while run.status not in ("completed", "failed", "cancelled"):
        await asyncio.sleep(1)
        run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    if run.status != "completed":
        return "Извините, произошла ошибка. Попробуйте ещё раз."

    messages = openai.beta.threads.messages.list(thread_id)
    reply = messages.data[0].content[0].text.value
    return reply

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я Марина, HR-ассистент студии. Расскажи, что тебя заинтересовало в нашей вакансии?")

@dp.message_handler()
async def chat(message: types.Message):
    reply = await ask_marina(message.from_user.id, message.text)
    await message.reply(reply)

    if "@" in message.text and message.chat.type == 'private':
        note = f"👤 Новая кандидатка @{message.from_user.username or 'без ника'}:\n{message.text}"
        await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=note)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
