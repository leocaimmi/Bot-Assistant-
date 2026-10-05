# Bot Asistente

Bot de Telegram personal para registrar gastos e ingresos en pesos argentinos y llevar la
rutina del gimnasio, escribiendo mensajes como `uber 2000` o `gym 47.000`.

- Plan y fases: [docs/ROADMAP.md](docs/ROADMAP.md)
- Arquitectura, modelo de datos y seguridad: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

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
3. En **Variables** cargá `BOT_TOKEN` y `ALLOWED_USER_IDS`. La imagen ya guarda la base
   en `/data/asistente.db`, dentro del volumen.
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
