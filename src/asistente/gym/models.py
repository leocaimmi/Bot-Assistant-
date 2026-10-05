from datetime import date
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asistente.db.base import Base, TimestampMixin

MAX_EXERCISE_NAME_LENGTH = 60


class MuscleGroup(StrEnum):
    CHEST = "pecho"
    BACK = "espalda"
    LEGS = "piernas"
    SHOULDERS = "hombros"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    ABS = "abdominales"
    OTHER = "otros"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    MuscleGroup.CHEST: "Pecho",
    MuscleGroup.BACK: "Espalda",
    MuscleGroup.LEGS: "Piernas",
    MuscleGroup.SHOULDERS: "Hombros",
    MuscleGroup.BICEPS: "Bíceps",
    MuscleGroup.TRICEPS: "Tríceps",
    MuscleGroup.ABS: "Abdominales",
    MuscleGroup.OTHER: "Otros",
}


class Exercise(TimestampMixin, Base):
    """An exercise of the user's catalog, e.g. "Banco plano" (pecho)."""

    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("user_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(MAX_EXERCISE_NAME_LENGTH))
    # Normalized name: "Banco Plano" and "banco plano" are the same exercise.
    key: Mapped[str] = mapped_column(String(MAX_EXERCISE_NAME_LENGTH))
    muscle_group: Mapped[MuscleGroup] = mapped_column(
        Enum(
            MuscleGroup,
            name="muscle_group",
            native_enum=False,
            create_constraint=True,
            length=15,
            values_callable=lambda groups: [group.value for group in groups],
            validate_strings=True,
        )
    )


class Workout(TimestampMixin, Base):
    """Everything trained on one day."""

    __tablename__ = "workouts"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)

    entries: Mapped[list["WorkoutEntry"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutEntry.id",
        lazy="raise",
    )


class WorkoutEntry(TimestampMixin, Base):
    """``sets`` x ``reps`` of an exercise, optionally with a weight."""

    __tablename__ = "workout_entries"
    __table_args__ = (
        CheckConstraint("sets > 0", name="sets_positive"),
        CheckConstraint("reps > 0", name="reps_positive"),
        CheckConstraint("weight_grams IS NULL OR weight_grams > 0", name="weight_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True
    )
    sets: Mapped[int]
    reps: Mapped[int]
    # Grams avoid floating point issues: 62.5 kg is stored as 62500.
    weight_grams: Mapped[int | None]

    workout: Mapped[Workout] = relationship(back_populates="entries", lazy="raise")
    exercise: Mapped[Exercise] = relationship(lazy="raise")
