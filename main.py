import os
import time
import asyncio
from aiogram import Bot, Dispatcher, types, executor
import openai
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Telegram numeric ID

if not all([BOT_TOKEN, OPENAI_API_KEY, ASSISTANT_ID, ADMIN_CHAT_ID]):
    raise RuntimeError("One or more environment variables are missing.")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# простая in-memory база потоков
user_threads = {}

async def ask_marina(user_id: int, user_text: str) -> str:
    """Отправляет текст в OpenAI Assistant и возвращает ответ"""
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

    # ждем завершения run
    while run.status not in ("completed", "failed", "cancelled"):
        await asyncio.sleep(1)
        run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    if run.status != "completed":
        return "Извините, произошла ошибка. Попробуйте еще раз."

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

    # если есть @ — шлём админу уведомление
    if "@" in message.text and message.chat.type == 'private':
        note = f"👤 Новая кандидатка @{message.from_user.username or 'без ника'}:\n{message.text}"
        await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=note)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
