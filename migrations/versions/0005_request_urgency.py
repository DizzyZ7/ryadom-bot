"""add request urgency

Revision ID: 0005_request_urgency
Revises: 0004_locations
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_request_urgency"
down_revision = "0004_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "help_requests",
        sa.Column("urgency", sa.String(length=32), nullable=False, server_default="flexible"),
    )
    op.create_index("ix_help_requests_urgency", "help_requests", ["urgency"])


def downgrade() -> None:
    op.drop_index("ix_help_requests_urgency", table_name="help_requests")
    op.drop_column("help_requests", "urgency")
