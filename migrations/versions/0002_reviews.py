"""add reviews

Revision ID: 0002_reviews
Revises: 0001_initial
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_reviews"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("help_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("request_id", "reviewer_id", "target_user_id", name="uq_reviews_request_reviewer_target"),
    )
    op.create_index("ix_reviews_request_id", "reviews", ["request_id"])
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])
    op.create_index("ix_reviews_target_user_id", "reviews", ["target_user_id"])


def downgrade() -> None:
    op.drop_table("reviews")
