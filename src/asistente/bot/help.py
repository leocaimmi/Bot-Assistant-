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
/movimientos [mes]: lista para ver o editar movimientos
/resumen [mes]: cuánto gastaste por categoría y cuánto ingresaste por cuenta
/categorias: categorías y las palabras que las eligen
/palabra nafta transporte: enseñarme una palabra o moverla de categoría
/nueva_categoria 🚙 Auto: crear una categoría (<code>ingreso</code> adelante para ingresos)"""

GYM_HELP = """\
<b>🏋️ Gimnasio</b>
Anotá lo que hiciste: primero las series y después las repeticiones.
• <code>pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8</code>
• <code>piernas: sentadilla 4x10 80kg; prensa 3x12</code>
• <code>ayer espalda: dominadas 4x8</code>
El peso es opcional. Grupos: pecho, espalda, piernas, hombros, bíceps, tríceps, abdominales.
/entreno [día]: lo que entrenaste ese día
/semana: días y músculos de esta semana
/historial banco plano: progreso y récord de un ejercicio
/ejercicios: tus ejercicios por músculo"""

GENERAL_HELP = """\
<b>⚙️ General</b>
/ayuda: esta ayuda
/cancelar: cancela la acción en curso"""

HELP_SECTIONS = (FINANCE_HELP, GYM_HELP, GENERAL_HELP)

HELP_TEXT = "\n\n".join(HELP_SECTIONS)
