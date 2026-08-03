# Tasks: Tableros operativos densos (puertas + rampa)

**Input**: Design documents from `specs/014-tableros-operativos-densos/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [quickstart.md](./quickstart.md)

**Tests**: sin automatizados (mismo criterio que S1.11) — verificación
manual guiada por [quickstart.md](./quickstart.md).

**Organización**: por historia de usuario (US1 = puertas, US2 = rampa,
ambas P1, independientes entre sí — comparten primitivos pero no
archivos).

## Phase 1: User Story 1 - Ver la ocupación de las puertas de un vistazo (Priority: P1)

**Goal**: `puertas/tablero-puertas` rediseñada con `.ah-tira` (semáforo de
ocupación/conflicto) y `.ah-tabla` para las asignaciones anidadas.

**Independent Test**: Escenario 1 de `quickstart.md`.

- [X] T001 [US1] `apps/web/src/app/puertas/tablero-puertas/tablero-puertas.ts`:
      función pura `claseOcupacionPuerta(asignaciones: AsignacionTablero[]): string`
      -- `''` (neutro) si vacío, `'ah-tira--ok'` si una sola vigente sin
      solapar, `'ah-tira--critico'` si hay solapamiento de intervalos
      (research.md Decisión 1); ordenar por `inicio_previsto` y comparar
      pares consecutivos
- [X] T002 [US1] `apps/web/src/app/puertas/tablero-puertas/tablero-puertas.html`:
      cada puerta como `.ah-tira` (código/tipo/envergadura en mono,
      barra con la clase de T001); la tabla de asignaciones anidada usa
      `.ah-tabla`; formulario de asignación manual con `.ah-campo`/
      `.ah-btn`; botones de carga con `.ah-btn`/`.ah-btn--secundario`;
      resultado de automática y errores con `.ah-alerta`; estado vacío
      (sin puertas) con `.ah-vacio`
- [X] T003 [US1] `apps/web/src/app/puertas/tablero-puertas/tablero-puertas.scss`
      NUEVO: layout responsivo, consistente con
      `estado-tiempo-real.scss` (S1.11)

**Checkpoint**: US1 verificable — SC-001, SC-003, SC-004.

---

## Phase 2: User Story 2 - Seguir un turnaround y sus tareas sin perderse (Priority: P1)

**Goal**: `rampa/panel-turnaround` rediseñada con `.ah-tira` para
turnarounds y `.ah-tabla` para tareas e incidencias, ambas con semáforo.

**Independent Test**: Escenario 2 de `quickstart.md`.

- [X] T004 [P] [US2] `apps/web/src/app/rampa/panel-turnaround/panel-turnaround.ts`:
      función pura `claseEstadoTurnaround(t: Turnaround, ahora: Date): string`
      -- mapeo `estado` → semáforo + refinamiento de vencido
      (research.md Decisión 2)
- [X] T005 [P] [US2] `apps/web/src/app/rampa/panel-turnaround/panel-turnaround.ts`:
      función pura `claseSeveridadIncidencia(severidad: string): string`
      -- `baja`→neutro, `media`→atención, `alta`/`critica`→crítico
      (research.md Decisión 3)
- [X] T006 [US2] `apps/web/src/app/rampa/panel-turnaround/panel-turnaround.html`:
      lista de turnarounds como `.ah-tira` (barra con T004); tabla de
      tareas del turnaround seleccionado en `.ah-tabla` (research.md
      Decisión 4, NO como tiras) con columna estado resaltada;
      formularios (turnaround, tarea) con `.ah-campo`/`.ah-btn`; tabla de
      incidencias en `.ah-tabla` con columna severidad usando T005;
      mensaje de mínimo privilegio de `role_ramp_agent` preservado tal
      cual dentro del tratamiento de estado vacío (`.ah-vacio`)
- [X] T007 [US2] `apps/web/src/app/rampa/panel-turnaround/panel-turnaround.scss`
      NUEVO: layout responsivo, misma densidad que las otras 2 vistas

**Checkpoint**: US2 verificable — SC-002, SC-003, SC-004.

---

## Phase 3: Documentación

- [X] T008 [P] `docs/PLAN_IMPLEMENTACION_v2.0.md`: sección §8.12 nueva
      (Sprint S1.12), formato de §8.1-§8.11
- [X] T009 [P] `CLAUDE.md`: fila S1.12 en la tabla de estado, y
      actualizar la sección de rediseño con lo implementado

---

## Phase 4: Polish

- [X] T010 Ejecutar los 3 escenarios de [quickstart.md](./quickstart.md)
      completos contra Docker real (`monetdb`, `gateway`, `web`,
      `docker compose up -d --build web`)
- [X] T011 Build de producción de `apps/web` en verde (`nx build web`)
- [X] T012 Confirmar coherencia visual con `vuelos/estado-tiempo-real`
      (Escenario 3 de quickstart.md, SC-005) — mismo componente tira,
      misma tipografía mono, misma paleta de semáforo en las 3 vistas

---

## Dependencies & Execution Order

- **US1 (puertas)** y **US2 (rampa)** son completamente independientes
  entre sí (archivos distintos, sin dependencia de datos compartidos) —
  pueden hacerse en cualquier orden o en paralelo
- **T004/T005** (dos funciones puras en el mismo archivo `panel-
  turnaround.ts`) son independientes entre sí pero preceden a T006
- **Documentación (Fase 3)**: en paralelo a todo, se cierra al final
- **Polish (Fase 4)**: depende de US1 y US2 completas

## Implementation Strategy

1. US1 (puertas) completa primero — más simple, valida el patrón de
   "tira = recurso" con datos ya cargados
2. US2 (rampa) — reutiliza el mismo patrón, agrega dos funciones de
   mapeo en vez de una
3. Documentación
4. Polish: verificación de los 3 escenarios + build + coherencia visual

## Notes

- Cero cambios en `puertas.service.ts`/`rampa.service.ts` — el rediseño
  es 100% de presentación sobre datos que el frontend ya recibe.
- El mensaje de mínimo privilegio de `role_ramp_agent` es contenido de
  negocio real (spec.md) — no se reescribe, solo se envuelve en el
  tratamiento visual de estado vacío.
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes (Principio V).
