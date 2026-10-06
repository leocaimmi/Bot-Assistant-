class UserError(Exception):
    """An expected problem caused by the user's input or action.

    Its message is written for the user (in Spanish) and is safe to show as is.
    """
