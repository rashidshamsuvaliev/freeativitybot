import os, asyncio, logging
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
import openai

load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN")            # токен Telegram‑бота
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")       # OpenAI key
ASSISTANT_ID    = os.getenv("ASSISTANT_ID")         # asst_… (промт правишь в UI)
ADMIN_CHAT_ID   = int(os.getenv("ADMIN_CHAT_ID", "0"))  # ID для уведомлений

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(bot)

# храним ID thread’ов для каждого пользователя
threads: dict[int, str] = {}

async def ask_assistant(user_id: int, text: str) -> str:
    """Отправляем текст ассистенту и возвращаем ответ"""
    th = threads.get(user_id)
    if not th:
        th = openai.beta.threads.create().id
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

@dp.message_handler(commands="start")
async def cmd_start(m: types.Message):
    await m.answer("Привет! Я Марина, HR‑ассистент студии. Что тебя заинтересовало в вакансии?")

@dp.message_handler()
async def chat(m: types.Message):
    reply = await ask_assistant(m.from_user.id, m.text)
    await m.reply(reply)

    # уведомляем менеджера, если пользователь прислал @ник
    if "@" in m.text and ADMIN_CHAT_ID:
        note = f"👤 Кандидат @{m.from_user.username or 'без_ника'}:\n{m.text}"
        await bot.send_message(ADMIN_CHAT_ID, note)

async def on_start(_):
    # 💡 ключевой момент: удаляем ВЕСЬ прежний webhook/polling
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Previous sessions dropped — polling starts")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_start)
