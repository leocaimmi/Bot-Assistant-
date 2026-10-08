from aiogram.fsm.state import State, StatesGroup


class EditWorkoutEntry(StatesGroup):
    """Waiting for the new sets, reps or weight. FSM data holds ``entry_id``."""

    values = State()
