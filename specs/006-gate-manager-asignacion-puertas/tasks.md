# Tasks: M3 Terminal & Gate Manager -- asignación de puertas sin solapamiento

**Input**: Design documents from `specs/006-gate-manager-asignacion-puertas/`

**Estado**: retroactivo -- todas las tareas completadas y commiteadas en `dbe3b23`.

## Phase 1: DDL y dominio

- [X] T001 `db/ddl/monetdb/10_ops.sql`: `ops.asignacion_puerta` + `96_grants_ops.sql`
- [X] T002 `services/gates/aerohub_gates/domain/asignacion_puerta.py`:
      `intervalos_se_solapan()`, `verificar_no_solapamiento()`,
      `verificar_compatibilidad_envergadura()`
- [X] T003 27 pruebas unitarias exhaustivas del algoritmo de intervalos
      (bordes `fin==inicio`, contención, solape parcial)

## Phase 2: Asignación manual secuencial (US1) 🎯

**Goal**: rechazar solapamientos y envergadura incompatible en el caso secuencial.

- [X] T004 [US1] `services/gates/aerohub_gates/infrastructure/`: G1, tablas,
      comandos, consultas
- [X] T005 [US1] `services/gates/aerohub_gates/application/asignar_puerta.py`
- [X] T006 [US1] `services/gates/aerohub_gates/application/cancelar_asignacion.py`
- [X] T007 [US1] `POST /puertas/asignaciones`, `POST .../cancelar`,
      `GET /puertas/tablero`
- [X] T008 [US1] Verificar PN-05 secuencial: solape parcial → 409, intervalo
      adyacente → 201, envergadura incompatible → 422

**Checkpoint**: PN-05 secuencial en verde.

## Phase 3: Concurrencia real (US2)

- [X] T009 [US2] `services/gates/aerohub_gates/infrastructure/comandos.py`:
      `bloquear_puerta_para_asignacion()` -- UPDATE sin efecto sobre la
      propia fila de la puerta, antes de leer asignaciones existentes
- [X] T010 [US2] Primera prueba de concurrencia real (2 peticiones
      simultáneas): FALLA con 500 en vez de 409 limpio
- [X] T011 [US2] Diagnosticar: SQLSTATE 42000 ("Update failed due to
      conflict with another transaction"), distinto del 40001 ya conocido
- [X] T012 [US2] Ampliar `aerohub_repository.reintentar_en_conflicto` para
      reconocer también SQLSTATE 42000
- [X] T013 [US2] Re-verificar concurrencia real: exactamente 201+409, nunca
      ambos 201 ni ningún 500, confirmado en 3 corridas consecutivas

**Checkpoint**: PN-05 concurrente en verde, con el mecanismo de reintento
compartido corregido para todo el proyecto, no solo para `gates`.

## Phase 4: Asignación automática por PuLP (US3)

- [X] T014 [US3] Agregar dependencia `pulp` a `services/gates/pyproject.toml`
- [X] T015 [US3] `services/gates/aerohub_gates/application/asignacion_automatica.py`:
      modelo `LpProblem` (maximizar vuelos asignados, restricciones de
      envergadura y no-solapamiento por pares, preferencia por `contacto`)
- [X] T016 [US3] `POST /puertas/asignaciones/automatica`
- [X] T017 [US3] Verificar sobre dataset sintético: plan sin conflictos de
      solapamiento ni de envergadura

**Checkpoint**: asignación automática produce un plan sin conflictos.

## Phase 5: Tablero Angular (FR-007)

- [X] T018 `apps/web/src/app/puertas/tablero-puertas/`: vista con formulario
      de asignación manual y notificación de conflicto (409 mostrado inline)
- [X] T019 Verificación en navegador real: conflicto 409 visible al usuario

## Phase N: Polish

- [X] T020 Verificación final: 264/264 tests, ruff/mypy/bandit/import-linter
      en verde

## Notes

- Commit real: `dbe3b23` -- "S1.4 -- M3 Terminal & Gate Manager"
- El hallazgo del SQLSTATE 42000 (Fase 3) es el ejemplo más claro del
  Principio III de la constitución: el diseño "correcto en el papel" falló
  la primera vez que se probó bajo concurrencia real.
