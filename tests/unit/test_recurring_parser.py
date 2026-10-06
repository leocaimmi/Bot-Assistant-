import pytest

from asistente.finance.recurring import RecurringRequest, parse_recurring


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "zapatillas 10.000 cuota 1 de 9",
            RecurringRequest("zapatillas 10.000", 9, 1, split_total=False, day_of_month=None),
        ),
        (
            "Zapatillas 10.000 Cuota 3/9",
            RecurringRequest("Zapatillas 10.000", 9, 3, split_total=False, day_of_month=None),
        ),
        (
            "zapatillas 10.000 1 de 9",
            RecurringRequest("zapatillas 10.000", 9, 1, split_total=False, day_of_month=None),
        ),
        (
            "zapatillas 90.000 en 9 cuotas",
            RecurringRequest("zapatillas 90.000", 9, 1, split_total=True, day_of_month=None),
        ),
        (
            "zapatillas en 9 cuotas de 10.000",
            RecurringRequest("zapatillas 10.000", 9, 1, split_total=False, day_of_month=None),
        ),
        (
            "9 cuotas de 10.000 zapatillas",
            RecurringRequest("10.000 zapatillas", 9, 1, split_total=False, day_of_month=None),
        ),
        (
            "seguro del celu 5.000 todos los meses",
            RecurringRequest(
                "seguro del celu 5.000", None, 1, split_total=False, day_of_month=None
            ),
        ),
        (
            "netflix 8.000 mensual",
            RecurringRequest("netflix 8.000", None, 1, split_total=False, day_of_month=None),
        ),
        (
            "pago fijo seguro 5000",
            RecurringRequest("seguro 5000", None, 1, split_total=False, day_of_month=None),
        ),
        (
            "alquiler 300.000 el 10 de cada mes",
            RecurringRequest("alquiler 300.000", None, 1, split_total=False, day_of_month=10),
        ),
        (
            "alquiler 300.000 todos los 10",
            RecurringRequest("alquiler 300.000", None, 1, split_total=False, day_of_month=10),
        ),
    ],
)
def test_reads_installments_and_fixed_payments(text: str, expected: RecurringRequest) -> None:
    assert parse_recurring(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "uber 2000",
        "gym 47.000",
        "zapatillas 10.000 cuota 10 de 9",  # past the last one
        "zapatillas 10.000 en 1 cuota",
        "zapatillas 10.000 en 200 cuotas",
        "zapatillas 10.000 cuota 1 de 9 todos los meses",  # two ways of repeating
        "algo 1000 el 10 de cada mes y el 20 de cada mes",
        "algo 1000 el 40 de cada mes",
    ],
)
def test_ignores_what_does_not_repeat_or_is_unclear(text: str) -> None:
    assert parse_recurring(text) is None
