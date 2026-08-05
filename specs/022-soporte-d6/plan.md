# Implementation Plan: Soporte D6

**Branch**: `022-soporte-d6` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-soporte-d6/spec.md`

## Summary

Dar superficie en `apps/web` a los 11 endpoints de `aerohub_support`
(S1.8), hasta ahora sin ningún consumidor de frontend (D6/M8 no tiene
`ruta` en `roles_modulos.py`). A diferencia de S1.15-S1.19, el backend
no necesita ningún endpoint nuevo -- este sprint es 100% frontend: una
vista nueva `soporte/panel-soporte` con tres secciones (bandeja de
tickets con SLA visible y detalle con hilo de mensajes, base de
conocimientos con aviso explícito de contenido compartido entre
tenants, changelog publicable), enlazada manualmente desde el shell
por scope (mismo mecanismo que tarifarios/informes), sin construir
vista para `GET /support/observabilidad/uptime` (decisión de producto
ya tomada -- Grafana lo resuelve).

## Technical Context

**Language/Version**: Python 3.12 (backend, sin cambios) / TypeScript 5 + Angular standalone (frontend)

**Primary Dependencies**: FastAPI + SQLAlchemy Core (backend, ya existente) / Angular signals, `HttpClient` (frontend)

**Storage**: MonetDB (sin DDL nuevo -- las tablas `support.ticket`, `support.ticket_mensaje`, `support.articulo_kb`, `support.changelog`, `support.changelog_item` ya existen desde S1.8)

**Testing**: pytest contra MonetDB real (Docker) para confirmar que los scopes ya alcanzan lo que la vista necesita; sin tests automatizados de frontend (mismo criterio que S1.15-S1.19)

**Target Platform**: Docker (gateway + web), navegador

**Project Type**: Web application (monorepo backend + frontend ya establecido)

**Performance Goals**: N/A -- sin requisito de performance nuevo, reutiliza endpoints ya verificados en S1.8

**Constraints**: Ninguna ruta requiere licencia de módulo (research.md Decisión 7 de S1.8, D6 es capacidad de plataforma); `articulo_kb` no tiene `tenant_id` -- debe quedar explícito en la interfaz

**Scale/Scope**: 1 vista nueva Angular (3 secciones), 1 servicio HTTP nuevo, 2-3 líneas de enlace en el shell -- sin cambios de backend

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Aislamiento Multi-Tenant Fail-Closed**: cumple sin cambios --
  `tickets`/`mensajes` son tenant-scoped y ya pasan por
  `contexto_tenant_id()` desde S1.8; `articulo_kb`/`changelog` son
  deliberadamente globales (ya lo eran desde S1.8, este sprint no
  cambia su alcance, solo lo hace visible con el aviso explícito que
  exige FR-008). Sin tabla nueva, sin alcance nuevo que registrar.
- **II. Arquitectura Modular por Capas**: sin cambios de backend --
  no se toca `domain/`/`application/`/`infrastructure/` de
  `aerohub_support`. El frontend nuevo vive en
  `apps/web/src/app/soporte/`, mismo patrón que `compliance/` (S1.19).
- **III. Verificación Empírica Obligatoria**: se confirma con un test
  de integración liviano que los 3 roles relevantes (`role_sre`,
  `role_support`, `role_tenant_admin`) ya alcanzan los endpoints
  `support:leer`/`support:escribir` sin ningún cambio de scopes (a
  diferencia de S1.16/S1.19, se espera que este test simplemente
  confirme "sin hallazgo", no corrija uno) -- MonetDB real, sin mocks.
  Build de producción de `apps/web` en verde antes de cerrar.
- **IV. Calidad Continua en Verde**: `ruff`/`mypy` sobre cualquier
  archivo Python tocado (esperado: ninguno, o como mucho
  `roles_modulos.py` si el gate de scopes revela lo contrario);
  regresión completa de la suite de soporte existente sin cambios.
- **V. Aprobación Explícita**: sin commit hasta pedido explícito,
  igual que S1.15-S1.19.

Sin violaciones -- no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/022-soporte-d6/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
services/support/aerohub_support/    # SIN CAMBIOS -- 11 endpoints ya existen
├── api/router.py
├── application/
├── domain/
└── infrastructure/

packages/contracts/aerohub_contracts/
└── roles_modulos.py                 # solo se toca SI el gate de scopes revela un hallazgo

apps/web/src/app/
├── soporte/                         # NUEVO -- mismo patron que compliance/ (S1.19)
│   ├── soporte.service.ts           # NUEVO: interfaces + 11 metodos HTTP
│   └── panel-soporte/
│       ├── panel-soporte.ts         # NUEVO
│       ├── panel-soporte.html       # NUEVO
│       └── panel-soporte.scss       # NUEVO
├── app.routes.ts                    # + ruta soporte/panel
└── shell/
    ├── shell.ts                     # + puedeVerSoporte() (por scope, no modulosConVista)
    └── shell.html                   # + enlace condicional

tests/integration/
└── test_soporte_hub.py              # NUEVO -- gate de scopes + smoke de los 3 flujos
```

**Structure Decision**: Web application ya establecida (`apps/web` +
`services/<modulo>`). Este sprint agrega únicamente el árbol
`apps/web/src/app/soporte/` (mismo patrón que `compliance/` de S1.19)
y una vista enlazada manualmente desde el shell, porque D6 no ocupa
ningún módulo M1-M9 con ruta libre en `modulosConVista`.

## Complexity Tracking

*Sin violaciones de la Constitution Check -- sección no aplica.*
