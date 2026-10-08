"""Gym texts (HTML). Exercise names come from the user, so they are always escaped."""

from collections.abc import Iterable
from datetime import date
from html import escape

from asistente.gym.models import MuscleGroup, Workout, WorkoutEntry
from asistente.gym.service import DaySummary, ExerciseHistory, HistoryEntry, LoggedWorkout
from asistente.gym.units import format_kg

WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")

FORMAT_EXAMPLES = (
    "<code>pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8</code>\n"
    "Primero las series y después las repeticiones; el peso es opcional."
)
WORKOUT_FORMAT_HELP = f"🤔 No entendí el entrenamiento. Escribilo así:\n{FORMAT_EXAMPLES}"
HISTORY_USAGE = "Decime el ejercicio, por ejemplo <code>/historial banco plano</code>."
INVALID_DAY = (
    "🤔 No entendí el día. Probá con <code>/entreno ayer</code> o <code>/entreno 15/09</code>."
)
ASK_VALUES = (
    "✏️ ¿Cómo quedó? Por ejemplo <code>3x10 40kg</code>, <code>40kg</code> o "
    "<code>sin peso</code>.\n/cancelar para dejarlo."
)
INVALID_VALUES = "🤔 No entendí. Probá con <code>3x10 40kg</code>, <code>40kg</code> o /cancelar."
UPDATED = "✏️ Ejercicio actualizado"
ALREADY_LIKE_THAT = "👌 Ya estaba así"
NOTHING_LOGGED = "🏋️ Todavía no anotaste entrenamientos."
CHANGE_UNAVAILABLE = "Este cambio ya no está disponible."
CHANGE_DISCARDED = "👌 Cambio descartado."


def logged_workout(logged: LoggedWorkout, today: date) -> str:
    lines = [f"✅ <b>Entrenamiento anotado</b> · {day_label(logged.day, today)}"]
    lines += _by_group(logged.entries, numbered=False)
    return "\n".join(lines)


def day_workout(workout: Workout | None, day: date, today: date) -> str:
    title = f"🏋️ <b>Entrenamiento de {day_label(day, today)}</b>"
    if workout is None or not workout.entries:
        return f"{title}\n\nNo anotaste nada ese día."
    lines = [title, *_by_group(workout.entries, numbered=True)]
    total = sum(entry.sets for entry in workout.entries)
    lines += ["", f"{total} series en total. Tocá un número para corregirlo o borrarlo."]
    return "\n".join(lines)


def week(days: list[DaySummary]) -> str:
    lines = ["📅 <b>Esta semana</b>", ""]
    if not days:
        return "\n".join([*lines, "Todavía no entrenaste esta semana."])
    for summary in days:
        groups = ", ".join(group.label for group in summary.groups)
        weekday = WEEKDAYS[summary.day.weekday()]
        lines.append(f"{weekday} {summary.day:%d/%m}: {groups} · {summary.sets} series")
    trained = "1 día entrenado" if len(days) == 1 else f"{len(days)} días entrenados"
    lines += ["", f"💪 {trained}"]
    return "\n".join(lines)


def history(result: ExerciseHistory) -> str:
    exercise = result.exercise
    lines = [f"📈 <b>{escape(exercise.name)}</b> ({exercise.muscle_group.label})"]
    if not result.entries:
        return "\n".join([*lines, "", "Todavía no anotaste este ejercicio."])
    if result.best is not None:
        lines.append(f"🏆 Récord: {_set_text(result.best)} ({result.best.day:%d/%m/%Y})")
    lines.append("")
    lines += [f"{entry.day:%d/%m}: {_set_text(entry)}" for entry in result.entries]
    return "\n".join(lines)


def exercises(items: Iterable[tuple[MuscleGroup, list[str]]]) -> str:
    lines = ["💪 <b>Tus ejercicios</b>"]
    rows = [
        f"<b>{group.label}</b>: {', '.join(escape(name) for name in names)}"
        for group, names in items
    ]
    if not rows:
        return "\n".join([*lines, "", f"Todavía no anotaste ejercicios. Probá:\n{FORMAT_EXAMPLES}"])
    return "\n".join([*lines, "", *rows])


def entry_card(entry: WorkoutEntry, today: date, *, title: str | None = None) -> str:
    """One exercise of a workout (``exercise`` and ``workout`` loaded)."""
    exercise = entry.exercise
    lines = [title, ""] if title else []
    lines += [
        f"🏋️ <b>{escape(exercise.name)}</b> · {exercise.muscle_group.label}",
        sets_text(entry.sets, entry.reps, entry.weight_grams),
        f"📅 {day_label(entry.workout.day, today)}",
    ]
    return "\n".join(lines)


def change_preview(entry: WorkoutEntry, sets: int, reps: int, weight_grams: int | None) -> str:
    """Title of a fix to confirm: ``3x10 · sin peso → 3x10 · 7,5 kg``."""
    before = sets_text(entry.sets, entry.reps, entry.weight_grams)
    after = sets_text(sets, reps, weight_grams)
    return f"✏️ <b>¿Aplico este cambio?</b>\n{before} → <b>{after}</b>"


def sets_text(sets: int, reps: int, weight_grams: int | None) -> str:
    """``3x10 · 7,5 kg`` or ``3x10 · sin peso``."""
    return f"{sets}x{reps} · {format_kg(weight_grams) if weight_grams else 'sin peso'}"


def undone(count: int) -> str:
    plural = "ejercicio borrado" if count == 1 else "ejercicios borrados"
    return f"↩️ Listo, {count} {plural}."


def day_label(day: date, today: date) -> str:
    if day == today:
        return f"hoy {day:%d/%m}"
    return f"{WEEKDAYS[day.weekday()]} {day:%d/%m/%Y}"


def entry_text(entry: WorkoutEntry) -> str:
    weight = f" · {format_kg(entry.weight_grams)}" if entry.weight_grams else ""
    return f"{escape(entry.exercise.name)}: {entry.sets}x{entry.reps}{weight}"


def _by_group(entries: list[WorkoutEntry], *, numbered: bool) -> list[str]:
    groups: dict[MuscleGroup, list[tuple[int, WorkoutEntry]]] = {}
    for number, entry in enumerate(entries, start=1):
        groups.setdefault(entry.exercise.muscle_group, []).append((number, entry))
    lines = []
    for group, group_entries in groups.items():
        lines += ["", f"<b>{group.label}</b>"]
        lines += [
            f"{f'{number}.' if numbered else '•'} {entry_text(entry)}"
            for number, entry in group_entries
        ]
    return lines


def _set_text(entry: HistoryEntry) -> str:
    weight = f" · {format_kg(entry.weight_grams)}" if entry.weight_grams else ""
    return f"{entry.sets}x{entry.reps}{weight}"
