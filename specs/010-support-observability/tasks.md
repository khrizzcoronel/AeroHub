# Tasks: S1.8 -- Soporte D6 y observabilidad

**Input**: Design documents from `specs/010-support-observability/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: incluidas -- Principio III/IV de la constitución.

**Organización**: por historia de usuario (US1-US5 de `spec.md`), en
orden de prioridad (P1, P1, P2, P3, P3).

## Phase 1: Setup

- [X] T001 Confirmar `services/support/pyproject.toml` (dependencias:
      `fastapi`, `pydantic`, `aerohub-kernel`, `aerohub-contracts`,
      `aerohub-repository` -- mismo patrón que `aerohub_compliance`)
- [X] T002 [P] Confirmar `.importlinter` ya incluye `aerohub_support`
      como root package y contrato de capas (si no, agregarlo -- mismo
      patrón que módulos anteriores)
- [X] T003 [P] Crear `tools/verificar_error_budget.py` como script
      standalone (sin dependencias del monorepo más allá de
      `aerohub-repository` para auditar y un cliente HTTP para
      Prometheus) -- estructura base, sin lógica todavía

---

## Phase 2: Foundational (bloqueante para US1/US4/US5)

**Propósito**: DDL del esquema `support` completo + grants -- ninguna
historia de tickets/KB/changelog puede implementarse sin esto. US2/US3
(observabilidad) NO dependen de esta fase (research.md Decisión 1/2: sin
tabla nueva) y pueden desarrollarse en paralelo.

**⚠️ CRÍTICO**: ninguna tarea de US1/US4/US5 empieza antes de cerrar
esta fase.

- [X] T004 `db/ddl/monetdb/14_support.sql`: las 8 tablas de
      [data-model.md](./data-model.md) transcritas fielmente del SDD §11
      (`categoria_ticket`, `ticket`, `ticket_mensaje`, `articulo_kb`,
      `etiqueta`, `articulo_kb_etiqueta`, `changelog`, `changelog_item`),
      con todos los CHECK/FK especificados
- [X] T005 `db/ddl/monetdb/99_grants_support.sql`: grants por rol
      (`role_support` con INSERT/UPDATE en `ticket`/`ticket_mensaje` +
      INSERT/UPDATE en `articulo_kb`/`etiqueta`/`articulo_kb_etiqueta`;
      `role_platform_admin` con INSERT en `changelog`/`changelog_item`;
      resto de roles de tenant con SELECT en las tablas propias de su
      tenant + SELECT global en KB/changelog; explícitamente SIN acceso
      a datos financieros vía este esquema)
- [X] T006 [P] `db/seeds/generate.py`: sembrar `support.categoria_ticket`
      (AODB, FIDS, Gates, Rampa, Billing, Cuenta -- un código por
      módulo/categoría de ejemplo)
- [X] T007 [P] `services/support/aerohub_support/infrastructure/tablas.py`:
      `Table()` de las 8 tablas propias
- [X] T008 [P] `services/support/aerohub_support/infrastructure/alcances.py`:
      registro G1 (`tenant`/`global`/`interno` según data-model.md --
      `ticket` tenant, `ticket_mensaje` interno, resto global)
- [X] T009 Verificación empírica: aplicar el DDL contra MonetDB real en
      Docker, confirmar las 8 tablas creadas con sus constraints

**Checkpoint**: esquema `support` completo y verificado en MonetDB real
-- US1/US4/US5 pueden empezar.

---

## Phase 3: User Story 1 - Gestión de tickets de soporte con SLA (Priority: P1) 🎯 MVP

**Goal**: un usuario de tenant crea un ticket con SLA automático según
el módulo afectado; `role_support` responde en un hilo, la primera
respuesta se marca una única vez, y los mensajes internos no son
visibles al tenant.

**Independent Test**: crear ticket -> responder como `role_support` ->
verificar `primera_respuesta_en` fijado una vez -> tenant de otro
tenant recibe 404 -- Escenario 1 de `quickstart.md`.

### Tests para US1

- [X] T010 [P] [US1] Test de dominio: transición de estado de ticket
      (rechaza `abierto` -> `resuelto` directo), cálculo de
      `sla_objetivo_min` por módulo, en
      `tests/unit/support/test_ticket.py`
- [X] T011 [P] [US1] Test de integración: ciclo completo crear ->
      responder -> `primera_respuesta_en` estable ante mensajes
      posteriores -> cambiar estado; mensaje interno oculto al tenant,
      en `tests/integration/test_ticket_sla.py`
- [X] T012 [P] [US1] Test negativo (PN-01): ticket de un tenant no
      accesible por usuario de otro tenant (404, no 403), en
      `tests/negative/test_pn01_tickets_cross_tenant.py`

### Implementación de US1

- [X] T013 [P] [US1] `services/support/aerohub_support/domain/ticket.py`:
      `Ticket`, `TicketMensaje`, máquina de transición de estados,
      `calcular_sla_objetivo_min(modulo)`
- [X] T014 [US1] `services/support/aerohub_support/infrastructure/comandos.py`
      (parcial): `insertar_ticket`, `insertar_ticket_mensaje`,
      `actualizar_estado_ticket`, `fijar_primera_respuesta` (solo si es
      NULL -- UPDATE condicional)
- [X] T015 [US1] `services/support/aerohub_support/infrastructure/consultas.py`
      (parcial): `obtener_ticket_por_id`, `listar_tickets`,
      `listar_mensajes_de_ticket`
- [X] T016 [US1] `services/support/aerohub_support/application/gestionar_tickets.py`:
      `crear_ticket`, `responder_ticket` (fija `primera_respuesta_en` la
      primera vez que el autor es `role_support`), `cambiar_estado_ticket`;
      consultas de `role_support` vía `alcance_global(motivo=..., rol="role_support")`
      (research.md Decisión 5) (depende de T013-T015)
- [X] T017 [US1] `services/support/aerohub_support/api/router.py`
      (parcial): `POST /support/tickets`, `GET /support/tickets/{id}`,
      `GET /support/tickets`, `POST /support/tickets/{id}/mensajes`,
      `PATCH /support/tickets/{id}/estado`
- [X] T018 [US1] Montar `router_support` en `services/gateway/main.py`
      (sin agregar el prefijo a `PREFIJO_A_CODIGO_MODULO` -- research.md
      Decisión 7)

**Checkpoint**: US1 funcional -- SC-001/SC-002 verificables. MVP del
sprint.

---

## Phase 4: User Story 2 - Visibilidad de uptime y error budget (Priority: P1)

**Goal**: un endpoint calcula a demanda, contra Prometheus, el uptime
mensual y el consumo de error budget de AODB/FIDS; Grafana lo visualiza
sin persistencia nueva.

**Independent Test**: consultar `/support/observabilidad/uptime` con
métricas simuladas en Prometheus y verificar el porcentaje reportado --
Escenario 2 de `quickstart.md`. No depende de la Fase 2 (Foundational).

### Tests para US2

- [X] T019 [P] [US2] Test de dominio: cálculo puro de error budget
      (uptime observado vs. objetivo de SLA -> porcentaje de budget
      consumido), casos borde 0 %/100 %/>100 %, en
      `tests/unit/support/test_error_budget.py`
- [X] T020 [P] [US2] Test de integración: `GET /support/observabilidad/uptime`
      con Prometheus real en Docker (métricas sintéticas vía
      `/metrics` del gateway) responde uptime y error budget del mes en
      curso, en `tests/integration/test_uptime_observabilidad.py`

### Implementación de US2

- [X] T021 [P] [US2] `services/support/aerohub_support/domain/error_budget.py`:
      `calcular_consumo_error_budget(uptime_observado_pct, objetivo_slo_pct)`
      -- función pura, sin I/O
- [X] T022 [US2] `services/support/aerohub_support/infrastructure/prometheus.py`:
      cliente HTTP mínimo contra `/api/v1/query` de Prometheus,
      `consultar_uptime_mensual(servicio)` (depende de T021 solo para
      el tipo de retorno)
- [X] T023 [US2] `services/support/aerohub_support/application/consultar_observabilidad.py`:
      orquesta infraestructura + dominio, expone
      `obtener_uptime_y_error_budget(servicio)` (depende de T021-T022)
- [X] T024 [US2] `services/support/aerohub_support/api/router.py`
      (parcial): `GET /support/observabilidad/uptime`
- [X] T025 [P] [US2] `infra/prometheus/alertas.yml`: reglas Sev1-Sev3
      sobre disponibilidad de AODB/FIDS
- [X] T026 [US2] `infra/prometheus/prometheus.yml`: agregar
      `rule_files: [alertas.yml]`
- [X] T027 [US2] Verificación empírica: dashboard de Grafana muestra
      uptime/error budget leyendo Prometheus sin configuración manual
      adicional (data source ya provisto desde S0.1)

**Checkpoint**: US2 funcional -- SC-003 verificado. US1+US2 = MVP
completo del sprint (cubre las dos compuertas de prioridad M/S
centrales del DoD).

---

## Phase 5: User Story 3 - Bloqueo automático de despliegues por error budget (Priority: P2)

**Goal**: `tools/verificar_error_budget.py` bloquea (código de salida
≠0) cuando el consumo de error budget de un servicio supera 80 %, salvo
override auditado por un rol de plataforma.

**Independent Test**: escenario simulado con consumo >80 % -> script
retorna 1; con `--override --motivo` -> retorna 0 y audita; con
`--override` sin motivo -> retorna 2, sin auditar -- Escenario 3 de
`quickstart.md`. Depende de US2 (reutiliza
`obtener_uptime_y_error_budget`).

### Tests para US3

- [X] T028 [US3] Test de integración: los 4 casos del script
      (bloquea/override con motivo/override sin motivo/no bloquea) con
      Prometheus real y verificación de la fila en
      `compliance.log_auditoria`, en
      `tests/integration/test_error_budget_gate.py`

### Implementación de US3

- [X] T029 [US3] `tools/verificar_error_budget.py`: lógica completa --
      parsea `--servicio`/`--override`/`--motivo`, reutiliza
      `aerohub_support.application.consultar_observabilidad`, decide
      código de salida según [contracts/error-budget-gate.md](./contracts/error-budget-gate.md),
      audita el override con `registrar_auditoria(esquema="observabilidad",
      tabla="bloqueo_despliegue", operacion="UPDATE", ...)` (depende de
      T023)
- [X] T030 [US3] Documentar en `.github/workflows/ci.yml` (comentario,
      no wiring real -- no existe pipeline de CD todavía) el punto donde
      un futuro job de despliegue invocaría el script, referenciando
      [contracts/error-budget-gate.md](./contracts/error-budget-gate.md)

**Checkpoint**: US3 funcional -- SC-004 verificado en escenario
simulado.

---

## Phase 6: User Story 4 - Base de conocimientos con etiquetado (Priority: P3)

**Goal**: `role_support` publica artículos versionados de KB, sin
tenant, etiquetables y buscables por texto/etiqueta.

**Independent Test**: publicar artículo con etiquetas -> buscar por
etiqueta -> aparece; publicar nueva versión -> ambas identificables --
Escenario 4 (parte 1) de `quickstart.md`.

### Tests para US4

- [X] T031 [P] [US4] Test de dominio: invariantes de `articulo_kb`
      (transición borrador -> publicado -> archivado; UQ
      titulo+version), en `tests/unit/support/test_articulo_kb.py`
- [X] T032 [P] [US4] Test de integración: publicar, versionar, buscar
      por texto y por etiqueta, artículo archivado no aparece en
      búsqueda, en `tests/integration/test_kb_changelog.py`

### Implementación de US4

- [X] T033 [P] [US4] `services/support/aerohub_support/domain/articulo_kb.py`:
      `ArticuloKB`, invariantes de versión/estado
- [X] T034 [US4] `services/support/aerohub_support/infrastructure/comandos.py`
      (resto): `insertar_articulo_kb`, `publicar_articulo_kb`,
      `insertar_etiqueta`, `asociar_etiqueta_articulo`
- [X] T035 [US4] `services/support/aerohub_support/infrastructure/consultas.py`
      (resto): `buscar_articulos_kb(texto, etiqueta)` (`ILIKE` sobre
      `titulo`/`cuerpo`, join con `articulo_kb_etiqueta`)
- [X] T036 [US4] `services/support/aerohub_support/application/gestionar_kb.py`:
      `publicar_articulo`, `buscar_articulos` (depende de T033-T035)
- [X] T037 [US4] `services/support/aerohub_support/api/router.py`
      (parcial): `POST /support/kb/articulos`,
      `GET /support/kb/articulos`, `GET /support/kb/articulos/{id}`

**Checkpoint**: US4 funcional -- SC-005 verificado.

---

## Phase 7: User Story 5 - Publicación de changelog (Priority: P3)

**Goal**: `role_platform_admin` publica changelog con ítems por módulo
y tipo de cambio, visible a todos los tenants sin condicionar a
licencia.

**Independent Test**: publicar changelog con ítem de un módulo no
licenciado por un tenant -> el tenant lo ve igual -- Escenario 4 (parte
2) de `quickstart.md`.

### Tests para US5

- [X] T038 [US5] Test de integración: publicar changelog con ítems,
      tenant sin licencia del módulo referenciado igual lo ve, en
      `tests/integration/test_kb_changelog.py` (mismo archivo que T032,
      casos adicionales)

### Implementación de US5

- [X] T039 [P] [US5] `services/support/aerohub_support/infrastructure/tablas.py`:
      redeclaración local de `catalogo.modulo` (patrón ya usado 4 veces
      desde S1.4) -- si no está ya cubierto por T007
- [X] T040 [US5] `services/support/aerohub_support/infrastructure/comandos.py`
      (resto): `insertar_changelog`, `insertar_changelog_item`
- [X] T041 [US5] `services/support/aerohub_support/application/gestionar_changelog.py`:
      `publicar_changelog` (depende de T039-T040)
- [X] T042 [US5] `services/support/aerohub_support/api/router.py`
      (resto): `POST /support/changelog`, `GET /support/changelog`

**Checkpoint**: US5 funcional -- SC-006 verificado. Las 5 historias
completas e independientemente probadas.

---

## Phase 8: Polish & Cross-Cutting

- [X] T043 Regresión completa de pruebas negativas PN-01 a PN-11,
      PN-04 reforzada y suite cruzada existentes -- confirmar que
      `aerohub_support` y `tools/verificar_error_budget.py` no rompen
      nada
- [X] T044 `ruff check .`, `mypy .`, `bandit -r services/support tools`,
      `lint-imports` en verde, corriendo dentro del contenedor del
      gateway (Docker)
- [X] T045 Ejecutar los 4 escenarios de [quickstart.md](./quickstart.md)
      completos contra MonetDB real + Prometheus real en Docker
- [X] T046 Actualizar `CLAUDE.md`: fila S1.8 en "Estado del plan" con el
      hash del commit, una vez cerrado

---

## Dependencies & Execution Order

### Fases

- **Setup (Fase 1)**: sin dependencias
- **Foundational (Fase 2)**: depende de Setup -- BLOQUEA US1/US4/US5
  (todo lo que toca el esquema `support`). NO bloquea US2/US3
  (observabilidad, sin tabla nueva)
- **US1 (Fase 3, P1)**: depende de Foundational -- MVP junto con US2
- **US2 (Fase 4, P1)**: depende solo de Setup (T003) -- independiente
  de Foundational y de US1, puede desarrollarse en paralelo desde el
  inicio
- **US3 (Fase 5, P2)**: depende de US2 (reutiliza
  `consultar_observabilidad`)
- **US4 (Fase 6, P3)**: depende de Foundational -- independiente de
  US1/US2/US3 salvo que comparte el módulo `aerohub_support` (mismo
  `comandos.py`/`router.py`, conviene secuenciar tras US1)
- **US5 (Fase 7, P3)**: depende de Foundational y de la redeclaración
  de `catalogo.modulo` (T007/T039) -- independiente de US1-US4
  funcionalmente
- **Polish (Fase 8)**: depende de todas las historias incluidas

### Oportunidades de paralelismo

- US2 (observabilidad) puede empezar el mismo día que Foundational,
  sin esperarla -- no comparte ninguna tabla ni archivo con US1/US4/US5
  hasta T024 (mismo `api/router.py`, que sí requiere secuenciar la
  edición del archivo)
- Dentro de Foundational: T006-T008 en paralelo
- Dentro de cada historia: dominio [P] e infraestructura [P] en
  paralelo; `application/`/`api/router.py`/montaje en Gateway son
  secuenciales
- US3 y US4 pueden desarrollarse en paralelo entre sí (módulos/archivos
  distintos: `tools/` vs. `aerohub_support/domain/articulo_kb.py`)

---

## Parallel Example: User Story 1

```bash
# Tests de US1 en paralelo:
Task: "Test de dominio de ticket en tests/unit/support/test_ticket.py"
Task: "Test de integración SLA en tests/integration/test_ticket_sla.py"
Task: "Test PN-01 cross-tenant en tests/negative/test_pn01_tickets_cross_tenant.py"

# Dominio e infraestructura de US1 en paralelo:
Task: "domain/ticket.py"
Task: "infrastructure/tablas.py + alcances.py (Foundational, ya cerrada)"
```

---

## Implementation Strategy

### MVP primero (US1 + US2)

1. Fase 1: Setup
2. Fase 2: Foundational (crítico para US1, no para US2)
3. Fase 3: US1 -- tickets con SLA (SC-001/SC-002)
4. Fase 4: US2 -- uptime y error budget (SC-003), en paralelo a Fase 2/3
5. **Validar**: Escenario 1 y 2 de `quickstart.md`
6. Cubre las dos compuertas de prioridad M del DoD -- entregable mínimo
   con valor real

### Entrega incremental

1. Setup + Foundational -> esquema `support` listo
2. US1 -> tickets con SLA (MVP parcial)
3. US2 -> visibilidad de uptime/error budget (MVP completo del DoD)
4. US3 -> bloqueo automático de despliegues
5. US4 -> base de conocimientos
6. US5 -> changelog
7. Polish -> regresión, calidad, cierre de sprint

---

## Notes

- US2/US3 (observabilidad) son las únicas historias de este sprint sin
  DDL propio -- research.md Decisiones 1/2 documentan por qué, y T045
  verifica el escenario de bloqueo de forma simulada porque no existe
  CD real contra el cual probarlo de verdad (mismo criterio que el DoD
  de S1.8 exige explícitamente).
- El acceso cross-tenant de `role_support` (T016) usa `alcance_global()`
  auditado -- no es una excepción nueva, es el mismo mecanismo en uso
  desde S0.2.
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes.
