"""Add documents_enqueued to scraper_runs.

Revision ID: b7d9e4f1a2c3
Revises: a3f7e2b1c4d0
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d9e4f1a2c3"
down_revision = "a3f7e2b1c4d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scraper_runs",
        sa.Column(
            "documents_enqueued",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("scraper_runs", "documents_enqueued")
