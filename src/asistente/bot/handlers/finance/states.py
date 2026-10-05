from aiogram.fsm.state import State, StatesGroup


class EditTransaction(StatesGroup):
    """Waiting for the new value of a field. FSM data holds ``tx_id``."""

    amount = State()
    description = State()
    day = State()
