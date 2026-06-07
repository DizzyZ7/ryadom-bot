from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    auto_publish_without_admins: bool = Field(default=True, alias="AUTO_PUBLISH_WITHOUT_ADMINS")
    create_schema_on_start: bool = Field(default=True, alias="CREATE_SCHEMA_ON_START")

    @property
    def admin_ids(self) -> set[int]:
        result: set[int] = set()
        for item in self.admin_ids_raw.split(","):
            item = item.strip()
            if item.isdigit():
                result.add(int(item))
        return result

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
