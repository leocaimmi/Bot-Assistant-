"""User-facing help: a short menu and one short card per topic, browsed with buttons."""

from enum import StrEnum


class HelpTopic(StrEnum):
    MENU = "menu"
    FINANCE = "finance"
    GYM = "gym"
    EDIT = "edit"
    REMINDERS = "reminders"
    AI = "ai"


# Button of each topic, in menu order.
TOPIC_BUTTONS = {
    HelpTopic.FINANCE: "💸 Gastos e ingresos",
    HelpTopic.GYM: "🏋️ Gimnasio",
    HelpTopic.EDIT: "✏️ Corregir y borrar",
    HelpTopic.REMINDERS: "⏰ Recordatorios",
    HelpTopic.AI: "🤖 IA y audios",
}

_MENU = """\
📖 <b>¿Qué puedo hacer?</b>
{how}
<code>uber 2000</code> · anoto un gasto
<code>transferencia utn 200.000</code> · un ingreso
<code>pecho: banco plano 4x12 60kg</code> · un entrenamiento
<code>recordame mañana a las 9 pagar la luz</code> · un recordatorio

Tocá un tema para ver todo 👇
/ayuda vuelve a este menú · /cancelar corta lo que estés haciendo"""

_FINANCE = """\
💸 <b>Gastos e ingresos</b>

<b>Anotar</b>
<code>uber 2000</code> · gasto
<code>transferencia utn 200.000</code> · ingreso
<code>super 15.430,50 efectivo</code> · con cuenta
<code>nafta 30k ayer</code> · con fecha
<code>+ 50000 venta bici</code> · fuerza ingreso (<code>-</code> fuerza gasto)

<b>Ver</b>
/resumen · el mes por categoría (<code>/resumen septiembre</code>)
/movimientos · lista para ver y editar

<b>Categorías</b>
/categorias · las tuyas y sus palabras
<code>/palabra nafta auto</code> · enseñame una palabra
<code>/nueva_categoria 🚙 Auto</code> · crear una

💡 Importes: <code>2.000</code> · <code>2k</code> · <code>200 mil</code> · <code>2 lucas</code>"""

_GYM = """\
🏋️ <b>Gimnasio</b>
Primero las series y después las repeticiones; el peso es opcional.

<b>Anotar</b>
<code>pecho: banco plano 4x12 60kg</code>
<code>piernas: sentadilla 4x10 80kg; prensa 3x12</code>
<code>ayer espalda: dominadas 4x8</code>
También vale <code>4 series de 12</code> o <code>4 por 12</code>.

<b>Ver</b>
/entreno · lo de hoy (<code>/entreno ayer</code>)
/semana · días y músculos de la semana
<code>/historial banco plano</code> · progreso y récord
/ejercicios · tus ejercicios por músculo"""

_EDIT = """\
✏️ <b>Corregir y borrar</b>
Cada movimiento trae botones para editarlo. También podés escribir:

<code>cambiar uber 2000 a 2500</code> · el importe
<code>cambiar uber a comida</code> · la categoría
<code>cambiar uber 2000</code> · muestra los botones
<code>borrar uber 2000</code> · pide confirmación
<code>borrar el último</code> · el más reciente

🏋️ Un entrenamiento se borra con <b>Deshacer</b> o desde /entreno."""

_REMINDERS = """\
⏰ <b>Recordatorios</b>
Te llegan como notificación de Telegram, en hora argentina:
<code>recordame mañana a las 9 pagar la luz</code>
<code>recordame en 20 minutos sacar la ropa</code>
<code>recordame el 15/10 a las 18:30 turno médico</code>
<code>recordame todos los lunes a las 12 la pastilla</code>
<code>recordame el 10 de cada mes pagar el alquiler</code>
Otra zona horaria: <code>... a las 10 hora de España</code>

Sin hora, te aviso a las 9. Cuando llega: ✅ Listo o ⏳ 10 min.
/recordatorios · ver y borrar"""

_AI = """\
🤖 <b>IA y audios</b>
Lo que las reglas no entienden lo interpreta la IA:
<code>gasté dos lucas en el super</code>
<code>el uber eran 2500</code> · te muestro el cambio antes
<code>hice press plano 4 de 12 con 60</code>

🎙 Mandame un audio de hasta 1 minuto: te muestro lo que entendí y lo anoto.
/ia · consultas y costo del mes"""

_AI_OFF = "⚠️ Ahora está apagada: falta configurar <code>OPENAI_API_KEY</code>."

_TOPICS = {
    HelpTopic.FINANCE: _FINANCE,
    HelpTopic.GYM: _GYM,
    HelpTopic.EDIT: _EDIT,
    HelpTopic.REMINDERS: _REMINDERS,
    HelpTopic.AI: _AI,
}


def help_text(topic: HelpTopic, *, ai_enabled: bool) -> str:
    """Text of one help screen (HTML). Without AI, audio is not offered."""
    if topic is HelpTopic.MENU:
        return _MENU.format(how="Escribime o mandame un audio:" if ai_enabled else "Escribime:")
    if topic is HelpTopic.AI and not ai_enabled:
        return f"{_AI}\n\n{_AI_OFF}"
    return _TOPICS[topic]
