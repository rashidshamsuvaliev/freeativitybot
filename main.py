
import os, time, asyncio
from aiogram import Bot, Dispatcher, types, executor
import openai
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # numeric string

if not all([BOT_TOKEN, OPENAI_API_KEY, ASSISTANT_ID, ADMIN_CHAT_ID]):
    raise RuntimeError("One or more environment variables are missing.")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# simple in-memory thread storage per user
user_threads = {}

async def ask_marina(user_id: int, user_text: str) -> str:
    """Send user_text to OpenAI Assistant and return reply"""
    # Create new thread if first message
    thread_id = user_threads.get(user_id)
    if thread_id is None:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[user_id] = thread_id

    # Start run
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        messages=[{"role": "user", "content": user_text}]
    )

    # Poll until done
    while run.status not in ("completed", "failed", "cancelled"):
        await asyncio.sleep(1)
        run = openai.beta.threads.runs.retrieve(thread_id, run.id)

    if run.status != "completed":
        return "Извините, произошла ошибка. Попробуйте ещё раз."

    messages = openai.beta.threads.messages.list(thread_id)
    # последний ответ ассистента первый в списке
    reply = messages.data[0].content[0].text.value
    return reply

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я Марина, HR-ассистент студии. Расскажи, что тебя заинтересовало в нашей вакансии?")

@dp.message_handler()
async def chat(message: types.Message):
    reply = await ask_marina(message.from_user.id, message.text)
    await message.reply(reply)

    # если сообщение содержит @ - считаем, что это ник кандидата -> шлём менеджеру
    if "@" in message.text and message.chat.type == 'private':
        note = f"Новая кандидатка от @{message.from_user.username}:\n{message.text}"
        await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=note)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
