# Implementation Plan: AODB backend + Angular mínimo -- aprovisionamiento de tenant y alta de vuelo

**Branch**: `main` | **Date**: 2026-07-31 (retroactivo) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-aodb-aprovisionamiento-tenant/spec.md`

## Summary

Primer backend HTTP real del proyecto: `services/gateway` (middleware JWT) +
`services/aodb` (dominio/aplicación/infraestructura/api de vuelo) +
`services/tenancy` (aprovisionamiento de tenant), con `apps/web` sirviendo un
formulario mínimo. Establece el patrón arquitectónico de capas que todos los
módulos de negocio siguientes van a replicar.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy Core, PyJWT

**Storage**: MonetDB -- `ops.terminal`, `ops.puerta`, `ops.vuelo`,
`ops.vuelo_estado` (`db/ddl/monetdb/10_ops.sql`)

**Testing**: `pytest` (unit/integration/negative/cross_tenant) contra
MonetDB real; Angular build/lint/test

**Target Platform**: backend suelto en el host (`uv run uvicorn`); Angular
dev-server suelto (`npx nx serve`) -- ambos dockerizados recién en S1.5

**Performance Goals**: sin objetivo explícito de este sprint (llega en S1.2,
RNF-P01)

**Constraints**: todo id Snowflake DEBE viajar como string en JSON; ningún
módulo de negocio importa `infrastructure/` de otro

**Scale/Scope**: 2 módulos de negocio con código real (`aodb`, `tenancy`),
1 formulario Angular

## Constitution Check

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE -- primera
  aplicación real del guardián G1/G2 de S0.2 contra HTTP real; PN-01/PN-02
  verificados con peticiones reales, no solo unit tests.
- **Principio II (Arquitectura Modular por Capas)**: CUMPLE -- establece el
  patrón `domain/application/infrastructure/api` que todo módulo posterior
  replica; corrige un falso-positivo real de `import-linter`
  (`allow_indirect_imports=True` para la cadena `application → infrastructure
  → aerohub_repository`).
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- 4 bugs
  reales encontrados y corregidos por verificación contra MonetDB y
  navegador real (columna calificada a 3 partes sobre vista, `contexto_rol_actor`
  vs `rol_activo_de_sesion`, corrupción de IDs en el navegador, falso-positivo
  de import-linter).

## Project Structure

### Documentation (this feature)

```text
specs/003-aodb-aprovisionamiento-tenant/
├── plan.md
└── spec.md
```

### Source Code (repository root)

```text
services/gateway/
├── aerohub_gateway/api/     # AutenticacionJWTMiddleware
└── main.py                   # composicion root, fuera del paquete aerohub_gateway

services/aodb/aerohub_aodb/
├── domain/vuelo.py            # invariantes puras (sentido, aeropuertos distintos, sta>std)
├── domain/estado.py           # validar_transicion (estado terminal no admite mas cambios)
├── application/alta_vuelo.py, consultar_vuelo.py, registrar_cambio_estado.py
├── infrastructure/            # G1 propio, tablas.py, comandos.py, consultas.py
└── api/router.py              # POST /vuelos, GET /vuelos/{id}, POST /vuelos/{id}/estados

services/tenancy/                # CU-O18 aprovisionar_tenant

apps/web/src/app/
├── tenants/tenant-creation/    # formulario Angular minimo
└── tenants/tenant.service.ts

db/ddl/monetdb/10_ops.sql        # ops.terminal, ops.puerta, ops.vuelo, ops.vuelo_estado
db/ddl/monetdb/96_grants_ops.sql
```

**Structure Decision**: cada módulo de negocio posee su propio
`infrastructure/` (registro G1 + tablas + consultas), NO centralizado en
`packages/repository` -- corrige el diseño de S0.1, que dejó subpaquetes
vacíos (`aerohub_repository/ops/`, `aerohub_repository/tenants/`, etc.) hoy
eliminados.

## Complexity Tracking

Sin violaciones que justificar.
