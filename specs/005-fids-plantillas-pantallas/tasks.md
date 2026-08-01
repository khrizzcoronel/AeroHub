# Tasks: M2 FIDS -- plantillas y pantallas en tiempo real, detección de sin-señal

**Input**: Design documents from `specs/005-fids-plantillas-pantallas/`

**Estado**: retroactivo -- todas las tareas completadas y commiteadas en `55a9e95`.

## Phase 1: DDL y dominio

- [X] T001 `db/ddl/monetdb/10_ops.sql`: `ops.plantilla_fids`, `ops.pantalla_fids` + grants
- [X] T002 [P] `services/fids/aerohub_fids/domain/plantilla.py`: PN-11
      (`CLAVES_PII_PROHIBIDAS`, `_ruta_pii()` recursivo)
- [X] T003 [P] `services/fids/aerohub_fids/domain/pantalla.py`:
      `esta_sin_senal(ahora, umbral_segundos)`
- [X] T004 17 tests unitarios de dominio, incluida detección de PII anidada

## Phase 2: Publicación de plantillas y pantallas (US1) 🎯

**Goal**: publicar una plantilla se refleja en las pantallas suscritas en < 1s.

- [X] T005 [US1] `services/fids/aerohub_fids/infrastructure/`: G1, tablas,
      comandos, consultas
- [X] T006 [US1] `services/fids/aerohub_fids/application/publicar_plantilla.py`
- [X] T007 [US1] `services/fids/aerohub_fids/application/registrar_pantalla.py`
- [X] T008 [US1] `services/fids/aerohub_fids/application/asignar_plantilla.py`
- [X] T009 [US1] `services/fids/aerohub_fids/infrastructure/eventos.py`:
      `BroadcasterFids`
- [X] T010 [US1] `POST /fids/plantillas`, `POST /fids/pantallas`,
      `PATCH /fids/pantallas/{id}/plantilla`
- [X] T011 [US1] `GET /fids/ws/pantalla/{codigo}`: WS de propagación
- [X] T012 [US1] Corregir hallazgo: `ContextoTenantAusente` en el WS --
      `aerohub_repository.contexto` nunca se puebla para el scope
      `"websocket"`; creado `infrastructure/contexto_ws.py` +
      `application/contexto_ws.py` para poblarlo a mano solo para la
      resolución código→id
- [X] T013 [US1] Medir RNF-P02: propagación de plantilla < 1s contra servidor real
- [X] T014 [US1] Verificar PN-11: publicar plantilla con campo de PII → 422

**Checkpoint**: publicación de plantilla propagada por WS en < 1s, PN-11 en verde.

## Phase 3: Detección de sin-señal (US2)

- [X] T015 [US2] `services/fids/aerohub_fids/application/registrar_heartbeat.py`
- [X] T016 [US2] `POST /fids/pantallas/{id}/heartbeat`
- [X] T017 [US2] `services/fids/aerohub_fids/application/monitorear_senal.py`:
      `ejecutar_ciclo_monitoreo` bajo `alcance_global()` (proceso de plataforma,
      como CU-O18)
- [X] T018 [US2] `services/gateway/main.py`: ciclo de fondo
      `_ciclo_monitor_senal_fids`, intervalo 10s (margen real bajo el umbral de 60s)
- [X] T019 [US2] Verificar RNF-R04 con umbral corto inyectado (no esperar 60s
      reales en el test): pantalla sin heartbeat → `sin_senal`
- [X] T020 [US2] Verificar que una pantalla en `mantenimiento` NO se
      transiciona a `sin_senal`

**Checkpoint**: RNF-R04 verificado con umbral inyectado, ciclo de fondo
corriendo en el Gateway.

## Phase 4: Reproductor Angular (US3)

- [X] T021 [US3] `apps/fids-player`: app Angular nueva (puerto 4300)
- [X] T022 [US3] Componente reproductor: carga plantilla vigente por HTTP,
      se suscribe al WS, renderiza `definicion_json`
- [X] T023 [US3] Heartbeat periódico desde el reproductor
- [X] T024 [US3] Verificación en navegador real contra el backend real

**Checkpoint**: reproductor Angular funcional de punta a punta.

## Phase N: Métricas y polish

- [X] T025 [P] `services/fids/aerohub_fids/metricas.py`: Histogram de latencia
      de propagación, Counters de heartbeat/sin-señal
- [X] T026 `/metrics` exento de autenticación en el middleware del Gateway
- [X] T027 Verificación final: 232/232 tests, ruff/mypy/bandit/import-linter
      en verde, build/lint/test de `apps/fids-player` en verde

## Notes

- Commit real: `55a9e95` -- "S1.3 -- M2 FIDS: plantillas y pantallas en tiempo real"
- El patrón `contexto_ws.py` (poblar contexto a mano para un WS que necesita
  tocar la base) se reutiliza tal cual en S1.5 si hiciera falta un WS
  similar para rampa (no hizo falta -- la detección de desviación resultó
  ser síncrona, no periódica).
