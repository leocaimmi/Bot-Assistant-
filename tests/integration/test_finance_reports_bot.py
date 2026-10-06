from datetime import datetime

from asistente.bot.handlers.finance import views
from asistente.core.dates import MONTHS, shift_month
from tests.factories import BUENOS_AIRES
from tests.harness import BotHarness


def _current_month() -> tuple[int, int]:
    now = datetime.now(BUENOS_AIRES)
    return now.year, now.month


async def test_summary_of_current_month(harness: BotHarness) -> None:
    await harness.send("uber 2000")
    await harness.send("sube 1500")
    await harness.send("gym 47.000")
    await harness.send("transferencia utn 200.000")

    await harness.send("/resumen")

    reply = harness.last_reply
    assert "💸 <b>Gastaste $50.500</b>" in reply
    assert "🏋️ Gimnasio: <b>$47.000</b> (93%)" in reply
    assert "🚗 Transporte: <b>$3.500</b> (7%)" in reply
    assert "    ├ uber: $2.000\n    └ sube: $1.500" in reply
    assert "💰 <b>Ingresaste $200.000</b>" in reply
    assert "📱 Mercado Pago: <b>$200.000</b>" in reply
    assert "Balance: <b>+$149.500</b>" in reply
    assert "4 movimientos" in reply


async def test_navigate_months_and_open_transactions(harness: BotHarness) -> None:
    await harness.send("uber 2000")
    await harness.send("/resumen")
    _year, month = shift_month(*_current_month(), -1)

    await harness.click(harness.button(f"◀️ {MONTHS[month - 1]}"))
    assert "No hay movimientos en este mes." in harness.last_reply

    current_name = MONTHS[_current_month()[1] - 1]
    await harness.click(harness.button(f"{current_name} ▶️"))
    assert "Gastaste $2.000" in harness.last_reply

    await harness.click(harness.button("Ver movimientos"))
    assert f"Movimientos de {current_name}" in harness.last_reply


async def test_summary_of_a_named_month(harness: BotHarness) -> None:
    await harness.send("/resumen marzo 2025")

    assert "Resumen de marzo 2025" in harness.last_reply
    assert "No hay movimientos" in harness.last_reply


async def test_invalid_month(harness: BotHarness) -> None:
    await harness.send("/resumen cualquiera")

    assert harness.last_reply == views.INVALID_SUMMARY_MONTH


async def test_each_detail_has_its_own_line(harness: BotHarness) -> None:
    for text in ("pague claude 34.000", "pague cloud apple 1.600", "varios 500", "otra cosa 100"):
        await harness.send(text)

    await harness.send("/resumen")

    lines = harness.last_reply.splitlines()
    assert "    ├ pague claude: $34.000" in lines
    assert "    ├ pague cloud apple: $1.600" in lines
    assert "    ├ varios: $500" in lines
    assert "    └ y 1 más" in lines
