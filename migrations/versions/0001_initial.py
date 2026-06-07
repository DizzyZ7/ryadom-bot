"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("district", sa.String(length=128), nullable=True),
        sa.Column("rating_sum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "help_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("district", sa.String(length=128), nullable=True),
        sa.Column("address_hint", sa.String(length=255), nullable=True),
        sa.Column("reward_type", sa.String(length=32), nullable=False, server_default="free"),
        sa.Column("reward_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("needed_at_text", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="moderation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_help_requests_user_id", "help_requests", ["user_id"])
    op.create_index("ix_help_requests_category", "help_requests", ["category"])
    op.create_index("ix_help_requests_city", "help_requests", ["city"])
    op.create_index("ix_help_requests_district", "help_requests", ["district"])
    op.create_index("ix_help_requests_status", "help_requests", ["status"])

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("help_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("helper_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_offers_request_id", "offers", ["request_id"])
    op.create_index("ix_offers_helper_id", "offers", ["helper_id"])
    op.create_index("ix_offers_status", "offers", ["status"])

    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("help_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_complaints_request_id", "complaints", ["request_id"])
    op.create_index("ix_complaints_reporter_id", "complaints", ["reporter_id"])
    op.create_index("ix_complaints_target_user_id", "complaints", ["target_user_id"])
    op.create_index("ix_complaints_status", "complaints", ["status"])


def downgrade() -> None:
    op.drop_table("complaints")
    op.drop_table("offers")
    op.drop_table("help_requests")
    op.drop_table("users")
