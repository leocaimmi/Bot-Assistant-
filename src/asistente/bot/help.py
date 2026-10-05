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

Después tocá los botones para cambiar categoría, importe, fecha o borrarlo, o escribí:
• <code>borrar uber 2000</code> o <code>borrar el último</code>: lo borra (con confirmación)
• <code>cambiar uber 2000 a 2500</code>, <code>cambiar uber a comida</code>: lo corrige
• <code>cambiar uber 2000</code>: muestra los botones para editarlo
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

AI_HELP = """\
<b>🤖 Mensajes libres y audios (si la IA está activada)</b>
Lo que no entiendan las reglas lo interpreta la IA, por ejemplo:
• <code>el uber de ayer eran 2500</code> (te muestro el cambio antes de aplicarlo)
• <code>gasté dos lucas en el super</code>
• <code>hice press plano 4 de 12 con 60 y fondos 3 de 10</code>
🎙 O mandame un audio de hasta un minuto: te muestro lo que entendí y lo anoto.
/ia: cuántas consultas usaste y cuánto cuestan"""

GENERAL_HELP = """\
<b>⚙️ General</b>
/ayuda: esta ayuda
/cancelar: cancela la acción en curso"""

HELP_SECTIONS = (FINANCE_HELP, GYM_HELP, AI_HELP, GENERAL_HELP)

HELP_TEXT = "\n\n".join(HELP_SECTIONS)
