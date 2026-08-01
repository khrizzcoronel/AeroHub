# Tasks: Fundación del monorepo

**Input**: Design documents from `specs/001-fundacion-monorepo/`

**Estado**: retroactivo -- todas las tareas ya completadas y commiteadas en `181b610`.

## Phase 1: Setup

- [X] T001 Reconstruir el workspace `uv` con 17 miembros (`packages/kernel`,
      `packages/contracts`, `packages/repository`, 12 `services/*`,
      `pipelines`, `ml`)
- [X] T002 Configurar `.importlinter` con contratos de capas por módulo +
      independencia cruzada
- [X] T003 [P] Configurar `ruff`, `mypy`, `bandit` a nivel de workspace
- [X] T004 [P] Scaffoldear `apps/web` y `apps/fids-player` sobre Angular 22 vía Nx
- [X] T005 Configurar `.github/workflows/ci.yml` (ruff, mypy, import-linter, pytest)
- [X] T006 Eliminar todo artefacto de la arquitectura PostgreSQL/RLS anterior
      (plan v1.0, ADR locales obsoletos, migraciones, tests negativos previos)

## Phase 2: Foundational

- [X] T007 [P] `aerohub_kernel`: generación de IDs (Snowflake-like), tipo
      `Dinero`, `CodigoIATA`/`CodigoICAO`, utilidades de tiempo UTC-aware
- [X] T008 [P] `aerohub_repository`: contexto de tenant vía `ContextVar`
      (`tenant_id`, `rol_actor`, `usuario_id`) + `alcance_global()`
- [X] T009 27 tests unitarios sobre `aerohub_kernel` y el contexto de
      `aerohub_repository`, 97% cobertura

## Phase 3: Infraestructura Docker (US1) 🎯

**Goal**: los 8 servicios de infraestructura arrancan sanos con un comando.

- [X] T010 `infra/docker-compose.yml`: MonetDB primario (ADR-013)
- [X] T011 `infra/docker-compose.yml`: MonetDB standby (ADR-018, componente C3)
- [X] T012 `infra/docker-compose.yml`: ClickHouse (ADR-012, capa dual)
- [X] T013 `infra/docker-compose.yml`: MinIO (capas medallion Parquet)
- [X] T014 `infra/docker-compose.yml`: Airflow -- corregido hallazgo real:
      fallo de LocalExecutor+SQLite (documentado en `docs/runbooks/airflow.md`)
- [X] T015 `infra/docker-compose.yml`: Prometheus, Loki, Grafana
- [X] T016 Verificación en vivo: los 8 servicios responden sanos por healthcheck
- [X] T017 Documentar en `docs/runbooks/airflow.md` el hallazgo del cuelgue
      reproducible al recrear el contenedor sobre un volumen ya inicializado

**Checkpoint**: entorno de desarrollo completo, reproducible con un comando.

## Phase 4: Verificación de independencia de módulos (US2)

- [X] T018 Probar `lint-imports` contra una importación cruzada deliberada
      entre dos módulos de negocio (introducida y revertida, no solo
      configurada en teoría)
- [X] T019 Confirmar que los 15+ contratos de `.importlinter` pasan sobre el
      workspace completo

**Checkpoint**: la independencia de módulos es un contrato verificado
automáticamente en CI, no solo documentado.

## Phase N: Documentación de arquitectura

- [X] T020 [P] ADR-017: arquitectura de módulos de dominio con capas internas
- [X] T021 [P] ADR-018: mecanismo de continuidad de MonetDB
- [X] T022 [P] ADR-019: guardián de tenant fail-closed en ejecución
- [X] T023 `docs/PLAN_IMPLEMENTACION_v2.0.md`: 5 fases, 24 sprints, compuerta
      de pruebas obligatoria por sprint

## Notes

- Commit real: `181b610` -- "S0.1 — fundacion del monorepo: arquitectura, workspace y CI"
- El guardián de tenant COMPLETO (G1+G2 en ejecución) y el journal de
  continuidad quedan fuera de alcance de este sprint por diseño -- son el
  contenido de S0.2 (`specs/002-capa-repositorio-guardian-tenant/`).
