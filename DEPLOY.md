# Deploy

## Production with Docker Compose

1. Copy production env example:

```bash
cp .env.prod.example .env
```

2. Edit `.env`:

```env
BOT_TOKEN=real_bot_token
ADMIN_IDS=your_telegram_id
POSTGRES_PASSWORD=strong_password
DATABASE_URL=postgresql+asyncpg://ryadom:strong_password@postgres:5432/ryadom
```

3. Build and start:

```bash
docker compose -f compose.prod.yaml up -d --build
```

4. Check logs:

```bash
docker compose -f compose.prod.yaml logs -f bot
```

5. Open Telegram and run:

```text
/health
```

## Update deployment

```bash
git pull
docker compose -f compose.prod.yaml up -d --build
```

The bot container runs migrations automatically before startup:

```bash
alembic upgrade head
```

## Backup PostgreSQL

```bash
docker exec ryadom_postgres pg_dump -U ryadom ryadom > ryadom_backup.sql
```

## Restore PostgreSQL

```bash
cat ryadom_backup.sql | docker exec -i ryadom_postgres psql -U ryadom ryadom
```

## Useful commands

```bash
docker compose -f compose.prod.yaml ps
docker compose -f compose.prod.yaml restart bot
docker compose -f compose.prod.yaml logs --tail=200 bot
docker compose -f compose.prod.yaml down
```
