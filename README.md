# Bot Asistente

Bot de Telegram personal para registrar gastos e ingresos en pesos argentinos y llevar la
rutina del gimnasio, escribiendo mensajes como `uber 2000` o `gym 47.000`.

- Plan y fases: [docs/ROADMAP.md](docs/ROADMAP.md)
- Arquitectura, modelo de datos y seguridad: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 y las dependencias)
- Git

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
