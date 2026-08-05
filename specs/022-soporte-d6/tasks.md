# Tasks: Soporte D6

**Input**: Design documents from `specs/022-soporte-d6/`

**Tests**: sin automatizados para el frontend; sí pytest de integración
para confirmar (sin corregir, a diferencia de S1.16/S1.19) que los 3
roles relevantes ya alcanzan `support:leer`/`support:escribir`.

**Organización**: US1 (tickets con SLA y conversación, P1), US2 (base
de conocimientos, P2), US3 (changelog, P3).

## Phase 1: Setup — el hallazgo de changelog que bloquea US3

- [X] T001 Leer `packages/contracts/aerohub_contracts/roles_modulos.py`
      y el dominio de cada caso de uso (`gestionar_tickets.py`,
      `gestionar_kb.py`, `gestionar_changelog.py`) -- confirmado:
      tickets/KB sin hallazgo (`role_sre`/`role_support`/
      `role_tenant_admin` ya alcanzan lo que necesitan), pero
      `publicar_changelog()` exige `role_platform_admin`
      (`_ROL_AUTORIZADO`) y ese rol no tenía ningún scope `support:*`
      -- `POST /support/changelog` era inalcanzable por cualquier rol
      (research.md Decisión 1).
- [X] T001b `packages/contracts/aerohub_contracts/roles_modulos.py`:
      agregar `support:leer`/`support:escribir` a `role_platform_admin`
      (research.md Decisión 1).
- [X] T001c `services/support/aerohub_support/{infrastructure/consultas.py,
      infrastructure/__init__.py, application/gestionar_tickets.py,
      application/__init__.py, api/router.py}`: agregar
      `GET /support/catalogo/categorias-ticket` (`support:leer`) --
      catálogo que faltaba para el formulario de alta de ticket (US1),
      mismo patrón de brecha ya corregido en S1.15 (contracts/support-api.md).

## Phase 2: Foundational (bloqueante para las 3 historias)

- [X] T002 [P] `apps/web/src/app/soporte/soporte.service.ts` NUEVO:
      interfaces (`Ticket`, `Mensaje`, `ArticuloKB`, `Changelog`,
      `ItemChangelog`, `CategoriaTicket`) y los 10 métodos HTTP que la
      vista necesita (catálogo de categorías, crear/listar/obtener
      ticket, responder, cambiar estado, publicar/buscar artículo,
      publicar/listar changelog) -- sin `GET /support/observabilidad/uptime`
      (research.md Decisión 5).
- [X] T003 `apps/web/src/app/app.routes.ts`: ruta `soporte/panel` →
      componente `PanelSoporte` (T004).
- [X] T004 `apps/web/src/app/shell/shell.ts`: `puedeVerSoporte()`
      computed por scope `support:leer` (mismo mecanismo que
      `puedeVerTarifarios`, research.md Decisión 2).
- [X] T005 `apps/web/src/app/shell/shell.html`: enlace condicional
      "Soporte" → `/soporte/panel` cuando `puedeVerSoporte()`.

**Checkpoint**: la ruta existe y el enlace aparece para un perfil con
`support:leer` -- confirma T003-T005 antes de construir las secciones.

---

## Phase 3: User Story 1 - Bandeja de tickets con SLA y conversación (Priority: P1)

- [X] T006 [US1] `apps/web/src/app/soporte/panel-soporte/panel-soporte.ts`
      NUEVO: signals de alta de ticket (categoría, severidad, asunto,
      cuerpo inicial) y listado con filtros de estado/severidad.
- [X] T007 [US1] `panel-soporte.ts`: función pura de cálculo de
      indicador de SLA (restante/vencido) a partir de `creado_en`,
      `sla_objetivo_min` y `primera_respuesta_en` (research.md
      Decisión 3, calculado en el cliente).
- [X] T008 [US1] `panel-soporte.ts`: signals de detalle de ticket
      (hilo de mensajes, responder con `es_interno` visible solo si
      `perfil().rol_codigo === 'role_support'` -- contracts/support-api.md
      hallazgo de `MensajeInternoNoAutorizado`), cambio de estado
      mostrando solo las transiciones válidas del estado actual
      (data-model.md) **y solo para `role_support`** (research.md
      Decisión 1-ter, hallazgo revelado por el test de integración).
- [X] T009 [US1] `apps/web/src/app/soporte/panel-soporte/panel-soporte.html`:
      sección "Tickets" -- `.ah-panel` de alta, `.ah-tabla` de bandeja
      con columna de SLA (`.ah-punto` o `.ah-pill` según vencido/no
      vencido), `.ah-modal` de detalle con hilo e input de respuesta.
- [X] T009b [US1] `panel-soporte.ts`/`.html`: ocultar la sección
      completa de "Tickets" (sin llamar a `listarTickets()`) cuando
      `perfil().rol_codigo === 'role_platform_admin'` (research.md
      Decisión 1-bis -- ese rol no tiene tenant, `listar_tickets_de_tenant`
      lanza `ContextoTenantAusente`/500).

**Checkpoint**: US1 verificable -- Escenario 1 de quickstart.md.

---

## Phase 4: User Story 2 - Base de conocimientos compartida (Priority: P2)

- [X] T010 [US2] `panel-soporte.ts`: signals de búsqueda (texto +
      etiqueta) y alta de artículo (título, cuerpo, etiquetas) --
      `puedeEscribirKB()` restringido a `role_support`/
      `role_platform_admin` (hallazgo de `gestionar_kb.py::_ROLES_AUTORIZADOS`).
- [X] T011 [US2] `panel-soporte.html`: sección "Base de conocimientos"
      -- aviso fijo y visible de contenido compartido entre tenants
      (research.md Decisión 4, FR-008/SC-004), formulario de alta,
      tabla/lista de resultados de búsqueda.

**Checkpoint**: US2 verificable -- Escenario 2 de quickstart.md.

---

## Phase 5: User Story 3 - Changelog publicable (Priority: P3)

- [X] T012 [US3] `panel-soporte.ts`: signals de alta de changelog
      (versión, resumen, items dinámicos con módulo M1-M9 + tipo de
      cambio) y listado -- `puedeEscribirChangelog()` restringido a
      `role_platform_admin` (research.md Decisión 1, hallazgo de scopes).
- [X] T013 [US3] `panel-soporte.html`: sección "Changelog" -- formulario
      de alta con items dinámicos (agregar/quitar fila), listado más
      reciente primero con sus items agrupados.

**Checkpoint**: US3 verificable -- Escenario 3 de quickstart.md.

---

## Phase 6: Polish y verificación

- [X] T014 [US1] `panel-soporte.ts`/`.html`: ocultar controles de
      escritura (responder, cambiar estado, publicar artículo,
      publicar changelog) cuando el perfil no tenga
      `support:escribir` (FR-011), y además por rol específico donde
      el dominio lo exige (T008/T010/T012).
- [X] T015 [P] `tests/integration/test_soporte_hub.py` NUEVO -- 8 tests:
      catálogo de categorías, ciclo de ticket con `role_tenant_admin`,
      `MensajeInternoNoAutorizado` (403 para tenant, visible/invisible
      según rol), transición de estado (403 por rol + 409 por
      transición inválida), KB visible entre tenants + 403 para
      tenant, changelog publicado por `role_platform_admin` + 403 para
      `role_support` -- 12/12 en verde junto con la suite existente
      `test_kb_changelog.py`, sin regresiones en
      `test_ticket_sla.py`/`test_pn01_tickets_cross_tenant.py`/
      `tests/unit/support` (30/30).
- [X] T016 [P] `docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.6: sin cambios
      de contenido necesarios -- solo referenciar el commit al cerrar.
- [X] T017 [P] `CLAUDE.md`: fila S1.20 en la tabla de sprints + resumen
      -- **este sprint cierra la Fase 1.5 completa (S1.15-S1.20)**,
      documentado explícitamente.
- [X] T018 `ruff`/`mypy` en verde sobre `services/support` +
      `packages/contracts` (contra la imagen reconstruida en Docker).
- [ ] T019 Ejecutar los 3 escenarios de quickstart.md contra Docker
      real -- solo si el usuario lo pide explícitamente (regla
      vigente).
- [X] T020 Build de producción de `apps/web` en verde.

## Dependencies

- Fase 1 (T001) bloquea todo lo demás -- confirma que no hace falta
  ningún cambio de scopes antes de construir sobre ese supuesto.
- Fase 2 (Foundational) bloquea las 3 historias.
- US1 (Fase 3) es el flujo central del sprint -- se implementa primero.
- US2 y US3 (Fases 4-5) son independientes entre sí y de US1 una vez
  que Foundational está lista.
- Fase 6 depende de las 3 historias completas.

## Implementation Strategy

**MVP = US1**: con Fase 1+2+3, el flujo central (bandeja + SLA +
conversación + transición de estado) es demostrable de punta a punta.
US2/US3 completan el resto de la superficie sin bloquear la
demostración inicial.

## Notes

- Backend sin cambios esperados (a diferencia de S1.15-S1.19) -- si
  T001 revela un hallazgo de scopes, tratarlo con la misma disciplina
  que S1.16/S1.19 (corregir, verificar con `TestClient`, documentar).
- `GET /support/observabilidad/uptime` queda sin vista por diseño
  (research.md Decisión 5) -- no crear ninguna tarea para él.
- Commit solo si se pide explícitamente.
