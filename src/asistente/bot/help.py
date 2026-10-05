"""User-facing help text, one section per feature."""

FINANCE_HELP = """\
<b>💸 Finanzas</b>
Mandá un mensaje con el gasto o el ingreso:
• <code>uber 2000</code>: gasto en Transporte
• <code>gym 47.000</code>: gasto en Gimnasio
• <code>transferencia utn 200.000</code>: ingreso
• <code>super 15.430,50 efectivo</code>: indicando la cuenta
• <code>nafta 30k ayer</code>: con fecha (<code>ayer</code>, <code>15/09</code>)
• <code>+ 50000 venta bici</code>: el <code>+</code> fuerza ingreso y el <code>-</code> gasto

Después tocá los botones para cambiar categoría, importe, fecha o borrarlo.
/movimientos [mes]: lista para ver o editar movimientos"""

GENERAL_HELP = """\
<b>⚙️ General</b>
/ayuda: esta ayuda
/cancelar: cancela la acción en curso"""

HELP_SECTIONS = (FINANCE_HELP, GENERAL_HELP)

HELP_TEXT = "\n\n".join(HELP_SECTIONS)
