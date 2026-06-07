# Ryadom Bot

Telegram bot for local help requests and neighborhood assistance.

## MVP

The first version supports:

- Telegram registration by user id
- profile city and district
- location catalog with city and district selection
- admin-managed city and district dictionary
- creating help requests
- request categories
- request urgency levels
- urgency-based request feed sorting
- published requests feed
- user requests list
- request lifecycle management
- helper offers
- accepting and rejecting offers
- moving accepted requests to in-progress status
- completion flow with helper rating
- user reviews and rating aggregation
- my profile card
- trust info in request and offer cards
- hiding banned authors from public feed
- safe Telegram notifications
- anti-spam rate limits
- per-user limits for unverified users
- complaints
- admin moderation
- complaint actions
- admin statistics
- moderator audit log
- user ban and unban
- user verification
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
2. Install dependencies.
3. Start PostgreSQL.
4. Apply migrations or enable `CREATE_SCHEMA_ON_START=true`.
5. Run the bot.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
alembic upgrade head
python run.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d
alembic upgrade head
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

## Request urgency

Requests support urgency levels:

- urgent — Срочно
- today — Сегодня
- tomorrow — Завтра
- week — На неделе
- flexible — Не срочно

The public feed is sorted by urgency first and creation date second.

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
RATE_LIMIT_SECONDS=0.7
MAX_ACTIVE_REQUESTS_PER_USER=5
MAX_PENDING_OFFERS_PER_USER=10
```

## User commands

- `/start` — start bot and create profile
- `/cancel` — cancel current action
- `/me` or `Мой профиль` — show profile card and activity counters
- `/request request_id` — show request details and owner actions
- `Профиль` — set city and district manually
- `Выбрать локацию` — choose city and district from catalog
- `Нужна помощь` — create request with catalog-based location and urgency selection
- `Заявки рядом` — show local requests sorted by urgency
- `Хочу помочь` — show local requests sorted by urgency
- `Мои заявки` — show own requests
- `Отклики по моим заявкам` or `/offers` — show incoming offers for own requests
- `Мои отклики` or `/myoffers` — show sent offers
- `Правила безопасности` — safety rules

## Admin commands

- `/admin` — admin dashboard
- `/stats` — project statistics
- `/audit` — last 10 moderator actions
- `/audit 30` — last 30 moderator actions
- `/locations` — city and district catalog
- `/addcity city_name` — add or reactivate city
- `/adddistrict city_id district_name` — add or reactivate district
- `/hidecity city_id` — hide city from user selection
- `/hidedistrict district_id` — hide district from user selection
- `/moderation` — requests waiting for moderation
- `/complaints` — new complaints
- `/complaint complaint_id` — complaint details and actions
- `/user telegram_id` — user details
- `/ban telegram_id` — ban user
- `/unban telegram_id` — unban user
- `/verify telegram_id` — mark user as verified
- `/unverify telegram_id` — remove user verification

## Production notes

The repository is public, so never commit real secrets. Use hosting environment variables for the bot token, database URL and admin ids.
