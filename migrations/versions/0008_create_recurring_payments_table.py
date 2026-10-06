"""create recurring payments table

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-06 17:12:11.837949+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=120), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("installments", sa.Integer(), nullable=True),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_cents > 0", name=op.f("ck_recurring_payments_amount_positive")),
        sa.CheckConstraint(
            "day_of_month BETWEEN 1 AND 31", name=op.f("ck_recurring_payments_day_of_month_range")
        ),
        sa.CheckConstraint(
            "installments IS NULL OR installments BETWEEN 2 AND 120",
            name=op.f("ck_recurring_payments_installments_range"),
        ),
        sa.CheckConstraint(
            "next_number >= 1", name=op.f("ck_recurring_payments_next_number_positive")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_recurring_payments_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_recurring_payments_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recurring_payments_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recurring_payments")),
    )
    with op.batch_alter_table("recurring_payments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_recurring_payments_active_next_run_at", ["active", "next_run_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_recurring_payments_user_id"), ["user_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("recurring_payments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recurring_payments_user_id"))
        batch_op.drop_index("ix_recurring_payments_active_next_run_at")

    op.drop_table("recurring_payments")
