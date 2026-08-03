# Tasks: Sistema de diseño + deuda de JWT + vista canónica

**Input**: Design documents from `specs/013-diseno-sistema-jwt/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [quickstart.md](./quickstart.md)

**Tests**: sin automatizados (frontend sin suite de tests hoy, no se
introduce una para un sprint de estilo) — verificación manual guiada por
[quickstart.md](./quickstart.md), Principio III de la constitución.

**Organización**: por historia de usuario (US1/US2 de `spec.md`, ambas P1).

## Phase 1: Setup

- [X] T001 Verificar en `apps/web/src/index.html` (o mecanismo de carga de
      fuentes) si IBM Plex Mono ya está enlazada; agregar el peso que
      falte (research.md Decisión 5)

---

## Phase 2: Foundational (bloqueante para US1/US2)

**Propósito**: el sistema de tokens y primitivos que ambas historias
consumen.

- [X] T002 `apps/web/src/styles.scss`: agregar los 4 tokens de semáforo
      (`--ah-estado-ok/atencion/critico/neutro`) y confirmar la regla de
      `--ah-font-mono` para dato operacional
- [X] T003 `apps/web/src/app/_primitivos.scss` NUEVO: `.ah-tira` (barra de
      estado 4px + datos en columnas mono, ver diagrama de
      DIRECCION_VISUAL.md §2.4), `.ah-tabla` (fila 40px, numerales
      tabulares), `.ah-campo`, `.ah-btn`, `.ah-alerta`, `.ah-vacio` —
      transición de la barra de `.ah-tira` en 150ms (research.md
      Decisión 4), respetando `prefers-reduced-motion` ya global
- [X] T004 Importar `_primitivos.scss` desde `styles.scss` (research.md
      Decisión 1)
- [X] T005 `apps/web/src/app/auth/_auth-form.scss`: reescribir
      `.card`/`.field`/`.btn`/`.alert`/`.notice` para apoyarse en los
      primitivos nuevos (research.md Decisión 2) — sin cambiar nombres de
      clase en las 6 plantillas HTML de auth, cero riesgo de romper S1.10

**Checkpoint**: sistema de diseño listo para consumirse.

---

## Phase 3: User Story 1 - Ver el estado de los vuelos en una consola legible (Priority: P1)

**Goal**: `vuelos/estado-tiempo-real` rediseñada por completo con `.ah-tira`.

**Independent Test**: Escenario 1 de `quickstart.md`.

- [X] T006 [US1] `apps/web/src/app/vuelos/estado-tiempo-real/estado-tiempo-real.html`:
      reemplazar la tabla HTML cruda por una lista de `.ah-tira` (una por
      evento, más reciente arriba), con el semáforo de color según
      `codigo_estado`; usar `.ah-vacio` cuando no hay eventos; usar
      `.ah-alerta` para el error de conexión
- [X] T007 [US1] `apps/web/src/app/vuelos/estado-tiempo-real/estado-tiempo-real.scss`
      NUEVO: layout de consola densa (sin tarjetas con aire, decisión
      central de DIRECCION_VISUAL.md §2.2), responsivo
- [X] T008 [US1] `apps/web/src/app/vuelos/estado-tiempo-real/estado-tiempo-real.ts`:
      mapear `codigo_estado` a uno de los 4 tokens de semáforo (función
      pura, sin lógica de negocio nueva); mantener el comportamiento de
      RF-O04 ya existente (más reciente primero, historial acotado)

**Checkpoint**: US1 verificable — SC-001/SC-002/SC-004/SC-005.

---

## Phase 4: User Story 2 - No tener que pegar un token para usar la aplicación (Priority: P1)

**Goal**: las 4 vistas dejan de pedir/aceptar un JWT manual.

**Independent Test**: Escenario 2 de `quickstart.md`.

- [X] T009 [P] [US2] `apps/web/src/app/vuelos/estado-tiempo-real/estado-tiempo-real.ts`:
      quitar el signal `tokenJwt`; inyectar `AuthService` y usar
      `auth.token()` para armar la URL del WebSocket (research.md
      Decisión 3); si `auth.token()` es `null`, no conectar y mostrar el
      mismo patrón de aviso que el resto de la aplicación; ante cierre
      con código de rechazo (`>= 4000`), redirigir a `/login`
- [X] T010 [US2] `apps/web/src/app/vuelos/estado-tiempo-real/estado-tiempo-real.html`:
      quitar el `<textarea>`/`<label for="tokenJwt">` (ya cubierto por el
      rediseño de T006, verificar que no queda ningún rastro)
- [X] T011 [P] [US2] `apps/web/src/app/billing/billing.service.ts`: quitar
      el parámetro `tokenJwt`/el helper `auth(tokenJwt)` de los 5
      métodos — `HttpClient` + `authInterceptor` ya agregan el header
- [X] T012 [US2] `apps/web/src/app/billing/panel-facturas/panel-facturas.ts`
      y `.html`: quitar el campo/textarea de token y dejar de pasarlo a
      `BillingService`
- [X] T013 [P] [US2] `apps/web/src/app/rampa/rampa.service.ts`: quitar el
      parámetro `tokenJwt`/el helper `auth(tokenJwt)` de todos los métodos
- [X] T014 [US2] `apps/web/src/app/rampa/panel-turnaround/panel-turnaround.ts`
      y `.html`: quitar el campo/textarea de token y dejar de pasarlo a
      `RampaService`
- [X] T015 [P] [US2] `apps/web/src/app/puertas/puertas.service.ts`: quitar
      el parámetro `tokenJwt` de todos los métodos
- [X] T016 [US2] `apps/web/src/app/puertas/tablero-puertas/tablero-puertas.ts`
      y `.html`: quitar el campo/textarea de token y dejar de pasarlo a
      `PuertasService`

**Checkpoint**: US2 verificable — SC-003; `grep -rn tokenJwt apps/web/src`
no debe encontrar nada.

---

## Phase 5: Documentación

- [X] T017 [P] `docs/PLAN_IMPLEMENTACION_v2.0.md`: sección §8.11 nueva
      (Sprint S1.11), formato de §8.1-§8.10
- [X] T018 [P] `CLAUDE.md`: fila S1.11 en la tabla de estado del plan
      (hash de commit cuando se cierre) y marcar en la sección de
      rediseño que S1.11 ya no está "sin empezar"

---

## Phase 6: Polish

- [X] T019 Ejecutar los 2 escenarios de [quickstart.md](./quickstart.md)
      completos contra Docker real (`monetdb`, `gateway`, `web`)
- [X] T020 `grep -rn "tokenJwt" apps/web/src` debe devolver cero
      coincidencias (verificación final de SC-003)
- [X] T021 Build de producción de `apps/web` en verde (`ng build` o
      equivalente del proyecto) — regresión mínima de que nada quedó roto

---

## Dependencies & Execution Order

- **Setup (Fase 1)** y **Foundational (Fase 2)**: sin dependencias entre
  sí más allá del orden dentro de la fase; bloquean US1/US2
- **US1 (Fase 3)**: depende de Foundational (necesita `.ah-tira` ya
  definido)
- **US2 (Fase 4)**: depende de Foundational solo para T009/T010 (comparte
  archivo con US1); T011-T016 (billing/rampa/puertas) son independientes
  entre sí y de US1 — pueden hacerse en paralelo
- **Documentación (Fase 5)**: en paralelo a todo, se cierra al final
- **Polish (Fase 6)**: depende de US1 y US2 completas

### Paralelismo

- T011/T013/T015 (los 3 `.service.ts`) en paralelo entre sí — archivos
  distintos, sin dependencias
- T009 (vuelos) es secuencial con T006-T008 (mismo archivo `.ts`)

## Implementation Strategy

1. Fase 1 + Fase 2: sistema de diseño listo
2. Fase 3: vista canónica rediseñada (US1)
3. Fase 4: deuda de JWT cerrada en las 4 vistas (US2) — T009/T010 tocan
   los mismos archivos que US1, hacerlas inmediatamente después de T006-T008
   evita reabrir el mismo componente dos veces
4. Fase 5: documentación
5. Fase 6: verificación final y build

## Notes

- Ninguna de las 3 vistas no-canónicas (billing/rampa/puertas) recibe
  rediseño visual en este sprint — solo pierden el token manual. Aplicar
  `.ah-tira`/`.ah-tabla` ahí es explícitamente alcance de S1.12/S1.13
  (no hacerlo aquí, sería adelantar trabajo de otro sprint y cargar el
  contexto de esta sesión).
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes (Principio V).
