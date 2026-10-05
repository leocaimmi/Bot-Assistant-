"""create gym tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05 18:32:03.630925+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column(
            "muscle_group",
            sa.Enum(
                "pecho",
                "espalda",
                "piernas",
                "hombros",
                "biceps",
                "triceps",
                "abdominales",
                "otros",
                name="muscle_group",
                native_enum=False,
                length=15,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "muscle_group IN ('pecho', 'espalda', 'piernas', 'hombros', "
            "'biceps', 'triceps', 'abdominales', 'otros')",
            name=op.f("ck_exercises_muscle_group"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_exercises_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
        sa.UniqueConstraint("user_id", "key", name=op.f("uq_exercises_user_id_key")),
    )
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_workouts_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workouts")),
        sa.UniqueConstraint("user_id", "day", name=op.f("uq_workouts_user_id_day")),
    )
    op.create_table(
        "workout_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("reps > 0", name=op.f("ck_workout_entries_reps_positive")),
        sa.CheckConstraint("sets > 0", name=op.f("ck_workout_entries_sets_positive")),
        sa.CheckConstraint(
            "weight_grams IS NULL OR weight_grams > 0",
            name=op.f("ck_workout_entries_weight_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_workout_entries_exercise_id_exercises"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workout_id"],
            ["workouts.id"],
            name=op.f("fk_workout_entries_workout_id_workouts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_entries")),
    )
    with op.batch_alter_table("workout_entries", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_workout_entries_exercise_id"), ["exercise_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_workout_entries_workout_id"), ["workout_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("workout_entries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workout_entries_workout_id"))
        batch_op.drop_index(batch_op.f("ix_workout_entries_exercise_id"))

    op.drop_table("workout_entries")
    op.drop_table("workouts")
    op.drop_table("exercises")
