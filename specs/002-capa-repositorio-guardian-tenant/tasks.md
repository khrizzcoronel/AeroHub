# Tasks: Capa de repositorio -- guardián de tenant, roles y DDL fundacional

**Input**: Design documents from `specs/002-capa-repositorio-guardian-tenant/`

**Estado**: retroactivo -- todas las tareas completadas y commiteadas en `0cdc813`.

## Phase 1: DDL fundacional

- [X] T001 [P] `db/ddl/monetdb/00_schemas.sql` .. `01_catalogo.sql` (10 catálogos globales)
- [X] T002 [P] `db/ddl/monetdb/02_tenants.sql` (esquema `tenants`, 10 tablas)
- [X] T003 [P] `db/ddl/monetdb/03_compliance_auditoria.sql` (`compliance.log_auditoria`,
      adelantada desde S1.7 por exigencia de P8)
- [X] T004 [P] `db/ddl/monetdb/04_continuidad.sql` (`continuidad.journal_mutacion`, ADR-018 C1)
- [X] T005 `db/ddl/monetdb/90_roles.sql` (16 roles de la matriz 4.3.1)
- [X] T006 `db/ddl/monetdb/91_grants_catalogo.sql` .. `94_grants_continuidad.sql`
      (GRANT reales por rol)
- [X] T007 `db/ddl/monetdb/95_usuario_aplicacion.sql` (usuario técnico `aerohub_app`)
- [X] T008 `db/migrations/apply.py` -- aplicador de DDL vía `pymonetdb`, orden lexicográfico
- [X] T009 `db/seeds/generate.py` -- datos sintéticos + filas canario fijas (MEC/UIO)

## Phase 2: Guardián de tenant (US1) 🎯

**Goal**: ninguna consulta sin filtro de tenant llega al motor.

- [X] T010 `packages/repository/aerohub_repository/guard.py`: G1
      (`registrar_alcance`, `alcance_de`)
- [X] T011 `packages/repository/aerohub_repository/guard.py`: G2
      (`verificar_sentencia`, recorrido de árbol SQLAlchemy Core)
- [X] T012 `packages/repository/aerohub_repository/base.py`: `sesion()` con
      `SET ROLE` real, registro de `verificar_sentencia` en `before_execute`
- [X] T013 `packages/repository/aerohub_repository/contexto.py`: `ContextVar`
      de tenant/rol/usuario + `alcance_global()`
- [X] T014 21 casos de prueba del guardián, incluido JOIN adversarial de dos
      tablas tenant
- [X] T015 Corregir hallazgo: `GENERATED ALWAYS AS IDENTITY` no funciona bajo
      `SET ROLE` -- mover generación de id a `packages/kernel/identificador.py`
- [X] T016 Corregir hallazgo: FK de `log_auditoria.usuario_id` hacia
      `tenants.usuario` rompía el INSERT para todo rol -- retirada

**Checkpoint**: guardián G1/G2 verificado con 21/21 casos contra MonetDB real.

## Phase 3: Journal y auditoría transaccional (US3)

- [X] T017 `packages/repository/aerohub_repository/journal.py`:
      `escribir_journal` (ADR-018 C1)
- [X] T018 `packages/repository/aerohub_repository/audit.py`:
      `registrar_auditoria` (P8)
- [X] T019 Prueba de rollback real: journal + auditoría + tabla de negocio en
      la misma transacción, ninguno persiste si la transacción revierte

**Checkpoint**: mutación + journal + auditoría son atómicos, probado con
rollback real.

## Phase 4: Suite cruzada G4 (US2)

- [X] T020 `tests/cross_tenant/`: suite por introspección
- [X] T021 Inyectar una fuga real deliberada (`OR` en vez de `AND` en el
      filtro de tenant) y confirmar que G4 la detecta donde G2 no puede
- [X] T022 Corregir bug de aislamiento de pruebas: `pytestmark` a nivel de
      `conftest.py` no se propaga a módulos hermanos -- reemplazado por
      fixture `autouse`
- [X] T023 Corregir fuga de estado global entre `test_guard.py` y
      `test_g1_conformidad.py`

**Checkpoint**: 58/58 casos de PN-03/04/08/15 + suite cruzada en verde.

## Phase N: Polish

- [X] T024 Corregir hallazgo: `MDB_CREATE_DBS` mal configurado en S0.1 (el
      `monetdb create` manual usaba el password por defecto del motor)
- [X] T025 Verificación final: ruff, mypy, bandit, import-linter,
      nomenclatura DDL, `docker-compose config` limpios
- [X] T026 134/134 tests totales en verde contra MonetDB real

## Notes

- Commit real: `0cdc813` -- "S0.2 -- capa de repositorio: guardian de tenant, roles y DDL fundacional"
- Los 3 hallazgos empíricos de este sprint están documentados también en
  `docs/runbooks/monetdb.md` para no tener que redescubrirlos.
