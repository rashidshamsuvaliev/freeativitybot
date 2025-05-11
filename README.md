
# Freeativity HR Telegram Bot

Telegram HR-бот «Марина» — работает на GPT (Assistants API) и aiogram.

## Быстрый старт локально

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # впишите свои ключи
python main.py
```

## Переменные окружения

| key | значение |
|-----|-----------|
| BOT_TOKEN | токен вашего Telegram-бота |
| OPENAI_API_KEY | ключ OpenAI |
| ASSISTANT_ID | ID ассистента (`asst_...`) из интерфейса OpenAI |
| ADMIN_CHAT_ID | Telegram ID, куда слать лидов |
