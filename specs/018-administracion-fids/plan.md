# Implementation Plan: Administración de FIDS

**Branch**: `main` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-administracion-fids/spec.md`

## Summary

Segundo sprint de la Fase 1.5 (`docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.2). Da superficie de usuario a M2 FIDS, que hoy solo tiene 3 endpoints de escritura sin consumidor (`POST /fids/plantillas`, `POST /fids/pantallas`, `PATCH /fids/pantallas/{id}/plantilla`) y ninguna ruta en `apps/web` (`ruta: None` en `roles_modulos.py`). Agrega los 2 endpoints de listado que hoy no existen (`GET /fids/plantillas`, `GET /fids/pantallas` — este último es el "tablero de telemetría" del plan: estado + última señal ya calculados por el backend, no lógica nueva) y un catálogo de solo lectura de terminales (redeclarado localmente, mismo patrón que S1.15 con aeropuertos). Construye una vista nueva en `apps/web` con el patrón ya consolidado (tabla + panel de búsqueda + modal), y activa la ruta de M2 en el mapeo rol-módulo.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy Core (ya existentes) — ningún paquete nuevo.

**Storage**: MonetDB — `ops.plantilla_fids`, `ops.pantalla_fids` (ya existen, S1.3) y `ops.terminal` (ya existe en `db/ddl/monetdb/10_ops.sql`, redeclarada de solo lectura en `aerohub_fids/infrastructure/`, mismo patrón que `catalogo.aeropuerto` en S1.15).

**Testing**: `pytest` de integración contra MonetDB real en Docker; verificación en navegador real contra el gateway en Docker (Principio III).

**Target Platform**: contenedores Docker (`gateway`, `web`).

**Performance Goals**: sin objetivo nuevo — la reasignación de plantilla ya cumple RNF-P02 (<1s) desde S1.3 vía WebSocket; este sprint solo agrega quién puede invocarla.

**Constraints**: cero cambios al contrato de los 3 endpoints de escritura existentes ni al WebSocket de `apps/fids-player` (cerrado en S1.14); `aerohub_fids` no importa `aerohub_aodb` para leer `ops.terminal` — se redeclara localmente (Principio II, ADR-017 §5.4).

**Scale/Scope**: 1 módulo de backend con 3 endpoints GET nuevos (listado de plantillas, listado de pantallas, catálogo de terminales), 1 vista nueva de frontend con 2 tablas y 3 modales, 1 entrada de menú nueva (M2 nunca tuvo una).

## Constitution Check

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE — los 2 listados nuevos filtran por `contexto_tenant_id()` como toda consulta de `aerohub_fids` desde S1.3; el catálogo de terminales es de solo lectura global, mismo criterio que `catalogo.aeropuerto`/`catalogo.aerolinea` de S1.15 (no requiere `alcance_global()`, `ops.terminal` sí tiene `tenant_id` a diferencia de `catalogo.*` — la consulta de terminales SÍ filtra por tenant).
- **Principio II (Arquitectura Modular por Capas e Independencia de Módulos)**: CUMPLE — `ops.terminal` se redeclara en `aerohub_fids/infrastructure/`, no se importa de `aerohub_aodb`; verificado por `import-linter`.
- **Principio III (Verificación Empírica Obligatoria)**: se aplica — publicar plantilla, registrar pantalla, reasignar plantilla y confirmar el efecto en `apps/fids-player` real, todo contra MonetDB real en Docker antes de reportar el sprint como cerrado.
- **Principio IV (Calidad Continua en Verde)**: ruff/mypy/bandit/import-linter/pytest en verde sobre `aerohub_fids`.
- **Principio V (Aprobación Explícita)**: diff presentado antes de cualquier commit; commit solo si se pide.
- **Infraestructura**: verificación en `gateway`/`web` en Docker.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/018-administracion-fids/
├── plan.md
├── research.md
└── quickstart.md
```

Sin `data-model.md` ni `contracts/` — mismo criterio que S1.15: las entidades ya existen en el esquema (`ops.plantilla_fids`, `ops.pantalla_fids`, `ops.terminal`, sin cambios de DDL), y el contrato HTTP se documenta directamente en el router.

### Source Code (repository root)

```text
services/fids/aerohub_fids/
├── infrastructure/
│   ├── consultas.py                  # + listar_plantillas, listar_pantallas
│   ├── consultas_catalogo.py         # NUEVO — redeclara ops.terminal (solo lectura)
│   └── __init__.py                   # + exporta lo nuevo
├── application/
│   ├── consultar_plantillas.py       # NUEVO — listado, ultima version por nombre
│   ├── consultar_pantallas.py        # NUEVO — listado con telemetria
│   └── consultar_catalogos.py        # NUEVO — consultar_terminales
└── api/
    └── router.py                     # + GET /fids/plantillas, /fids/pantallas, /fids/catalogo/terminales

packages/contracts/aerohub_contracts/
└── roles_modulos.py                  # MODULOS["M2"].ruta = "/fids/pantallas" (hoy None)

apps/web/src/app/fids/
├── fids.service.ts                   # NUEVO
└── pantalla-list/
    ├── pantalla-list.html            # NUEVO — tabla plantillas + tabla pantallas + 3 modales
    ├── pantalla-list.ts              # NUEVO
    └── pantalla-list.scss            # NUEVO

apps/web/src/app/app.routes.ts        # + ruta /fids/pantallas
```

**Structure Decision**: mismo patrón por componente que el resto de `apps/web` (workpanel: `.ah-panel` + `.ah-tabla` + `.ah-modal`). Se usa una sola vista con dos secciones (plantillas arriba, pantallas abajo) en vez de dos rutas separadas — M2 solo tiene una entrada de menú posible (`modulosConVista` mapea un `modulo.ruta` por módulo), y las dos entidades están fuertemente acopladas (no se puede registrar una pantalla sin ver qué plantillas existen).

## Complexity Tracking

Sin violaciones que justificar.
