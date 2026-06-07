"""add moderation logs

Revision ID: 0003_moderation_logs
Revises: 0002_reviews
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_moderation_logs"
down_revision = "0002_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "moderation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("moderator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_moderation_logs_moderator_id", "moderation_logs", ["moderator_id"])
    op.create_index("ix_moderation_logs_action", "moderation_logs", ["action"])
    op.create_index("ix_moderation_logs_entity_type", "moderation_logs", ["entity_type"])
    op.create_index("ix_moderation_logs_entity_id", "moderation_logs", ["entity_id"])


def downgrade() -> None:
    op.drop_table("moderation_logs")
