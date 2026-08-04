# Implementation Plan: Tarifarios y conciliación de pax

**Branch**: `019-tarifarios-conciliacion-pax` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/019-tarifarios-conciliacion-pax/spec.md`

## Summary

Cerrar la superficie de usuario de M5 Billing sobre tarifarios (RF-T10) y
conciliación de pax (RF-O15), cuyos 6 endpoints de escritura (S1.6) no
tienen ningún consumidor en `apps/web`. Se agregan 2 endpoints GET de
listado (tarifarios con sus conceptos, conciliaciones) tenant-scoped sin
lógica de negocio nueva, y una vista nueva `billing/tarifarios` con dos
secciones (mismo patrón de S1.16: una ruta, dos tablas relacionadas). No
hay gap de scopes esta vez -- `role_tenant_admin` y `role_billing_officer`
ya tienen `billing:escribir`.

## Technical Context

**Language/Version**: Python 3.12 (backend, `services/billing`), TypeScript / Angular 19 (frontend, `apps/web`)

**Primary Dependencies**: FastAPI, SQLAlchemy Core (sin ORM), `aerohub_repository` (guardián de tenant), Angular standalone components + signals

**Storage**: MonetDB (esquema `billing.*`, tablas `tarifario`/`tarifario_concepto`/`concepto_cargo`/`conciliacion_pax` ya existentes desde S1.6 -- sin DDL nuevo)

**Testing**: pytest de integración contra MonetDB real en Docker (mismo patrón que `tests/integration/test_fids_administracion.py` de S1.16); ruff/mypy/bandit/import-linter

**Target Platform**: Docker (gateway :8000, web :4200) -- Windows host con Git Bash

**Project Type**: Web (backend `services/billing/aerohub_billing` + frontend `apps/web`)

**Performance Goals**: N/A (listados administrativos de bajo volumen, sin requisito de rendimiento específico distinto del resto de `apps/web`)

**Constraints**: Ningún cambio al motor de facturación (`calcular_facturacion`) ni a la lógica de dominio de tarifarios/conciliación ya cerrada en S1.6; `diferencia` y `total` siguen siendo valores derivados, nunca columnas ni inputs.

**Scale/Scope**: 2 endpoints GET nuevos, 1 vista nueva de 2 secciones (tarifarios, conciliaciones), sin cambios de rol/scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Aislamiento fail-closed (tenant)**: ambos listados nuevos filtran por
  `contexto_tenant_id()`, mismo patrón que `listar_tarifarios_vigentes`/
  `obtener_conciliacion_por_id` ya existentes. PASA.
- **Arquitectura modular por capas**: los listados van en
  `infrastructure/consultas.py` (ya existe, se extiende) →
  `application/consultar.py` (ya existe, se extiende) → `api/router.py`
  (se agregan 2 rutas GET). Ninguna regla de negocio nueva. PASA.
- **Verificación empírica (Principio III)**: se corrigieron 2
  suposiciones incorrectas del spec inicial tras leer
  `conciliar_pax.py`/`domain/conciliacion_pax.py` reales -- `conciliar`
  EXIGE diferencia cero (no lo contrario), y `pax_registrado_sistema` es
  un input al registrar, no un valor que el sistema calcula solo. Se
  corrigió `spec.md` antes de continuar, no se implementó sobre la
  suposición original. Se verificará de nuevo contra MonetDB real con
  pytest antes de cerrar el sprint.
- **Calidad en verde**: se correrán ruff/mypy/bandit/import-linter sobre
  `services/billing` antes de cerrar.
- **Aprobación explícita**: no se commitea sin pedido explícito del
  usuario (regla ya establecida, sin cambios).

Sin violaciones -- no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/019-tarifarios-conciliacion-pax/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── quickstart.md        # Fase 1
├── checklists/requirements.md
└── tasks.md              # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
services/billing/aerohub_billing/
├── infrastructure/consultas.py   # + listar_tarifarios, listar_conceptos_de_tarifario (ya existe, reusar)
├── application/consultar.py       # + consultar_tarifarios, consultar_conciliaciones
└── api/router.py                  # + GET /billing/tarifarios, GET /billing/conciliaciones

apps/web/src/app/billing/
├── billing.service.ts (existente -- se extiende: listarTarifarios, crearTarifario,
│   agregarConcepto, activarTarifario, listarConciliaciones, registrarConciliacion, conciliar)
├── panel-facturas/               # existente, S1.13 -- sin cambios
└── panel-tarifarios/             # NUEVO -- 2 secciones: tarifarios, conciliaciones

tests/integration/
└── test_billing_tarifarios_conciliacion.py   # NUEVO
```

**Structure Decision**: Mismo patrón de capas que S1.15/S1.16 -- extensión
de `infrastructure/`/`application/`/`api/` existentes en
`aerohub_billing` (sin paquete nuevo), y una vista nueva standalone en
`apps/web/src/app/billing/panel-tarifarios/` junto a `panel-facturas/`
ya existente. `modulosConVista` solo admite una ruta por módulo
(`modulo.ruta`, ya ocupada por `/billing/facturas`) -- la ruta nueva se
expone como enlace manual en el shell (`puedeVerTarifarios`, computed
por scope `billing:escribir`), mismo mecanismo ya usado para
`usuarios`/`api-keys`/`licencias`/`tenants` (ninguno de esos es un
módulo M1-M9 tampoco). Ver Decisión 1 en `research.md`.

## Complexity Tracking

*Sin violaciones -- tabla omitida.*

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
