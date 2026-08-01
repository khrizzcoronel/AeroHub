# Tasks: M4 Ground Operations -- turnaround, y dockerización completa del stack

**Input**: Design documents from `specs/007-ground-operations-turnaround/`

**Estado**: retroactivo -- todas las tareas completadas y commiteadas en
`0d95b2e` (turnaround) y `36c2f45` (CLAUDE.md).

## Phase 1: DDL y catálogos

- [X] T001 `db/ddl/monetdb/11_rampa.sql`: `tipo_tarea`, `tipo_incidencia_rampa`,
      `turnaround`, `tarea_turnaround`, `incidencia_rampa`
- [X] T002 `db/ddl/monetdb/97_grants_rampa.sql`: grants por rol (solo
      `role_ramp_agent` con I/Up)
- [X] T003 `db/seeds/generate.py`: sembrar `TIPOS_TAREA` (combustible/catering/
      limpieza/equipaje) y `TIPOS_INCIDENCIA_RAMPA`

## Phase 2: Dominio

- [X] T004 [P] `services/ramp/aerohub_ramp/domain/turnaround.py`: invariantes
      (vuelos distintos, ventana, estado)
- [X] T005 [P] `services/ramp/aerohub_ramp/domain/tarea_turnaround.py`:
      `duracion_minutos()` (derivada), `excede_estandar()`
- [X] T006 [P] `services/ramp/aerohub_ramp/domain/incidencia_rampa.py`:
      `severidad_por_desviacion()`
- [X] T007 24 pruebas unitarias de dominio

## Phase 3: Crear turnaround (US1) 🎯

- [X] T008 [US1] `services/ramp/aerohub_ramp/application/crear_turnaround.py`:
      valida sentido L/S, misma aeronave, `UQ` de vuelo de llegada
- [X] T009 [US1] `POST /rampa/turnarounds`, `GET /rampa/turnarounds`
- [X] T010 [US1] Verificar: vuelos incompatibles → 422, turnaround duplicado
      de vuelo de llegada → 409

## Phase 4: Registrar tareas y detectar desviación (US2)

- [X] T011 [US2] `services/ramp/aerohub_ramp/application/iniciar_tarea.py`:
      crea la fila con agente + `inicio_real` en el mismo momento
- [X] T012 [US2] `services/ramp/aerohub_ramp/application/finalizar_tarea.py`:
      calcula duración, compara contra estándar, genera `incidencia_rampa`
      SINCRÓNICAMENTE si excede -- decisión explícita de NO usar un ciclo de
      fondo (a diferencia de FIDS S1.3): el evento "marca fin" ya conoce la
      duración real
- [X] T013 [US2] `POST /rampa/turnarounds/{id}/tareas`,
      `POST /rampa/tareas/{id}/finalizar`, `GET /rampa/incidencias`
- [X] T014 [US2] Medir en la prueba de integración: incidencia generada en
      ~0.9s desde la petición de fin (exigido < 60s)
- [X] T015 [US2] Corregir hallazgo de bandit: dos `assert` en
      `finalizar_tarea.py` (se eliminan bajo bytecode optimizado) --
      reemplazados por `RuntimeError` explícitos

**Checkpoint**: RF-O16 verificado con medición real, no solo asumido < 60s.

## Phase 5: Mínimo privilegio de role_ramp_agent (US3)

- [X] T016 [US3] `services/ramp/aerohub_ramp/infrastructure/consultas.py`:
      `listar_tareas_de_turnaround()` filtra por `agente_usuario_id` cuando
      `rol_actor == role_ramp_agent`
- [X] T017 [US3] `finalizar_tarea()`: 404 (no 403) si la tarea es de otro
      agente y el rol activo es `role_ramp_agent`
- [X] T018 [US3] Verificar: agente B no ve tarea de agente A, agente B no
      puede finalizarla (404), `role_operations_controller` SÍ la ve
      (control positivo)

**Checkpoint**: mínimo privilegio verificado en ambos sentidos + control positivo.

## Phase 6: Panel Angular (FR-008)

- [X] T019 `apps/web/src/app/rampa/panel-turnaround/`: crear turnaround,
      iniciar/finalizar tareas, ver incidencias
- [X] T020 Verificación en navegador real, incluido el caso de error 422
      (fin_real anterior a inicio_real)

## Phase 7: Dockerización completa del stack (US4)

- [X] T021 `services/gateway/Dockerfile`: workspace `uv` completo
- [X] T022 Corregir hallazgo: `uv sync` sin `--all-packages` solo instala el
      grupo `dev` -- primera imagen arrancó sin `uvicorn`
- [X] T023 `apps/web/Dockerfile`, `apps/fids-player/Dockerfile`: `npx nx
      serve --host 0.0.0.0`
- [X] T024 Corregir hallazgo: `tsconfig.base.json` no existe en la raíz (es
      `tsconfig.json`) -- Dockerfiles corregidos
- [X] T025 Corregir hallazgo: `npm ci` falla por discrepancia de versión de
      npm entre el lockfile del repo y la imagen base -- cambiado a `npm install`
- [X] T026 `infra/docker-compose.yml`: servicios `gateway`/`web`/`fids-player`
      nuevos, DSN interno `monetdb:50000`
- [X] T027 `infra/prometheus/prometheus.yml`: scrape target del gateway
- [X] T028 Regenerar `uv.lock` dentro del contenedor (donde `uv` sí está
      disponible) y copiarlo de vuelta al repo con `docker cp` -- corrige la
      desactualización arrastrada desde S1.3 (`prometheus-client`, `pulp`)
- [X] T029 Verificación en vivo: los 4 contenedores arrancan sanos,
      navegador contra `web`/`fids-player` dockerizados trae datos reales a
      través del `gateway` dockerizado
- [X] T030 `.claude/launch.json`: apuntar a los servicios dockerizados en
      vez de lanzar `nx serve` suelto

**Checkpoint**: stack completo (MonetDB + gateway + web + fids-player)
corriendo íntegramente en Docker, verificado en vivo.

## Phase 8: Contexto persistente y Spec Kit (fuera del alcance original del sprint, agregado a pedido del usuario)

- [X] T031 `CLAUDE.md`: estado del plan, reglas de trabajo, patrones
      arquitectónicos, hallazgos empíricos de MonetDB, entorno de desarrollo
- [X] T032 Instalar y configurar GitHub Spec Kit (`.specify/`,
      `.claude/skills/speckit-*`)
- [X] T033 `.specify/memory/constitution.md`: ratificar v1.0.0 a partir de
      los ADR y reglas ya vigentes
- [X] T034 `specs/001-*` .. `specs/007-*`: specs/plan/tasks retroactivos
      para S0.1-S1.5

## Notes

- Commits reales: `0d95b2e` ("S1.5 -- M4 Ground Operations (turnaround) y
  dockerizacion completa del stack de desarrollo"), `36c2f45` ("Agrega
  CLAUDE.md").
- Este es el primer sprint donde el propio proceso de desarrollo (Docker,
  contexto persistente, Spec Kit) se vuelve parte del entregable, no solo
  el código de negocio.
