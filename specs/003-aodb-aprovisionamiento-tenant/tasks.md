# Tasks: AODB backend + Angular mínimo -- aprovisionamiento de tenant y alta de vuelo

**Input**: Design documents from `specs/003-aodb-aprovisionamiento-tenant/`

**Estado**: retroactivo -- todas las tareas completadas y commiteadas en `72488fe`.

## Phase 1: Setup

- [X] T001 `db/ddl/monetdb/10_ops.sql`: `ops.terminal`, `ops.puerta`,
      `ops.vuelo`, `ops.vuelo_estado`
- [X] T002 `db/ddl/monetdb/96_grants_ops.sql`: grants por rol sobre `ops.*`
- [X] T003 Corregir falso-positivo de `import-linter`: contrato
      "solo-infrastructure-toca-repository" marcaba como violación la
      dependencia legítima `application → infrastructure → aerohub_repository`
      -- corregido con `allow_indirect_imports=True`
- [X] T004 Eliminar subpaquetes vacíos obsoletos de
      `packages/repository/aerohub_repository/{ops,tenants,billing,...}/`

## Phase 2: Foundational

- [X] T005 `services/gateway/aerohub_gateway/api/`: `AutenticacionJWTMiddleware`
- [X] T006 `services/gateway/main.py`: composición root fuera del paquete
      `aerohub_gateway` (permite importar módulos de negocio hermanos)
- [X] T007 Corregir hallazgo: `registrar_auditoria()` llamaba a
      `contexto_rol_actor()` en vez de `rol_activo_de_sesion()`, rompía bajo
      `alcance_global()` (caso exacto de CU-O18)

## Phase 3: Aprovisionar tenant (US1) 🎯 MVP

**Goal**: `role_platform_admin` puede dar de alta un tenant con su usuario admin.

- [X] T008 [US1] `services/tenancy/`: dominio + aplicación + infraestructura
      de `aprovisionar_tenant` (CU-O18)
- [X] T009 [US1] `POST /tenants` -- crea tenant + usuario admin en una transacción
- [X] T010 [US1] `apps/web/src/app/tenants/tenant-creation/`: formulario Angular
- [X] T011 [US1] `apps/web/src/app/tenants/tenant.service.ts`
- [X] T012 [US1] Verificación en navegador real: formulario → backend real →
      datos exactos en MonetDB

**Checkpoint**: aprovisionamiento de tenant funcional de punta a punta.

## Phase 4: Alta, consulta y cambio de estado de vuelo (US2)

- [X] T013 [P] [US2] `services/aodb/aerohub_aodb/domain/vuelo.py`:
      invariantes puras
- [X] T014 [P] [US2] `services/aodb/aerohub_aodb/domain/estado.py`:
      `validar_transicion`
- [X] T015 [US2] `services/aodb/aerohub_aodb/infrastructure/`: G1 propio,
      `tablas.py`, `comandos.py`, `consultas.py`
- [X] T016 [US2] `services/aodb/aerohub_aodb/application/alta_vuelo.py`
- [X] T017 [US2] `services/aodb/aerohub_aodb/application/consultar_vuelo.py`
- [X] T018 [US2] `services/aodb/aerohub_aodb/application/registrar_cambio_estado.py`
- [X] T019 [US2] `services/aodb/aerohub_aodb/api/router.py`: `POST /vuelos`,
      `GET /vuelos/{id}`, `POST /vuelos/{id}/estados`
- [X] T020 [US2] Corregir hallazgo: MonetDB rechaza columna calificada a 3
      partes en `WHERE` sobre una VISTA -- reimplementada la consulta de
      estado vigente directo sobre `ops.vuelo_estado`

**Checkpoint**: ciclo de vida de vuelo (alta/consulta/cambio de estado)
funcional contra MonetDB real.

## Phase 5: PN-01 / PN-02 (US3)

- [X] T021 [US3] Corregir hallazgo: IDs Snowflake como número JSON se
      corrompen en el navegador por encima de `Number.MAX_SAFE_INTEGER` --
      transmitidos como string en ambos sentidos
- [X] T022 [US3] Verificar PN-01 con HTTP real: vuelo de otro tenant → 404
- [X] T023 [US3] Verificar PN-02 con HTTP real: `tenant_id` del cuerpo se ignora

**Checkpoint**: PN-01/PN-02 verificados con peticiones HTTP reales.

## Phase N: Polish

- [X] T024 `.claude/launch.json`: configuración de preview de `web`
- [X] T025 Verificación final: 186/186 tests, ruff/mypy/bandit/import-linter
      en verde, build/lint/test de Angular en verde

## Notes

- Commit real: `72488fe` -- "S1.1 -- backend completo y Angular minimo funcional"
- Este sprint establece el PATRÓN arquitectónico (capas + G1 por módulo +
  IDs como string) que S1.2-S1.5 replican sin volver a discutirlo.
