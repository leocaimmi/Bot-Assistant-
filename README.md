# Bot Asistente

Bot de Telegram personal para registrar gastos e ingresos en pesos argentinos, llevar la
rutina del gimnasio y agendar recordatorios, escribiendo (o dictando) mensajes como
`uber 2000`, `gym 47.000` o `recordame mañana a las 9 pagar la luz`.

- Plan y fases: [docs/ROADMAP.md](docs/ROADMAP.md)
- Arquitectura, modelo de datos y seguridad: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Uso

En el bot, `/ayuda` abre un menú con un botón por tema (gastos, gimnasio, correcciones,
recordatorios e IA) y ejemplos que se copian con un toque.

| Mensaje | Resultado |
| ------- | --------- |
| `uber 2000` | Gasto de $2.000 en 🚗 Transporte, cuenta Mercado Pago |
| `gym 47.000` | Gasto de $47.000 en 🏋️ Gimnasio |
| `transferencia utn 200.000` | Ingreso de $200.000 en 🔁 Transferencias |
| `super 15.430,50 efectivo` | Gasto en 🛒 Supermercado pagado en Efectivo |
| `nafta 30k ayer` | Gasto de $30.000 con fecha de ayer |
| `+ 50000 venta bici` | El `+` fuerza ingreso; el `-` fuerza gasto |
| `coca, doritos, alfajor 10.200` | Un gasto con 3 ítems (también separados por `;` o `+`) |
| `eliminar uber 2000` / `borrar el último` | Busca el movimiento y pide confirmación para borrarlo |
| `cambiar uber 2000 a 2500` | Muestra el cambio y lo aplica cuando tocás **Aplicar** (también `a comida`, `a ayer` o `a efectivo`) |
| `hice una transferencia a juan 5000` | Gasto en 📤 Transferencias enviadas (`recibí` o `me pagaron`: ingreso) |
| `cambiar uber 2000` | Muestra los botones para editarlo |
| `/movimientos [mes]` | Lista paginada; tocá un número para editarlo o borrarlo |
| `/resumen [mes]` | Gastos por categoría (con detalle: uber, sube...), ingresos por cuenta y balance |
| `/categorias` | Categorías y las palabras que las eligen |
| `/palabra nafta auto` | Enseña o mueve una palabra clave a otra categoría |
| `/nueva_categoria 🚙 Auto` | Crea una categoría (`ingreso` adelante para ingresos) |

Cada movimiento registrado llega con botones para cambiar la categoría, el importe, la
descripción, la fecha, la cuenta o el tipo, y para borrarlo (con confirmación).

La descripción se guarda con la primera letra en mayúscula y el resto en minúscula
(`uber` → `Uber`; las siglas como `YPF` quedan igual). Si un importe paga varias cosas,
cada una es un ítem: la ficha los muestra uno por renglón y `/movimientos` y `/resumen`,
separados por coma. Sin comas (`gasto 10.200 una coca Doritos picantes y un chocolate`)
los separa la IA.

Importes aceptados: `2000`, `2.000`, `1.500,50`, `2k`, `1,5k`, `200 mil`, `2 lucas`,
`1 palo`. Fechas: `hoy`, `ayer`, `anteayer`, `15/09`, `15/09/2026`. Cuentas: `mp`,
`mercado pago`, `efectivo`, `banco`.

### Gimnasio

Primero las series y después las repeticiones; el peso es opcional.

| Mensaje | Resultado |
| ------- | --------- |
| `pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8` | Anota 2 ejercicios de pecho en el día de hoy |
| `hice pecho banco plano 4 series de 12` | Mismo formato con palabras |
| `piernas: sentadilla 4x10 80kg; prensa 3x12` | Varios ejercicios, separados por coma, `;`, `y` o renglones |
| `ayer espalda: dominadas 4x8` | Con fecha |
| `/entreno [día]` | El entrenamiento del día, con botones para borrar ejercicios |
| `/semana` | Días entrenados y músculos de la semana |
| `/historial banco plano` | Progreso del ejercicio y récord personal |
| `/ejercicios` | Tus ejercicios agrupados por músculo |

Cada entrenamiento anotado trae un botón **Deshacer**.

### Recordatorios

En hora argentina, salvo que digas otra zona. Llegan como un mensaje del bot, así que el
celular muestra la **notificación de Telegram** (si el chat no está silenciado).

| Mensaje | Resultado |
| ------- | --------- |
| `recordame mañana a las 9 pagar la luz` | Una vez, mañana a las 9:00 |
| `recordame en 20 minutos sacar la ropa` | Dentro de 20 minutos (también `en 2 horas`, `en 3 días`) |
| `recordame el 15/10 a las 18:30 turno médico` | Ese día (también `el 15 de octubre`, `el viernes`, `el 15`) |
| `recordame todos los lunes a las 12 la pastilla` | Cada lunes (también `los martes y jueves`, `de lunes a viernes`) |
| `recordame todos los días a las 8 tomar agua` | Todos los días |
| `recordame el 10 de cada mes pagar el alquiler` | Todos los meses (el 31 cae el último día en meses cortos) |
| `recordame mañana a las 10 hora de España llamar a Pablo` | A las 10 de España, y te muestra qué hora es acá |
| `/recordatorios` | Tus recordatorios, con botones para borrarlos |

- Horas de 24 h o con `de la mañana`, `de la tarde`, `de la noche`; sin hora, a las 9.
- De madrugada (antes de las 5), `mañana` es el día que ya empezó: a la 1:30,
  `recordame mañana a las 9` llega en unas horas, y la ficha muestra la fecha
  (`hoy (mar 06/10) a las 9:00`).
- Cuando llega: **✅ Listo** o **⏳ 10 min** para que te lo vuelva a recordar.
- Si el bot estuvo apagado, al volver manda lo pendiente avisando la hora original, sin
  repetir los que se perdieron de un recordatorio periódico.
- Hasta 30 activos y 200 caracteres cada uno. Las frases que las reglas no entienden las
  interpreta la IA (si está activada) y el bot verifica la fecha antes de crearlo.

### Cuotas y gastos fijos

Se anotan solos cada mes, sin usar la IA, y el bot te avisa en el chat sin sonido.

| Mensaje | Resultado |
| ------- | --------- |
| `zapatillas 10.000 cuota 1 de 9` | Anota `zapatillas (1/9)` hoy y la 2/9, 3/9... el mismo día de cada mes |
| `zapatillas 90.000 en 9 cuotas` | Divide el total (`9 cuotas de 10.000` da el valor de cada una) |
| `seguro del celu 5.000 todos los meses` | Gasto fijo: hoy y el mismo día de cada mes (también `cada mes`, `mensual`, `fijo`) |
| `alquiler 300.000 el 10 de cada mes` | Gasto fijo que se anota el 10 (el 31 cae el último día en meses cortos) |
| `/fijos` | Lo que viene, con botones para dar de baja (lo ya anotado queda) |

Si el bot estuvo apagado, al volver anota lo que se perdió con su fecha original.

### IA (opcional)

Con `OPENAI_API_KEY` configurada, lo que las reglas no entienden lo interpreta `gpt-6-luna`
con **una sola consulta** por mensaje:

| Mensaje | Resultado |
| ------- | --------- |
| `el uber de ayer eran 2500` | Muestra «Importe: $2.000 → $2.500» y espera tu confirmación |
| `gasté dos lucas en el super` | Gasto de $2.000 en Supermercado |
| `hice press plano 4 de 12 con 60 y fondos 3 de 10` | Anota el entrenamiento |
| `/ia` | Consultas de hoy y del mes, tokens y costo estimado |

`uber 2000`, `borrar uber 2000` o `pecho: banco plano 4x12` **nunca** usan la IA: las reglas
son gratis e instantáneas.

### Audios

Con la IA activada también podés mandar **audios de hasta un minuto**. El bot te muestra lo
que entendió (🎙 _Uber, 2000 pesos._) y lo procesa igual que un mensaje escrito: si las
reglas lo entienden no hace otra consulta, y si no, lo interpreta la IA.

- Transcribe `gpt-4o-mini-transcribe`, el más barato: US$0,003 por minuto (un audio de
  10 segundos cuesta US$0,0005). `gpt-transcribe` es más preciso y cuesta 50% más.
- Los montos y las series se dictan igual que se escriben: «uber dos mil», «banco plano
  cuatro por doce con sesenta kilos».
- El audio se descarga en memoria y solo se envía a OpenAI para transcribirlo: el bot no
  lo guarda.
- Cada audio cuenta como una consulta en el tope diario y aparece en `/ia`.

Seguridad y costo:

- La respuesta tiene que cumplir un esquema JSON estricto y se valida antes de actuar: los
  importes tienen que estar en tu mensaje y fechas y números se vuelven a leer con las reglas.
- Borrar siempre pide confirmación; editar muestra el antes y después y espera tu OK.
- `store=false`: OpenAI no guarda las interpretaciones. Solo se envían el mensaje (o el
  audio), tus categorías y los nombres de tus ejercicios.
- Tope diario (`AI_DAILY_LIMIT`), timeout y salida limitada. Costo aproximado: entre US$0,06
  y US$0,20 cada 1.000 consultas, según cuánto aproveche el caché de OpenAI. `/ia` muestra el
  costo real del mes.
- Recomendado: crear la key en un proyecto propio de OpenAI con límite de gasto mensual.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 y las dependencias)
- Git
- Docker (opcional, para probar la imagen de producción)

## Crear el bot en Telegram

1. Hablale a [@BotFather](https://t.me/BotFather), usá `/newbot` y guardá el token.
2. En @BotFather, `/setjoingroups` → **Disable**, para que nadie pueda agregarlo a grupos.
3. Conseguí tu ID numérico con [@userinfobot](https://t.me/userinfobot).

## Configuración

Copiá `.env.example` a `.env` y completalo. `.env` está en `.gitignore`: nunca se sube.

| Variable | Obligatoria | Descripción |
| -------- | ----------- | ----------- |
| `BOT_TOKEN` | Sí | Token de @BotFather |
| `ALLOWED_USER_IDS` | Sí | IDs de Telegram autorizados, separados por coma. El resto se ignora en silencio |
| `DATABASE_URL` | No | Solo en tu computadora (por defecto `./data/asistente.db`). **No la cargues en Railway**: la imagen usa `/data/asistente.db` (el volumen) |
| `TIMEZONE` | No | Por defecto `America/Argentina/Buenos_Aires`; también es la hora de los logs |
| `LOG_LEVEL` | No | `DEBUG`, `INFO` (por defecto), `WARNING` o `ERROR` |
| `OPENAI_API_KEY` | No | Activa la IA para mensajes libres y audios. Sin key, solo reglas |
| `OPENAI_MODEL` | No | Por defecto `gpt-6-luna`, el más barato |
| `OPENAI_TRANSCRIPTION_MODEL` | No | Por defecto `gpt-4o-mini-transcribe`, el más barato |
| `AI_DAILY_LIMIT` | No | Consultas a la IA por día, textos y audios (por defecto 100; `0` la desactiva) |

Si el bot no te responde, revisá los logs: cada mensaje de un usuario no autorizado se
registra con su ID.

## Correr en local

```bash
uv sync
```

```bash
uv run alembic upgrade head
```

```bash
uv run python -m asistente
```

Para probar la misma imagen que corre en producción:

```bash
docker compose up --build
```

## Deploy en Railway

1. **New Project → Deploy from GitHub repo** y elegí este repositorio. Railway usa
   `railway.json` y construye con el `Dockerfile`.
2. Creá el volumen: en el lienzo del proyecto, **clic derecho → Volume** (o `Ctrl+K` /
   `⌘K` y escribí *volume*), elegí el servicio del bot y poné `/data` como *mount path*.
   No está en *Settings*. Sin volumen, la base se borra en cada deploy.
3. En **Variables** cargá `BOT_TOKEN` y `ALLOWED_USER_IDS` (y `OPENAI_API_KEY` si querés la
   IA). **No copies `DATABASE_URL`**: la imagen ya guarda la base en `/data/asistente.db`,
   dentro del volumen, y si recibe la ruta local (`./data/...`) no arranca.
4. Activá los backups automáticos del volumen.
5. Dejá **una sola réplica**: los volúmenes no admiten más y Telegram solo permite un
   proceso haciendo polling por bot.

El contenedor aplica las migraciones al arrancar y después inicia el bot como usuario sin
privilegios. Más detalles en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#despliegue-en-railway).

## Desarrollo

```bash
uv sync
```

```bash
uv run pre-commit install
```

Comandos de calidad (los mismos que corre el CI):

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

```bash
uv run pytest
```

## Convenciones

- Una rama por feature; nunca se commitea directo a `main`.
- [Conventional Commits](https://www.conventionalcommits.org/) en inglés.
- Los secretos van solo en `.env` (ignorado por git) o en las variables del hosting.
