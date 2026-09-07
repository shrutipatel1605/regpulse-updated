"""add failed_extractions to scraper_runs

Revision ID: a3f7e2b1c4d0
Revises: 1066cb96e57c
Create Date: 2026-05-15 14:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7e2b1c4d0"
down_revision: Union[str, None] = "1066cb96e57c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraper_runs",
        sa.Column(
            "failed_extractions",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("scraper_runs", "failed_extractions")
