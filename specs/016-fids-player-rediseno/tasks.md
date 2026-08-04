# Tasks: Rediseño de fids-player/pantalla-player

**Input**: Design documents from `specs/016-fids-player-rediseno/`

**Tests**: sin automatizados — verificación manual guiada por
[quickstart.md](./quickstart.md).

**Organización**: US1 (modo reproducción, P1), US2 (modo configuración,
P2), US3 (modo sin señal, P3).

## Phase 1: Setup

- [X] T001 [P] `apps/fids-player/src/styles.scss`: copiar variables
      `:root` de `apps/web/src/styles.scss` (navy/semáforo/fuentes,
      research.md Decisión 4) — sin `@use 'app/primitivos'`.
- [X] T002 [P] `apps/fids-player/src/index.html`: agregar los mismos
      `<link>` de Google Fonts (IBM Plex Sans/Mono) que
      `apps/web/src/index.html` (research.md Decisión 4).

## Phase 2: Foundational (bloqueante para las 3 historias)

- [X] T003 `apps/fids-player/src/app/pantallas/pantalla-player/pantalla-player.ts`:
      signal `modoActual` computado con 3 valores
      (`'configuracion'`|`'reproduccion'`|`'sin_senal'`) derivado de
      `conectado`/`error`/un nuevo signal `senalPerdida` (research.md
      Decisión 1) — sin lógica de detección todavía (eso es US3).
- [X] T004 `apps/fids-player/src/app/pantallas/pantalla-player/pantalla-player.html`:
      reestructurar en 3 bloques `@if (modoActual() === '...')`
      mutuamente excluyentes, reemplazando el HTML plano actual
      (T003 alimenta la condición).
- [X] T005 `apps/fids-player/src/app/pantallas/pantalla-player/pantalla-player.scss`
      NUEVO: layout base a pantalla completa (`height: 100vh`, sin
      scroll, `background`/`color` desde los tokens de T001).

**Checkpoint**: la vista carga sin errores en modo `configuracion` por
defecto (mismo comportamiento que hoy, solo con la nueva estructura).

---

## Phase 3: User Story 1 - Legibilidad del contenido en modo reproducción (Priority: P1)

- [X] T006 [US1] `pantalla-player.ts`: reemplazar `filasDeTexto()` para
      que, cuando no reconoce la estructura, devuelva un valor que el
      HTML use para mostrar el mensaje de respaldo "Contenido no
      disponible en este formato" (research.md Decisión 7) en vez del
      `<pre>{{ ... | json }}</pre>` actual.
- [X] T007 [US1] `pantalla-player.html`: bloque `@if (modoActual() === 'reproduccion')`
      con el contenido de la plantilla en tipografía monoespaciada
      grande (una fila por línea de `filasDeTexto()`, o el respaldo de
      T006), sin ningún botón/formulario/tabla administrativa visible
      (spec.md FR-002).
- [X] T008 [US1] `pantalla-player.scss`: escala tipográfica propia con
      `clamp()` (mínimo ≥ 3rem, research.md Decisión 5) para el bloque
      de contenido; transición de color/estado en ≤ 150ms si aplica
      semáforo por fila.

**Checkpoint**: US1 verificable — Escenario 1 de quickstart.md.

---

## Phase 4: User Story 2 - Modo de configuración distinto del de reproducción (Priority: P2)

- [X] T009 [US2] `pantalla-player.html`: bloque `@if (modoActual() === 'configuracion')`
      con el formulario de código+token existente (mismos campos,
      mismo `conectar()`), envuelto en una composición propia (no
      reutiliza el bloque de T007).
- [X] T010 [US2] `pantalla-player.scss`: estilo del modo configuración
      inspirado en `apps/web/auth/login` (franja/fondo navy, campo
      claro, research.md Decisión 6) — sin copiar `.ah-campo`/`.ah-btn`
      (no existe ese paquete en esta app, research.md Decisión 4).

**Checkpoint**: US2 verificable — Escenario 2 de quickstart.md.

---

## Phase 5: User Story 3 - Detección y recuperación de "sin señal" (Priority: P3)

- [X] T011 [US3] `pantalla-player.ts`: signal `senalPerdida` que se
      activa cuando el WebSocket cierra con `evento.code >= 4000` sin
      que medie un `desconectar()` manual, O cuando `enviarHeartbeat`
      falla 2 veces consecutivas (research.md Decisión 2) — alimenta
      `modoActual` (T003).
- [X] T012 [US3] `pantalla-player.ts`: al recibir `onmessage` del
      WebSocket o un heartbeat exitoso mientras `senalPerdida()` es
      verdadero, limpiarlo de inmediato (recuperación automática,
      research.md Decisión 3) — sin intervención manual.
- [X] T013 [US3] `pantalla-player.html`/`.scss`: bloque
      `@if (modoActual() === 'sin_senal')` con composición visual propia
      (distinta de T007 y T009), usando `--ah-estado-critico` de T001.

**Checkpoint**: US3 verificable — Escenario 3 de quickstart.md.

---

## Phase 6: Documentación y Polish

- [X] T014 [P] `docs/PLAN_IMPLEMENTACION_v2.0.md`: sección §8.14 nueva
      (S1.14 — FIDS player), mismo formato que §8.11-§8.13.
- [X] T015 [P] `CLAUDE.md`: fila S1.14 en la tabla de sprints, marcar el
      rediseño de interfaz (S1.11-S1.14) como cerrado.
- [X] T016 [P] `docs/diseno/DIRECCION_VISUAL.md`: marcar
      `fids-player/pantalla-player` como implementado en la tabla de
      §1, y registrar los tamaños de tipografía propios de esta app
      (research.md Decisión 5) como adenda de §2.3.
- [ ] T017 Ejecutar los 3 escenarios de quickstart.md contra Docker real
      (`docker compose up -d --build gateway fids-player`).
- [X] T018 Build de producción de `fids-player` en verde
      (`nx build fids-player --configuration=production`).

## Dependencies

- Fase 1 (Setup) y Fase 2 (Foundational) bloquean las 3 historias —
  ninguna historia puede verse sin los tokens (T001-T002) ni la
  estructura de 3 modos (T003-T005).
- US1 (Fase 3), US2 (Fase 4) y US3 (Fase 5) son independientes entre sí
  una vez completada la Fase 2 — pueden implementarse y verificarse en
  cualquier orden, aunque se sugiere P1→P2→P3 (mismo orden de prioridad
  de spec.md).
- Fase 6 depende de que las 3 historias estén completas.

## Parallel Example

```text
# Tras completar Fase 1 y Fase 2:
Task T006, T007, T008   (US1 -- reproduccion)
Task T009, T010          (US2 -- configuracion)
Task T011, T012, T013    (US3 -- sin_senal)
# Las 3 tocan pantalla-player.html/.ts/.scss en secciones distintas
# (bloques @if separados, signals separados) -- bajo riesgo de conflicto
# real si se hacen secuencialmente en una sola sesión, pero son
# conceptualmente independientes entre sí.
```

## Implementation Strategy

**MVP = US1 solo**: con Fase 1+2+3 completas, la pantalla ya muestra
contenido legible en modo reproducción (el caso de uso que justifica la
aplicación entera) — US2/US3 mejoran configuración inicial y manejo de
error, pero US1 sola ya es demostrable.

## Notes

- Cero cambios en `pantalla.service.ts` (spec.md FR-004, FR-009).
- Cero cambios de backend/contrato HTTP-WS/esquema en todo el sprint.
- Commit solo si se pide explícitamente.
