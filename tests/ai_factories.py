"""Builders and fakes for AI tests (no real API calls, no cost)."""

from collections.abc import Sequence

from asistente.ai.interpreter import InterpretationResult, InterpreterContext, InterpreterError
from asistente.ai.pricing import TokenUsage
from asistente.ai.schema import (
    Changes,
    ExerciseDone,
    Intent,
    Interpretation,
    Movement,
    Target,
)
from asistente.gym.models import MuscleGroup


def interpretation(
    intent: Intent,
    *,
    movements: Sequence[Movement] = (),
    target: Target | None = None,
    changes: Changes | None = None,
    exercises: Sequence[ExerciseDone] = (),
    workout_day: str | None = None,
) -> Interpretation:
    return Interpretation(
        intent=intent,
        movements=list(movements),
        target=target,
        changes=changes,
        exercises=list(exercises),
        workout_day=workout_day,
    )


def movement(
    description: str,
    amount: str,
    *,
    income: bool = False,
    day: str | None = None,
    account: str | None = None,
) -> Movement:
    return Movement(description=description, amount=amount, income=income, day=day, account=account)


def target(
    description: str | None = None, amount: str | None = None, day: str | None = None
) -> Target:
    return Target(description=description, amount=amount, day=day)


def changes(
    *,
    amount: str | None = None,
    description: str | None = None,
    category: str | None = None,
    day: str | None = None,
) -> Changes:
    return Changes(amount=amount, description=description, category=category, day=day)


def exercise(
    name: str,
    sets: int,
    reps: int,
    *,
    group: MuscleGroup = MuscleGroup.CHEST,
    kg: float | None = None,
) -> ExerciseDone:
    return ExerciseDone(name=name, muscle_group=group, sets=sets, reps=reps, weight_kg=kg)


class FakeInterpreter:
    """Returns queued answers and records what it was asked."""

    def __init__(self) -> None:
        self.answers: list[Interpretation | InterpreterError] = []
        self.texts: list[str] = []
        self.contexts: list[InterpreterContext] = []

    def will_answer(self, *answers: Interpretation | InterpreterError) -> None:
        self.answers.extend(answers)

    async def interpret(
        self, text: str, context: InterpreterContext, *, user_key: str
    ) -> InterpretationResult:
        self.texts.append(text)
        self.contexts.append(context)
        answer = self.answers.pop(0)
        if isinstance(answer, InterpreterError):
            raise answer
        return InterpretationResult(answer, TokenUsage(input_tokens=900, output_tokens=60))
