"""add cost to ai usage

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05 22:06:16.419489+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "cost_micro_usd", sa.BigInteger(), server_default=sa.text("0"), nullable=False
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.drop_column("cost_micro_usd")
