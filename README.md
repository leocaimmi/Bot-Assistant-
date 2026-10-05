# Bot Asistente

Bot de Telegram personal para registrar gastos e ingresos en pesos argentinos y llevar la
rutina del gimnasio, escribiendo mensajes como `uber 2000` o `gym 47.000`.

- Plan y fases: [docs/ROADMAP.md](docs/ROADMAP.md)
- Arquitectura, modelo de datos y seguridad: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Uso

| Mensaje | Resultado |
| ------- | --------- |
| `uber 2000` | Gasto de $2.000 en 🚗 Transporte, cuenta Mercado Pago |
| `gym 47.000` | Gasto de $47.000 en 🏋️ Gimnasio |
| `transferencia utn 200.000` | Ingreso de $200.000 en 🔁 Transferencias |
| `super 15.430,50 efectivo` | Gasto en 🛒 Supermercado pagado en Efectivo |
| `nafta 30k ayer` | Gasto de $30.000 con fecha de ayer |
| `+ 50000 venta bici` | El `+` fuerza ingreso; el `-` fuerza gasto |
| `eliminar uber 2000` / `borrar el último` | Busca el movimiento y pide confirmación para borrarlo |
| `cambiar uber 2000 a 2500` | Corrige el importe (también `a comida` o `a ayer`) |
| `cambiar uber 2000` | Muestra los botones para editarlo |
| `/movimientos [mes]` | Lista paginada; tocá un número para editarlo o borrarlo |
| `/resumen [mes]` | Gastos por categoría (con detalle: uber, sube...), ingresos por cuenta y balance |
| `/categorias` | Categorías y las palabras que las eligen |
| `/palabra nafta auto` | Enseña o mueve una palabra clave a otra categoría |
| `/nueva_categoria 🚙 Auto` | Crea una categoría (`ingreso` adelante para ingresos) |

Cada movimiento registrado llega con botones para cambiar la categoría, el importe, la
descripción, la fecha, la cuenta o el tipo, y para borrarlo (con confirmación).

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

### IA (opcional)

Con `OPENAI_API_KEY` configurada, lo que las reglas no entienden lo interpreta `gpt-5.4-nano`
con **una sola consulta** por mensaje:

| Mensaje | Resultado |
| ------- | --------- |
| `el uber de ayer eran 2500` | Muestra «Importe: $2.000 → $2.500» y espera tu confirmación |
| `gasté dos lucas en el super` | Gasto de $2.000 en Supermercado |
| `hice press plano 4 de 12 con 60 y fondos 3 de 10` | Anota el entrenamiento |
| `/ia` | Consultas de hoy y del mes, tokens y costo estimado |

`uber 2000`, `borrar uber 2000` o `pecho: banco plano 4x12` **nunca** usan la IA: las reglas
son gratis e instantáneas.

Seguridad y costo:

- La respuesta tiene que cumplir un esquema JSON estricto y se valida antes de actuar: los
  importes tienen que estar en tu mensaje y fechas y números se vuelven a leer con las reglas.
- Borrar siempre pide confirmación; editar muestra el antes y después y espera tu OK.
- `store=false`: OpenAI no guarda los pedidos. Solo se envían el mensaje, tus categorías y
  los nombres de tus ejercicios.
- Tope diario (`AI_DAILY_LIMIT`), timeout y salida limitada. Costo aproximado: US$0,25 cada
  1.000 consultas.
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
| `DATABASE_URL` | No | Por defecto `./data/asistente.db` en local y `/data/asistente.db` (el volumen) en Docker |
| `TIMEZONE` | No | Por defecto `America/Argentina/Buenos_Aires` |
| `LOG_LEVEL` | No | `DEBUG`, `INFO` (por defecto), `WARNING` o `ERROR` |
| `OPENAI_API_KEY` | No | Activa la IA para mensajes libres. Sin key, solo reglas |
| `OPENAI_MODEL` | No | Por defecto `gpt-5.4-nano` |
| `AI_DAILY_LIMIT` | No | Consultas a la IA por día (por defecto 100; `0` la desactiva) |

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
2. En el servicio: **Settings → Volumes → Add Volume** montado en `/data`.
   Sin volumen, la base se borra en cada deploy.
3. En **Variables** cargá `BOT_TOKEN` y `ALLOWED_USER_IDS` (y `OPENAI_API_KEY` si querés la
   IA). La imagen ya guarda la base en `/data/asistente.db`, dentro del volumen.
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
