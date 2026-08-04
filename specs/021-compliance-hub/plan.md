# Implementation Plan: Compliance Hub (M9)

**Branch**: `021-compliance-hub` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-compliance-hub/spec.md`

## Summary

Dar superficie a los 11 endpoints de M9 (S1.7): incidentes, post-mortems
(único caso con UPDATE controlado), reportes DGAC, accesos de auditor,
evidencia SOC2. Corrige el hallazgo crítico de que `role_sre` -- el
único rol que el dominio permite para post-mortems -- no tiene ningún
scope `compliance:*`. Agrega 4 endpoints GET de listado que faltan
(post-mortems, reportes DGAC, accesos de auditor, evidencia SOC2) más 3
catálogos de solo lectura (tipo de incidente, tipo de reporte, control
SOC2). Frontend: una vista nueva `compliance/panel-compliance` con 5
secciones, mismo patrón que S1.16 (una ruta, varias tablas).

## Technical Context

**Language/Version**: Python 3.12 (`services/compliance`), TypeScript / Angular 19 (`apps/web`)

**Primary Dependencies**: FastAPI, SQLAlchemy Core, `aerohub_repository`, Angular standalone components + signals

**Storage**: MonetDB -- sin DDL nuevo, tablas `compliance.*` ya existentes desde S1.7

**Testing**: pytest de integración vía `TestClient` (mismo patrón que sprints previos de Fase 1.5)

**Target Platform**: Docker

**Project Type**: Web (1 backend + 1 frontend)

**Constraints**: PN-04 reforzada -- ninguna pantalla nueva ofrece mutación sobre las 5 tablas append-only; `post_mortem`/`post_mortem_accion` son la única excepción con UPDATE, ya controlada por el dominio (S1.7).

**Scale/Scope**: 7 endpoints GET nuevos (4 listados + 3 catálogos), 1 vista nueva de 5 secciones, 1 corrección de scopes.

## Constitution Check

- **Aislamiento fail-closed**: los 4 listados nuevos filtran por
  `contexto_tenant_id()` igual que el resto del módulo. PASA.
- **Arquitectura modular por capas**: extensión de
  `infrastructure/consultas.py` → `application/consultar.py` →
  `api/router.py`, sin paquete nuevo. PASA.
- **Verificación empírica**: el hallazgo de scopes de `role_sre` se
  verifica leyendo `roles_modulos.py` y `gestionar_post_mortem.py`
  directamente (ya hecho en research.md), y se re-verifica end-to-end
  con pytest tras el fix.
- **Calidad en verde**: ruff/mypy/bandit/import-linter sobre
  `services/compliance` antes de cerrar.
- **Aprobación explícita**: no se commitea sin pedido explícito.

Sin violaciones -- no aplica Complexity Tracking.

## Project Structure

```text
services/compliance/aerohub_compliance/
├── infrastructure/consultas.py        # + listar_post_mortems, listar_reportes_dgac,
│                                         listar_accesos_auditor, listar_evidencia_soc2
├── infrastructure/consultas_catalogo.py  # NUEVO: catalogos de solo lectura
├── application/consultar.py           # + 4 casos de uso de listado
├── application/consultar_catalogos.py # NUEVO
└── api/router.py                      # + 7 rutas GET

apps/web/src/app/compliance/
├── compliance.service.ts              # NUEVO
└── panel-compliance/                  # NUEVO -- 5 secciones

packages/contracts/aerohub_contracts/roles_modulos.py  # fix: role_sre + M9/compliance:*

tests/integration/test_compliance_hub.py  # NUEVO
```

**Structure Decision**: Mismo patrón de capas que S1.15-S1.18. Frontend:
una vista con 5 secciones (incidentes, post-mortems, reportes DGAC,
accesos de auditor, evidencia SOC2), expuesta ya sea vía `modulosConVista`
(M9 no tenía ruta -- se le asigna una, igual que M2 en S1.16) o como
enlace auxiliar si el rol no cae dentro del menú dinámico de módulos.
