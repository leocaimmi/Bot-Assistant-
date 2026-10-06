"""create finance tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05 17:27:00.452505+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("emoji", sa.String(length=8), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_accounts_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("user_id", "name", name=op.f("uq_accounts_user_id_name")),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("emoji", sa.String(length=8), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "expense",
                "income",
                name="transaction_kind",
                native_enum=False,
                length=10,
            ),
            nullable=False,
        ),
        sa.Column("is_fallback", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('expense', 'income')", name=op.f("ck_categories_transaction_kind")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_categories_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("user_id", "name", name=op.f("uq_categories_user_id_name")),
    )
    op.create_table(
        "category_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_category_keywords_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_category_keywords_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_category_keywords")),
        sa.UniqueConstraint(
            "user_id", "keyword", name=op.f("uq_category_keywords_user_id_keyword")
        ),
    )
    with op.batch_alter_table("category_keywords", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_category_keywords_category_id"), ["category_id"], unique=False
        )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "expense",
                "income",
                name="transaction_kind",
                native_enum=False,
                length=10,
            ),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('expense', 'income')", name=op.f("ck_transactions_transaction_kind")
        ),
        sa.CheckConstraint("amount_cents > 0", name=op.f("ck_transactions_amount_positive")),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_transactions_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_transactions_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_transactions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_transactions_account_id"), ["account_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_transactions_category_id"), ["category_id"], unique=False
        )
        batch_op.create_index(
            "ix_transactions_user_id_occurred_at", ["user_id", "occurred_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index("ix_transactions_user_id_occurred_at")
        batch_op.drop_index(batch_op.f("ix_transactions_category_id"))
        batch_op.drop_index(batch_op.f("ix_transactions_account_id"))

    op.drop_table("transactions")
    with op.batch_alter_table("category_keywords", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_category_keywords_category_id"))

    op.drop_table("category_keywords")
    op.drop_table("categories")
    op.drop_table("accounts")
