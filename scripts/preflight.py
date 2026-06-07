import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from app.config import settings
from app.database import engine


REQUIRED_TABLES = {
    "alembic_version",
    "users",
    "help_requests",
    "offers",
    "complaints",
    "reviews",
    "moderation_logs",
    "cities",
    "districts",
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str = ""


def print_result(result: CheckResult) -> None:
    status = "OK" if result.ok else "FAIL"
    details = f" — {result.details}" if result.details else ""
    print(f"[{status}] {result.name}{details}")


async def check_database() -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        async with engine.begin() as connection:
            await connection.execute(text("select 1"))
            results.append(CheckResult("database connection", True))

            rows = await connection.execute(
                text(
                    "select table_name from information_schema.tables "
                    "where table_schema = 'public'"
                )
            )
            existing_tables = {row[0] for row in rows.fetchall()}
            missing_tables = sorted(REQUIRED_TABLES - existing_tables)
            results.append(
                CheckResult(
                    "required tables",
                    not missing_tables,
                    "missing: " + ", ".join(missing_tables) if missing_tables else "all present",
                )
            )

            if "alembic_version" in existing_tables:
                version_rows = await connection.execute(text("select version_num from alembic_version"))
                versions = [row[0] for row in version_rows.fetchall()]
                results.append(
                    CheckResult(
                        "alembic version",
                        bool(versions),
                        ", ".join(versions) if versions else "empty",
                    )
                )
    except Exception as exc:
        results.append(CheckResult("database connection", False, f"{type(exc).__name__}: {exc}"))
    finally:
        await engine.dispose()
    return results


def check_config() -> list[CheckResult]:
    return [
        CheckResult("BOT_TOKEN", bool(settings.telegram_bot_token)),
        CheckResult("DATABASE_URL", bool(settings.database_url)),
        CheckResult("ADMIN_IDS", bool(settings.admin_ids), f"count={len(settings.admin_ids)}"),
        CheckResult("ENVIRONMENT", bool(settings.environment), settings.environment),
        CheckResult("RATE_LIMIT_SECONDS", settings.rate_limit_seconds >= 0, str(settings.rate_limit_seconds)),
        CheckResult("MAX_ACTIVE_REQUESTS_PER_USER", settings.max_active_requests_per_user > 0, str(settings.max_active_requests_per_user)),
        CheckResult("MAX_PENDING_OFFERS_PER_USER", settings.max_pending_offers_per_user > 0, str(settings.max_pending_offers_per_user)),
    ]


async def main() -> int:
    results = check_config()
    results.extend(await check_database())

    failed = False
    for result in results:
        print_result(result)
        failed = failed or not result.ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
