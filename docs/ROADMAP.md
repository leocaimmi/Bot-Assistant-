# Roadmap

Plan de trabajo del bot asistente personal de Telegram.

## Objetivo

Un bot de Telegram de uso personal (un solo usuario) para:

1. **Finanzas**: registrar gastos e ingresos en pesos argentinos escribiendo texto libre
   (`uber 2000`, `gym 47.000`, `transferencia utn 200.000`), editarlos, listarlos y obtener
   un resumen mensual por categoría y por cuenta.
2. **Gimnasio**: llevar la rutina: días entrenados, ejercicios, series × repeticiones y peso.

## Principios

- **Seguridad primero**: el bot solo responde a IDs de Telegram autorizados, los secretos
  viven únicamente en variables de entorno y no se expone ningún puerto HTTP.
- **Formato argentino**: importes como `$200.000` o `$1.500,50`, fechas `dd/mm/aaaa` y hora
  de Buenos Aires (`America/Argentina/Buenos_Aires`).
- **Fricción mínima**: registrar un movimiento es mandar un mensaje; corregirlo, un toque.
- **Monolito modular**: cada dominio (finanzas, gym) vive en su propio paquete con sus
  modelos, servicios y handlers, así sumar módulos no toca lo existente.

## Fases

| Fase | Rama | Estado |
| ---- | ---- | ------ |
| 0. Base del repositorio | `chore/project-setup` | En curso |
| 1. Núcleo del bot | `feat/bot-core` | En curso |
| 2. Finanzas: movimientos | `feat/finance-transactions` | En curso |
| 3. Finanzas: resumen mensual | `feat/finance-reports` | En curso |
| 4. Finanzas: categorías y palabras clave | `feat/finance-categories` | En curso |
| 5. Gimnasio | `feat/gym-tracker` | Próxima sesión |
| 6. Mejoras | varias | Backlog |

### Fase 0: base del repositorio

- Proyecto Python gestionado con `uv` (`pyproject.toml` + `uv.lock`).
- Calidad: `ruff` (lint + formato), `mypy --strict` y `pytest`.
- `pre-commit` con escaneo de secretos (`gitleaks`) y detección de claves privadas.
- CI en GitHub Actions: lint, tipos, tests y escaneo de secretos en cada push.
- Dependabot para dependencias de Python, GitHub Actions y Docker.

### Fase 1: núcleo del bot

- Configuración tipada con `pydantic-settings` que falla rápido si falta algo.
- Logging que enmascara secretos aunque aparezcan en un error.
- SQLite + SQLAlchemy 2 async + Alembic.
- Middleware de acceso: whitelist de usuarios y solo chats privados.
- Comandos `/start`, `/ayuda` y `/cancelar`.
- Imagen Docker con usuario sin privilegios y despliegue en Railway con volumen persistente.

### Fase 2: finanzas, movimientos

- Texto libre → movimiento: detecta importe, fecha, cuenta, categoría y tipo.
- Cuentas: Mercado Pago (por defecto) y Efectivo.
- Categorías con palabras clave (`uber` → Transporte, `gym` → Gimnasio, ...).
- Ficha de cada movimiento con botones: cambiar categoría, importe, descripción, fecha,
  cuenta, gasto/ingreso o borrar (con confirmación).
- `/movimientos` paginado, con filtro opcional por mes.

### Fase 3: finanzas, resumen mensual

- `/resumen [mes]`: total gastado por categoría (con detalle: uber, sube, didi...),
  ingresos por cuenta y balance del mes, con botones para navegar entre meses.

### Fase 4: finanzas, categorías

- `/categorias`: lista categorías y sus palabras clave.
- `/palabra <palabra> <categoría>`: enseña o mueve una palabra clave
  (por ejemplo `/palabra nafta auto`).
- `/nueva_categoria <nombre>`: crea categorías propias de gasto o ingreso.

### Fase 5: gimnasio (próxima sesión)

Modelo de datos:

- `exercises`: catálogo de ejercicios del usuario (nombre normalizado, alias).
- `workouts`: una sesión de entrenamiento (fecha, notas, inicio y fin).
- `workout_sets`: cada serie (ejercicio, orden, repeticiones y peso en kg).

Sintaxis prevista:

| Mensaje | Resultado |
| ------- | --------- |
| `/entreno` | Abre la sesión de hoy |
| `press banca 4x10 60` | 4 series de 10 repeticiones con 60 kg |
| `sentadilla 80x8 85x6 90x5` | 3 series con peso × repeticiones distintos |
| `dominadas 3x12` | 3 series de 12 con peso corporal |
| `/fin` | Cierra la sesión y muestra el resumen |
| `/historial press banca` | Progresión del ejercicio y récord personal |
| `/semana` | Días entrenados y volumen de la semana |

### Fase 6: mejoras (backlog)

- Gastos recurrentes (por ejemplo, la cuota del gimnasio todos los meses).
- Presupuestos por categoría con aviso al acercarse al límite.
- `/exportar` a CSV y `/backup`, que envía la base por Telegram.
- Registro de peso corporal.
- Gráficos mensuales como imagen.
- Movimientos en dólares.
- Recordatorios.

## Cómo se va a usar

| Mensaje | Qué hace |
| ------- | -------- |
| `uber 2000` | Gasto de $2.000 en Transporte, cuenta Mercado Pago, ahora |
| `gym 47.000` | Gasto de $47.000 en Gimnasio |
| `transferencia utn 200.000` | Ingreso de $200.000 a Mercado Pago |
| `super 15.430,50 efectivo` | Gasto de $15.430,50 en Supermercado, pagado en efectivo |
| `nafta 30k ayer` | Gasto de $30.000 en Transporte con fecha de ayer |
| `+ 50000 venta bici` | El `+` fuerza que sea ingreso |
| `- 5000 transferencia a juan` | El `-` fuerza que sea gasto |
| `/movimientos` | Últimos movimientos, con botones para editar |
| `/resumen septiembre` | Resumen de septiembre |

Formatos de importe aceptados: `2000`, `2.000`, `1.500,50`, `2k`, `1,5k`, `200 mil`,
`2 lucas`, `1 palo`, `$2000`.

Fechas aceptadas: `hoy`, `ayer`, `anteayer`, `15/09`, `15/09/2026`.

## Decisiones

| Tema | Decisión | Motivo |
| ---- | -------- | ------ |
| Lenguaje | Python 3.12 + aiogram 3 | Async, tipado y muy usado para bots |
| Base de datos | SQLite en un volumen de Railway | Un solo usuario: más simple y rápido, sin costo extra y sin red expuesta. El plan free de Supabase pausa los proyectos inactivos |
| Portabilidad | SQLAlchemy + Alembic | Pasar a PostgreSQL es cambiar `DATABASE_URL` y migrar los datos |
| Hosting | Railway, una réplica | Ya hay plan Pro; los volúmenes admiten una sola réplica, que es lo que necesita un bot con polling |
| Recepción de mensajes | Long polling | No hay endpoint HTTP público, así que no hay superficie de ataque entrante |
| Importes | Enteros en centavos | Sin errores de redondeo de punto flotante |
| Fechas | UTC en la base, Buenos Aires en pantalla | Comparaciones correctas y formato local |
| Nafta | Categoría Transporte por defecto | Se puede mover con `/palabra nafta <categoría>` |
| "transferencia" | Se toma como ingreso | Según el ejemplo `transferencia utn 200.000`; con `-` adelante se fuerza gasto |

## Flujo de trabajo con Git

- Una rama por feature, nunca commits directos a `main`.
- Conventional Commits en inglés (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `build:`).
- Las ramas de código están apiladas porque cada una depende de la anterior:
  `main` ← `chore/project-setup` ← `feat/bot-core` ← `feat/finance-transactions`
  ← `feat/finance-reports` ← `feat/finance-categories`.
- Orden de merge a `main`: `docs/project-plan` (independiente) y después las ramas de
  código en el orden de la cadena.
