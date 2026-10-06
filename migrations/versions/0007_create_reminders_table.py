"""create reminders table

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06 02:32:09.151080+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=200), nullable=False),
        sa.Column(
            "repeat",
            sa.Enum(
                "once",
                "daily",
                "weekly",
                "monthly",
                name="reminder_repeat",
                native_enum=False,
                length=10,
            ),
            nullable=False,
        ),
        sa.Column("minute_of_day", sa.Integer(), nullable=False),
        sa.Column("weekdays", sa.Integer(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "repeat IN ('once', 'daily', 'weekly', 'monthly')",
            name=op.f("ck_reminders_reminder_repeat"),
        ),
        sa.CheckConstraint(
            "day_of_month IS NULL OR day_of_month BETWEEN 1 AND 31",
            name=op.f("ck_reminders_day_of_month_range"),
        ),
        sa.CheckConstraint(
            "minute_of_day BETWEEN 0 AND 1439", name=op.f("ck_reminders_minute_of_day_range")
        ),
        sa.CheckConstraint("weekdays BETWEEN 0 AND 127", name=op.f("ck_reminders_weekdays_range")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_reminders_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminders")),
    )
    with op.batch_alter_table("reminders", schema=None) as batch_op:
        batch_op.create_index(
            "ix_reminders_active_next_run_at", ["active", "next_run_at"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_reminders_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("reminders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reminders_user_id"))
        batch_op.drop_index("ix_reminders_active_next_run_at")

    op.drop_table("reminders")
