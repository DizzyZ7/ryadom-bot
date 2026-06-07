# Ryadom Bot

Telegram bot for local help requests and neighborhood assistance.

## MVP

The first version supports:

- Telegram registration by user id
- profile city and district
- creating help requests
- request categories
- published requests feed
- user requests list
- helper offers
- basic moderation callbacks
- PostgreSQL storage through SQLAlchemy async

## Stack

- Python 3.12
- aiogram 3
- PostgreSQL
- SQLAlchemy 2
- asyncpg
- pydantic-settings

## Local start

1. Create `.env` from `.env.example`.
2. Install dependencies from `deps.txt`.
3. Start PostgreSQL.
4. Run:

```bash
python -m app.main
```

## Environment

Required variables:

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
ADMIN_IDS=123456789
ENVIRONMENT=local
LOG_LEVEL=INFO
AUTO_PUBLISH_WITHOUT_ADMINS=true
CREATE_SCHEMA_ON_START=true
```

## Production notes

The repository is public, so never commit real secrets. Use hosting environment variables for the bot token, database URL and admin ids.
