# Arquitectura

## Stack

| Pieza | Tecnología |
| ----- | ---------- |
| Lenguaje | Python 3.12 (compatible con 3.11) |
| Framework del bot | aiogram 3 (asyncio) |
| Base de datos | SQLite (modo WAL) vía `aiosqlite` |
| ORM y migraciones | SQLAlchemy 2 (async) + Alembic |
| Configuración | pydantic-settings |
| Dependencias | uv (`uv.lock` versionado) |
| Calidad | ruff, mypy `--strict`, pytest, pre-commit, gitleaks |
| Despliegue | Docker + Railway (volumen montado en `/data`) |

## Estructura

```text
src/asistente/
├── __main__.py            # python -m asistente
├── config.py              # Settings tipados desde variables de entorno
├── logging_config.py      # Logging con enmascarado de secretos
├── core/                  # Utilidades puras, sin I/O
│   ├── dates.py           # Zona horaria, meses en español, fechas relativas
│   ├── money.py           # Parseo y formato de pesos argentinos
│   └── text.py            # Normalización (minúsculas, sin acentos)
├── db/                    # Infraestructura de persistencia
│   ├── base.py            # DeclarativeBase, convenciones de nombres y mixins
│   ├── engine.py          # Engine async y PRAGMAs de SQLite
│   ├── registry.py        # Importa todos los modelos (para Alembic)
│   └── types.py           # UTCDateTime
├── users/                 # Dominio: usuarios
├── finance/               # Dominio: finanzas
│   ├── models.py          # Account, Category, CategoryKeyword, Transaction
│   ├── defaults.py        # Categorías, palabras clave y cuentas iniciales
│   ├── parser.py          # "uber 2000 ayer" → ParsedEntry
│   ├── matching.py        # Búsqueda de palabras clave
│   ├── repository.py      # Acceso a datos (consultas)
│   ├── service.py         # Reglas de negocio
│   └── reports.py         # Resumen mensual
└── bot/                   # Adaptador de Telegram
    ├── app.py             # Arma Bot + Dispatcher y arranca el polling
    ├── commands.py        # Menú de comandos
    ├── middlewares/       # Acceso, sesión de DB, usuario
    └── handlers/          # Un paquete por dominio (common, finance, ...)
migrations/                # Alembic
tests/                     # unit/ (lógica pura) e integration/ (DB + bot)
```

## Capas

```mermaid
flowchart LR
    TG[Telegram] -->|long polling| D[Dispatcher aiogram]
    D --> A[AccessMiddleware<br/>whitelist + chat privado]
    A --> S[DbSessionMiddleware<br/>una transacción por update]
    S --> U[UserMiddleware<br/>usuario actual]
    U --> H[Handlers]
    H --> SV[Services<br/>reglas de negocio]
    SV --> R[Repositories<br/>consultas]
    R --> DB[(SQLite)]
    SV --> C[core<br/>parseo y formato puros]
```

- **Handlers**: solo traducen entre Telegram y los servicios (texto, botones y estados).
- **Services**: validan, aplican reglas y garantizan que cada operación sea del usuario actual.
- **Repositories**: consultas SQLAlchemy; no conocen Telegram.
- **core**: funciones puras y testeables sin base ni red.

Cada update se procesa dentro de una única transacción: si el handler falla, se hace rollback.

## Modelo de datos (finanzas)

```mermaid
erDiagram
    users ||--o{ accounts : tiene
    users ||--o{ categories : tiene
    users ||--o{ transactions : registra
    categories ||--o{ category_keywords : "se detecta por"
    accounts ||--o{ transactions : mueve
    categories ||--o{ transactions : clasifica

    users {
        int id PK
        bigint telegram_id UK
    }
    accounts {
        int id PK
        int user_id FK
        string name
        string slug
        json aliases
        bool is_default
    }
    categories {
        int id PK
        int user_id FK
        string name
        string emoji
        string kind "expense | income"
        bool is_fallback
    }
    category_keywords {
        int id PK
        int user_id FK
        int category_id FK
        string keyword UK
    }
    transactions {
        int id PK
        int user_id FK
        int account_id FK
        int category_id FK
        string kind "expense | income"
        bigint amount_cents "mayor a 0"
        string description
        datetime occurred_at "UTC"
    }
```

- Los importes se guardan en **centavos enteros** y siempre positivos; el tipo
  (`expense`/`income`) define el signo.
- Las fechas se guardan en **UTC**; los rangos de cada mes se calculan en hora de
  Buenos Aires y se convierten a UTC antes de consultar.
- Todas las consultas filtran por `user_id`: un `id` de movimiento ajeno, por ejemplo uno
  manipulado en un botón, no devuelve nada.

## Seguridad

| Riesgo | Mitigación |
| ------ | ---------- |
| Que otra persona use el bot | `ALLOWED_USER_IDS` obligatorio; los updates de otros usuarios o de grupos se descartan sin responder |
| Filtración del token | Solo en variables de entorno (`.env` está en `.gitignore`), tipo `SecretStr`, enmascarado en logs y errores de validación ocultos |
| Secretos commiteados | `gitleaks` en pre-commit y en CI, más `detect-private-key` |
| Superficie de red | Long polling, sin puertos HTTP expuestos; la base es un archivo en el volumen, sin acceso remoto |
| Inyección SQL | Solo consultas parametrizadas de SQLAlchemy; `hide_parameters` en el engine |
| Manipulación de botones (IDOR) | Toda lectura o escritura valida que el registro pertenezca al usuario |
| Inyección de formato | Todo texto del usuario se escapa antes de enviarse en HTML |
| Contenedor | Imagen slim multi-stage, sin herramientas de build, el proceso corre como usuario sin privilegios |
| Dependencias | Versiones fijadas en `uv.lock` y Dependabot semanal |
| CI | Permisos mínimos (`contents: read`) |

## Despliegue en Railway

1. Crear un servicio desde el repositorio de GitHub; Railway detecta `railway.json` y
   construye con el `Dockerfile`.
2. Agregar un **Volume** montado en `/data`. Sin volumen, los datos se pierden en cada deploy.
3. Variables del servicio: `BOT_TOKEN`, `ALLOWED_USER_IDS` y
   `DATABASE_URL=sqlite+aiosqlite:////data/asistente.db`.
4. Activar los backups automáticos del volumen.

Al arrancar, el contenedor:

1. Corre como root solo para darle la propiedad de `/data` al usuario `app`, porque
   Railway monta los volúmenes como root.
2. Baja privilegios al usuario `app`.
3. Aplica las migraciones (`alembic upgrade head`). No se usa el pre-deploy de Railway
   porque corre en otro contenedor que no monta el volumen.
4. Inicia el bot.

## Tests

- `tests/unit`: parseo de importes y fechas, parser de movimientos, configuración, logging
  y middlewares, sin I/O.
- `tests/integration`: servicios contra una base SQLite temporal, un test que verifica que
  las migraciones coinciden con los modelos (upgrade y downgrade) y flujos completos del bot
  con un `Bot` simulado que no hace llamadas a Telegram.
