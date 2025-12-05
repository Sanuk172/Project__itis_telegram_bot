# Telegram бот для изучения английского с Gemini AI

Бот для практики английского языка: тесты, диалоги с проверкой грамматики, изучение слов.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env`:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
GEMINI_API_KEY=ваш_ключ_от_Google_AI_Studio
```

3. Запустите:
```bash
python bot.py
```

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/test` | Тест по грамматике (10 вопросов) |
| `/dialogue` | Диалог покупатель-продавец с проверкой грамматики |
| `/vocabulary` | Изучение слов по теме |
| `/history` | История тестов и слов |
| `/cancel` | Отмена действия |

## Получение ключей

- **Telegram**: [@BotFather](https://t.me/BotFather) → `/newbot`
- **Gemini**: [Google AI Studio](https://makersuite.google.com/app/apikey)
