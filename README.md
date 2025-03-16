# Custos AI Telegram Bot

Telegram-бот для проведения customer development интервью с использованием искусственного интеллекта.

## Возможности

- 🎯 Создание цифровых респондентов по заданному портрету
- 🗣 Проведение интервью с реалистичной симуляцией "трудных" респондентов
- 📊 Анализ ответов на соответствие гипотезам
- 🔍 Детекция bias в ответах
- 📈 Автоматическая визуализация результатов

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/custos-ai-bot.git
cd custos-ai-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте необходимые переменные окружения:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
SITE_URL=your_site_url
SITE_NAME=your_site_name
```

## Использование

1. Запустите бота:
```bash
python Bot_Core/main.py
```

2. В Telegram найдите бота и отправьте команду `/start`

3. Следуйте инструкциям бота для:
   - Создания нового респондента
   - Проведения интервью
   - Просмотра аналитики

## Структура проекта

```
📁 Bot_Core/
├── 📄 main.py              # Точка входа (запуск бота)
├── 📁 responders/          # Генерация респондентов
│   └── 📄 generator.py     # Промпты для LLM + валидация
├── 📁 validation/          # Проверка профилей и ответов
│   ├── 📄 validator.py     # Логика Validator-агента
│   └── 📄 bias_hunter.py   # Детекция bias
├── 📁 analytics/           # Анализ ответов
│   ├── 📄 nlp_processor.py # Кластеризация (KeyBERT)
│   └── 📄 reporter.py      # Генерация отчетов
├── 📁 data/                # Хранение сессий
│   └── 📄 sessions.db      # SQLite с данными интервью
└── 📁 utils/               # Вспомогательные функции
    └── 📄 plotter.py       # Визуализация (Plotly)
```

## Технологии

- Python 3.8+
- python-telegram-bot 20.7
- OpenRouter API (DeepSeek model)
- KeyBERT для NLP-анализа
- SQLAlchemy для работы с БД
- Plotly для визуализации

## Лицензия

MIT

## Авторы

- Ваше имя
- Контакты для связи # cust_dev_tg_bot
