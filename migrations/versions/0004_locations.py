"""add locations

Revision ID: 0004_locations
Revises: 0003_moderation_logs
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_locations"
down_revision = "0003_moderation_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_cities_name", "cities", ["name"], unique=True)

    op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("city_id", "name", name="uq_districts_city_name"),
    )
    op.create_index("ix_districts_city_id", "districts", ["city_id"])
    op.create_index("ix_districts_name", "districts", ["name"])

    cities_table = sa.table(
        "cities",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    districts_table = sa.table(
        "districts",
        sa.column("city_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        cities_table,
        [
            {"id": 1, "name": "Алматы", "is_active": True},
            {"id": 2, "name": "Астана", "is_active": True},
            {"id": 3, "name": "Москва", "is_active": True},
            {"id": 4, "name": "Санкт-Петербург", "is_active": True},
        ],
    )
    op.bulk_insert(
        districts_table,
        [
            {"city_id": 1, "name": "Алмалинский", "is_active": True},
            {"city_id": 1, "name": "Бостандыкский", "is_active": True},
            {"city_id": 1, "name": "Ауэзовский", "is_active": True},
            {"city_id": 1, "name": "Медеуский", "is_active": True},
            {"city_id": 1, "name": "Турксибский", "is_active": True},
            {"city_id": 2, "name": "Алматинский", "is_active": True},
            {"city_id": 2, "name": "Есиль", "is_active": True},
            {"city_id": 2, "name": "Сарыарка", "is_active": True},
            {"city_id": 3, "name": "Центральный", "is_active": True},
            {"city_id": 3, "name": "Северный", "is_active": True},
            {"city_id": 3, "name": "Южный", "is_active": True},
            {"city_id": 4, "name": "Центральный", "is_active": True},
            {"city_id": 4, "name": "Адмиралтейский", "is_active": True},
            {"city_id": 4, "name": "Петроградский", "is_active": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("districts")
    op.drop_table("cities")
