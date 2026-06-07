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
- complaints
- admin moderation
- user ban and unban
- PostgreSQL storage through SQLAlchemy async
- Alembic migrations

## Stack

- Python 3.12
- aiogram 3
- PostgreSQL
- SQLAlchemy 2
- asyncpg
- Alembic
- pydantic-settings

## Local start

1. Create `.env` from `.env.example`.
2. Install dependencies from `deps.txt` or create `requirements.txt` with the same content.
3. Start PostgreSQL.
4. Apply migrations or enable `CREATE_SCHEMA_ON_START=true`.
5. Run:

```bash
python run.py
```

## Migrations

```bash
alembic upgrade head
```

For production, prefer migrations and set:

```env
CREATE_SCHEMA_ON_START=false
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

## User commands

- `/start` — start bot and create profile
- `/cancel` — cancel current action
- `Профиль` — set city and district
- `Нужна помощь` — create request
- `Заявки рядом` — show local requests
- `Хочу помочь` — show local requests
- `Мои заявки` — show own requests
- `Правила безопасности` — safety rules

## Admin commands

- `/admin` — admin dashboard
- `/moderation` — requests waiting for moderation
- `/complaints` — new complaints
- `/user telegram_id` — user details
- `/ban telegram_id` — ban user
- `/unban telegram_id` — unban user

## Production notes

The repository is public, so never commit real secrets. Use hosting environment variables for the bot token, database URL and admin ids.
