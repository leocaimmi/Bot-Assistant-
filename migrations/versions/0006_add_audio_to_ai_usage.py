"""add audio to ai usage

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-05 22:16:50.544088+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("transcriptions", sa.Integer(), server_default=sa.text("0"), nullable=False)
        )
        batch_op.add_column(
            sa.Column("audio_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.drop_column("audio_seconds")
        batch_op.drop_column("transcriptions")
