# Smoke test checklist

Use this checklist before giving the bot to real testers.

## 0. Preflight

Run migrations and preflight:

```bash
alembic upgrade head
python scripts/preflight.py
```

Expected result: every line starts with `OK`.

In Telegram, admin runs:

```text
/health
```

Expected result:

- Database: OK
- Config: OK
- admin count is greater than 0

## 1. Basic user start

User A:

```text
/start
```

Expected:

- bot creates profile
- main menu appears
- no errors in logs

## 2. Profile location

User A:

```text
Выбрать локацию
```

Steps:

1. choose city
2. choose district

Expected:

- one bot message is edited during selection
- final text says location is saved
- `/me` shows selected location

## 3. Create request

User A:

```text
Нужна помощь
```

Steps:

1. choose category
2. send title
3. send description
4. choose city
5. choose district
6. send address hint or `-`
7. send time text
8. choose urgency
9. choose reward type
10. send `+`

Expected:

- choice steps edit one wizard message
- request is created
- final card includes category, status, urgency, location, reward and trust line

## 4. Nearby feed

User B:

```text
/start
Выбрать локацию
Заявки рядом
```

Expected:

- request from User A is visible if location matches
- request card has `Откликнуться` and `Пожаловаться`
- urgent requests appear above non-urgent requests

## 5. Request filter

User B:

```text
Фильтр заявок
```

Steps:

1. choose category
2. choose urgency
3. choose search scope

Expected:

- filter message is edited on each step
- result summary shows selected filters and found count
- matching requests are sent as cards

## 6. Offer flow

User B opens a request and taps:

```text
Откликнуться
```

Then sends a short offer message.

Expected:

- offer is saved
- User A receives notification
- User A sees offer in `Отклики по моим заявкам`

## 7. Accept offer

User A:

```text
Отклики по моим заявкам
```

Steps:

1. open pending offer card
2. tap `Принять`

Expected:

- offer becomes accepted
- request status becomes in_progress
- other pending offers for the same request become rejected
- User B receives notification

## 8. Complete request and rating

User A:

```text
/request request_id
```

Steps:

1. tap `Завершить`
2. choose rating 1-5

Expected:

- request status becomes done
- rating is saved once
- helper rating count increases
- duplicate rating is rejected

## 9. Complaint flow

User B taps:

```text
Пожаловаться
```

Then sends reason text.

Expected:

- complaint is created
- admin sees it in `/complaints`
- `/complaint complaint_id` opens details
- admin can close complaint or ban target user

## 10. Admin moderation

Set in env:

```env
AUTO_PUBLISH_WITHOUT_ADMINS=false
```

Create a request as User A.

Admin:

```text
/moderation
```

Expected:

- one moderation card appears
- `Назад / Далее` works if there are several requests
- `Опубликовать` changes status to published
- `Отклонить` changes status to rejected
- action appears in `/audit`

## 11. Admin locations

Admin:

```text
/locations
/addcity TestCity
/adddistrict city_id TestDistrict
/hidecity city_id
/hidedistrict district_id
/audit
```

Expected:

- `/locations` is paginated
- city and district changes are saved
- every admin change appears in audit log

## 12. Limits and bans

Admin:

```text
/ban user_telegram_id
```

Expected:

- banned user receives restricted access message
- banned user's published requests are hidden from public feed
- `/unban user_telegram_id` restores access

User limit check:

1. create max active requests as unverified user
2. try to create one more
3. verify user with `/verify user_telegram_id`
4. try again

Expected:

- unverified user hits limit
- verified user can continue

## 13. Admin health and stats

Admin:

```text
/health
/stats
/audit
```

Expected:

- `/health` shows Database OK and Config OK
- `/stats` shows counters
- `/audit` is paginated

## 14. Docker smoke test

```bash
cp .env.prod.example .env
docker compose -f compose.prod.yaml up -d --build
docker compose -f compose.prod.yaml logs -f bot
```

Expected:

- PostgreSQL becomes healthy
- migrations run
- bot starts polling
- `/health` works in Telegram

## 15. Rollback basics

Before real testing, make backup:

```bash
docker exec ryadom_postgres pg_dump -U ryadom ryadom > ryadom_backup.sql
```

Expected:

- backup file is created
- file size is greater than 0
