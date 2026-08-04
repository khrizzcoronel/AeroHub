# Implementation Plan: Informes operativos (RF-I)

**Branch**: `020-informes-operativos` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/020-informes-operativos/spec.md`

## Summary

Formalizar la familia RF-I01-RF-I04 con 6 informes (1 simple + 1
compuesto) sobre horizonte operativo (MonetDB), uno por módulo dueño de
su tabla raíz: AODB, Gates, Ground Ops, Billing, Tenancy, Compliance.
Cada módulo gana `application/informes.py` + `infrastructure/consultas_informe.py`
+ 2 rutas `GET /<modulo>/informes/<simple|compuesto>?formato=csv|json`.
Frontend: un único componente reutilizable `informes/panel-informe`
consumido desde cada módulo con una configuración declarativa distinta
(no 6 componentes casi idénticos) — construye el primitivo `.ah-informe`
una sola vez.

## Technical Context

**Language/Version**: Python 3.12 (6 servicios `services/*`), TypeScript / Angular 19 (`apps/web`)

**Primary Dependencies**: FastAPI, SQLAlchemy Core (agregación `func.sum`/`func.count`/`func.avg` en el servidor), `aerohub_repository` (guardián de tenant + `registrar_auditoria`), Angular standalone components + signals

**Storage**: MonetDB -- sin DDL nuevo, los 6 informes leen tablas ya existentes de cada módulo (redeclaradas donde haga falta, ADR-017 §5.4)

**Testing**: pytest de integración vía `TestClient` (mismo patrón que `test_billing_tarifarios_conciliacion.py`) -- 1 suite por módulo, verificando SC-002 (subtotales == total) y SC-003 (conciliación de facturación) contra datos reales

**Target Platform**: Docker (gateway :8000, web :4200)

**Project Type**: Web (6 backends + 1 frontend compartido)

**Performance Goals**: N/A -- agregaciones de bajo volumen (tenant único, período acotado), sin requisito de rendimiento distinto del resto de `apps/web`

**Constraints**: Totales SIEMPRE en el servidor (nunca sumados en Angular); CSV desde el MISMO endpoint que JSON (`?formato=csv`), nunca un endpoint paralelo; cero cambios a la lógica de negocio de los 6 módulos (informes son de solo lectura); RF-I04 (auditoría) solo en M5/M9, no en los otros 4.

**Scale/Scope**: 12 endpoints GET nuevos (6 módulos × 2), 1 componente frontend reutilizable con 6 configuraciones, 1 primitivo CSS nuevo (`.ah-informe`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Aislamiento fail-closed (tenant)**: cada consulta de informe filtra
  por `contexto_tenant_id()`, igual que cualquier otra consulta del
  módulo -- un informe no es un camino de acceso nuevo (spec.md Edge
  Cases). PASA.
- **Arquitectura modular por capas**: cada informe vive en
  `infrastructure/consultas_informe.py` → `application/informes.py` →
  `api/router.py` del módulo dueño de su tabla raíz -- ningún módulo
  importa `domain`/`application` de otro (redeclaración local si hace
  falta una tabla ajena, mismo patrón que gates/ramp sobre `ops.vuelo`).
  PASA.
- **Verificación empírica (Principio III)**: SC-002 (subtotales==total)
  y SC-003 (conciliación de facturación) se verifican con pytest contra
  MonetDB real, no solo por inspección del código.
- **Calidad en verde**: ruff/mypy/bandit/import-linter sobre los 6
  servicios modificados antes de cerrar.
- **Aprobación explícita**: no se commitea sin pedido explícito.

**Decisión de complejidad** (única, documentada en Complexity Tracking):
un componente Angular compartido en vez de 6 componentes por módulo --
NO es una violación de un gate, es una simplificación deliberada frente
al patrón "una vista por módulo" ya usado en S1.15-S1.17 (ver research.md
Decisión 1).

## Project Structure

### Documentation (this feature)

```text
specs/020-informes-operativos/
├── plan.md
├── research.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
services/aodb/aerohub_aodb/{infrastructure/consultas_informe.py, application/informes.py}
services/gates/aerohub_gates/{infrastructure/consultas_informe.py, application/informes.py}
services/ramp/aerohub_ramp/{infrastructure/consultas_informe.py, application/informes.py}
services/billing/aerohub_billing/{infrastructure/consultas_informe.py, application/informes.py}
services/tenancy/aerohub_tenancy/{infrastructure/consultas_informe.py, application/informes.py}
services/compliance/aerohub_compliance/{infrastructure/consultas_informe.py, application/informes.py}
# cada uno + 2 rutas GET /<prefijo>/informes/{simple,compuesto} en su api/router.py

apps/web/src/app/_primitivos.scss           # + .ah-informe
apps/web/src/app/informes/
├── informe.service.ts                       # 1 servicio, 6 métodos (uno por módulo)
└── panel-informe/                           # 1 componente reutilizable, config por @Input
    ├── panel-informe.ts
    ├── panel-informe.html
    └── panel-informe.scss
# consumido desde una ruta nueva por modulo: /aodb/informes, /puertas/informes,
# /rampa/informes, /billing/informes, /tenants/informes, /compliance/informes

tests/integration/
├── test_aodb_informes.py
├── test_gates_informes.py
├── test_ramp_informes.py
├── test_billing_informes.py
├── test_tenancy_informes.py
└── test_compliance_informes.py
```

**Structure Decision**: Backend replica el patrón ya usado en S1.15-S1.17
(extensión de capas existentes, sin paquete nuevo) por cada uno de los 6
módulos. Frontend rompe deliberadamente el patrón "una vista por módulo"
de S1.15-S1.17: en vez de 6 componentes casi idénticos, un único
`panel-informe` parametrizado por `@Input() config` (título, columnas,
filtros, endpoint) — ver research.md Decisión 1.

## Complexity Tracking

| Decisión | Por qué | Alternativa más simple descartada |
|---|---|---|
| 1 componente Angular compartido para 6 informes, en vez de 6 componentes por módulo | Los 6 informes comparten exactamente la misma forma (parámetros/filas/subtotales/total, exportar CSV) -- 6 copias del mismo componente violarían "tres líneas similares está bien, una abstracción prematura no" en la dirección contraria: aquí la abstracción NO es prematura, es el mismo componente repetido 6 veces | 6 componentes independientes (`aodb/panel-informes`, `gates/panel-informes`, ...) -- rechazado, duplicaría ~200 líneas de TS/HTML casi idénticas 6 veces sin ninguna diferencia real de comportamiento, solo de configuración |
