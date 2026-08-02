# Tasks: S1.7 -- Licenciamiento, credenciales y Compliance Hub

**Input**: Design documents from `specs/009-compliance-licensing-hub/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: incluidas -- Principio III/IV de la constitución.

**Organización**: por historia de usuario (US1-US4 de `spec.md`), en orden
de prioridad (P1, P1, P2, P3).

## Phase 1: Setup

- [X] T001 Confirmar `services/compliance/pyproject.toml` (dependencias:
      `fastapi`, `pydantic`, `aerohub-kernel`, `aerohub-contracts`,
      `aerohub-repository` -- mismo patrón que `aerohub_billing`)
- [X] T002 [P] Confirmar `.importlinter` ya incluye `aerohub_compliance`
      como root package y contrato de capas (si no, agregarlo -- mismo
      patrón que `aerohub_billing`/`aerohub_passenger` en S1.6)

---

## Phase 2: Foundational (bloqueante para todas las historias)

**Propósito**: DDL del esquema `compliance` completo + grants + catálogo
`catalogo.modulo` sembrado (primera vez) -- ninguna historia puede
implementarse sin esto.

**⚠️ CRÍTICO**: ninguna tarea de US1-US4 empieza antes de cerrar esta fase.

- [X] T003 `db/ddl/monetdb/13_compliance_hub.sql`: las 9 tablas de
      [data-model.md](./data-model.md) transcritas fielmente del SDD §10
      (`tipo_incidente`, `incidente_seguridad`,
      `tipo_reporte_regulatorio`, `reporte_dgac`, `acceso_auditor`,
      `post_mortem`, `post_mortem_accion`, `control_soc2`,
      `evidencia_soc2`), con todos los CHECK/FK especificados
- [X] T004 `db/ddl/monetdb/99_grants_compliance_hub.sql`: grants por rol
      (`role_sre` con INSERT/UPDATE en `post_mortem`/`post_mortem_accion`
      + INSERT en el resto; `role_platform_admin`/`role_regulatory_auditor`
      con SELECT amplio; `role_tenant_analyst`/`role_business_viewer` sin
      acceso)
- [X] T005 [P] `db/seeds/generate.py`: sembrar `catalogo.modulo`
      (`AODB`, `FIDS`, `GATE`, `RAMP`, `BILL`, `PASS` -- primera vez que
      se puebla esta tabla), `compliance.tipo_incidente`,
      `compliance.tipo_reporte_regulatorio`, `compliance.control_soc2`
      (un código de ejemplo cada uno)
- [X] T006 [P] `services/compliance/aerohub_compliance/infrastructure/tablas.py`:
      `Table()` de las 9 tablas propias
- [X] T007 [P] `services/compliance/aerohub_compliance/infrastructure/alcances.py`:
      registro G1 (`tenant`/`global`/`interno` según data-model.md)
- [X] T008 Verificación empírica: aplicar el DDL contra MonetDB real en
      Docker, confirmar las 9 tablas creadas con sus constraints

**Checkpoint**: esquema `compliance` completo y verificado en MonetDB
real -- las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - El sistema deniega acceso a un módulo sin licencia vigente (Priority: P1) 🎯 MVP

**Goal**: `AutenticacionJWTMiddleware` verifica `tenants.licencia` tras
autenticar, deniega con 403 si no hay licencia vigente para el módulo de
la ruta, y audita el intento.

**Independent Test**: tenant sin licencia para `billing` invoca
`GET /billing/facturas` -> 403 + fila nueva en `log_auditoria` --
Escenario 1 de `quickstart.md`.

### Tests para US1

- [X] T009 [P] [US1] Test de dominio: `PREFIJO_A_CODIGO_MODULO` resuelve
      cada prefijo de ruta conocido al código de 4 caracteres correcto,
      en `tests/unit/gateway/test_licencia.py`
- [X] T010 [P] [US1] Test de integración (PN-09): sin licencia -> 403 +
      auditoría; licencia vigente -> pasa; licencia vencida -> 403, en
      `tests/negative/test_pn09_licenciamiento.py`

### Implementación de US1

- [X] T011 [P] [US1] `services/gateway/aerohub_gateway/domain/licencia.py`:
      `PREFIJO_A_CODIGO_MODULO`, `LicenciaInvalida`,
      `resolver_modulo_de_ruta(path)`
- [X] T012 [P] [US1] `services/gateway/aerohub_gateway/infrastructure/licencia.py`:
      `Table()` local de `tenants.licencia`, redeclarada (mismo patrón que
      `ops.vuelo` en gates/ramp), `obtener_licencia_vigente(tenant_id, modulo_codigo, ahora)`
- [X] T013 [US1] `services/gateway/aerohub_gateway/application/verificar_licencia.py`:
      orquesta dominio + infraestructura, decide permitir/denegar,
      registra en `compliance.log_auditoria` si deniega (depende de
      T011-T012)
- [X] T014 [US1] `services/gateway/aerohub_gateway/api/middleware.py`:
      invocar `verificar_licencia` DESPUÉS de `contexto_autenticado`,
      ANTES de `peticion_permitida` (rate limiting) o después -- decidir
      orden y documentar por qué, devolver 403 si deniega

**Checkpoint**: US1 funcional -- SC-001 verificado. MVP del sprint.

---

## Phase 4: User Story 2 - role_sre redacta y cierra un post-mortem (Priority: P1)

**Goal**: `role_sre` crea un post-mortem, edita `causa_raiz` (excepción
ADR-009), agrega/completa acciones de remediación, y solo puede publicar
cuando todas están completadas.

**Independent Test**: ciclo completo crear -> editar -> completar
acciones -> publicar; publicar con acciones pendientes falla -- Escenario
2 de `quickstart.md`.

### Tests para US2

- [X] T015 [P] [US2] Test de dominio: `puede_publicar(acciones)` es
      `False` si alguna no está `completada`, `True` si todas lo están,
      en `tests/unit/compliance/test_post_mortem.py`
- [X] T016 [P] [US2] Test de integración: ciclo completo con `role_sre`
      -> éxito; publicar con acción pendiente -> 409; crear/editar con
      `role_support` -> rechazado, en
      `tests/integration/test_compliance_post_mortem.py`

### Implementación de US2

- [X] T017 [P] [US2] `services/compliance/aerohub_compliance/domain/post_mortem.py`:
      `PostMortem`, `PostMortemAccion`, `puede_publicar(acciones)`
- [X] T018 [US2] `services/compliance/aerohub_compliance/infrastructure/comandos.py`
      (parcial): `insertar_post_mortem`, `actualizar_post_mortem`,
      `insertar_post_mortem_accion`, `completar_post_mortem_accion` --
      ÚNICAS funciones de UPDATE de todo el módulo
- [X] T019 [US2] `services/compliance/aerohub_compliance/application/gestionar_post_mortem.py`:
      valida `contexto_rol_actor() == "role_sre"` antes de cualquier
      mutación; `publicar_post_mortem` consulta acciones y rechaza si
      alguna no está completada (depende de T017-T018)
- [X] T020 [US2] `services/compliance/aerohub_compliance/api/router.py`
      (parcial): `POST /compliance/post-mortems`,
      `PATCH /compliance/post-mortems/{id}`,
      `POST /compliance/post-mortems/{id}/acciones`,
      `POST .../acciones/{id}/completar`, `POST .../publicar`,
      `GET /compliance/post-mortems/{id}`
- [X] T021 [US2] Montar `router_compliance` en `services/gateway/main.py`

**Checkpoint**: US2 funcional -- SC-002 verificado (post-mortem
publicable, tiempo medido). US1+US2 = MVP completo del sprint.

---

## Phase 5: User Story 3 - Auditoría append-only sobre las 4 tablas nuevas (Priority: P2)

**Goal**: `incidente_seguridad`, `reporte_dgac`, `acceso_auditor`,
`evidencia_soc2` son append-only -- ningún método de mutación existe para
ellas en la capa de repositorio.

**Independent Test**: análisis estático del módulo confirma que solo
existen funciones `insertar_*` para estas 4 tablas -- Escenario 3 de
`quickstart.md`.

### Tests para US3

- [X] T022 [US3] Test de análisis estático (mismo patrón que PN-15):
      recorre `aerohub_compliance.infrastructure.comandos` y falla si
      aparece `actualizar_*`/`eliminar_*` para
      `incidente_seguridad`/`reporte_dgac`/`acceso_auditor`/
      `evidencia_soc2`, en
      `tests/negative/test_pn04_compliance_append_only.py`

### Implementación de US3

- [X] T023 [P] [US3] `services/compliance/aerohub_compliance/domain/incidente_seguridad.py`
      y `reporte_dgac.py`: invariantes de una fila aislada
      (severidad/estado válidos, `periodo_fin >= periodo_inicio`)
- [X] T024 [US3] `services/compliance/aerohub_compliance/infrastructure/comandos.py`
      (resto): `insertar_incidente_seguridad`, `insertar_reporte_dgac`,
      `insertar_acceso_auditor`, `insertar_evidencia_soc2` -- SOLO INSERT
- [X] T025 [US3] `services/compliance/aerohub_compliance/application/gestionar_incidentes.py`,
      `gestionar_reportes.py`, `gestionar_evidencia_soc2.py`
- [X] T026 [US3] `services/compliance/aerohub_compliance/api/router.py`
      (resto): `POST /compliance/incidentes`, `GET /compliance/incidentes`,
      `POST /compliance/reportes-dgac`, `POST /compliance/accesos-auditor`,
      `POST /compliance/evidencia-soc2`

**Checkpoint**: US3 funcional -- SC-003 verificado (análisis estático en
verde).

---

## Phase 6: User Story 4 - Rotación de API Keys con evento auditado (Priority: P3)

**Goal**: rotar una API Key emite un secreto nuevo sin perder acceso,
marca la anterior `revocada`+`rotada_en`, y audita el evento.

**Independent Test**: crear -> rotar -> confirmar key anterior revocada,
key nueva activa, evento en `log_auditoria` -- Escenario 4 de
`quickstart.md`.

### Tests para US4

- [X] T027 [US4] Test de integración: rotar produce key nueva activa +
      key anterior `revocada`/`rotada_en` poblado + fila en
      `log_auditoria`, en `tests/integration/test_rotar_api_key.py`

### Implementación de US4

- [X] T028 [US4] `services/tenancy/aerohub_tenancy/infrastructure/comandos_api_key.py`:
      `rotar_api_key_fila_anterior(conn, *, id, tenant_id, rotada_en)` --
      set `estado='revocada'`, `rotada_en`
- [X] T029 [US4] `services/tenancy/aerohub_tenancy/application/gestionar_api_key.py`:
      `rotar_api_key(*, api_key_id)` -- inserta key nueva (reusa lógica de
      `crear_api_key`) + marca la anterior, ambos en la misma transacción
      (depende de T028)
- [X] T030 [US4] `services/tenancy/aerohub_tenancy/api/router.py`:
      `POST /tenants/api-keys/{id}/rotar`

**Checkpoint**: US4 funcional -- SC-004 verificado. Las 4 historias
completas e independientemente probadas.

---

## Phase 7: Polish & Cross-Cutting

- [X] T031 Regresión completa de pruebas negativas PN-01 a PN-11 y
      cross-tenant existentes (SC-005) -- confirmar que `aerohub_compliance`
      y el middleware de licencia no rompen nada
- [X] T032 `ruff check .`, `mypy .`, `bandit -r services/compliance
      services/tenancy services/gateway`, `lint-imports` en verde,
      corriendo dentro del contenedor del gateway (Docker)
- [X] T033 Ejecutar los 4 escenarios de [quickstart.md](./quickstart.md)
      completos contra MonetDB real en Docker
- [X] T034 Actualizar `CLAUDE.md`: fila S1.7 en "Estado del plan" con el
      hash del commit, una vez cerrado

---

## Dependencies & Execution Order

### Fases

- **Setup (Fase 1)**: sin dependencias
- **Foundational (Fase 2)**: depende de Setup -- BLOQUEA todas las
  historias
- **US1 (Fase 3, P1)**: depende de Foundational -- es el MVP junto con US2
- **US2 (Fase 4, P1)**: depende de Foundational -- independiente de US1
  (módulos distintos: gateway vs. compliance), pero ambas P1 forman el
  MVP real del sprint (DoD explícito exige las dos compuertas)
- **US3 (Fase 5, P2)**: depende de Foundational -- reutiliza el mismo
  módulo `aerohub_compliance` que US2 (mismo `comandos.py`), conviene
  secuenciar después de US2 aunque no dependa funcionalmente
- **US4 (Fase 6, P3)**: depende de Foundational -- completamente
  independiente (módulo `aerohub_tenancy`, no toca `aerohub_compliance`
  ni el middleware), puede desarrollarse en paralelo a cualquier otra
  historia
- **Polish (Fase 7)**: depende de todas las historias incluidas

### Oportunidades de paralelismo

- US1 (gateway) y US4 (tenancy) son completamente independientes entre sí
  y de US2/US3 (compliance) -- tres desarrolladores podrían tomar
  US1+US4+US2/US3 en paralelo tras Foundational
- Dentro de Foundational: T005-T007 en paralelo
- Dentro de cada historia: dominio [P] e infraestructura [P] en paralelo;
  `application/`/`api/router.py`/montaje en Gateway son secuenciales

---

## Implementation Strategy

### MVP primero (US1 + US2)

1. Fase 1: Setup
2. Fase 2: Foundational (crítico)
3. Fase 3: US1 -- licenciamiento (PN-09)
4. Fase 4: US2 -- post-mortem (SC-002)
5. **Validar**: Escenario 1 y 2 de `quickstart.md`
6. Esto cubre las DOS compuertas de pruebas que el DoD del sprint nombra
   explícitamente -- entregable mínimo con valor real

### Entrega incremental

1. Setup + Foundational -> esquema `compliance` + catálogo `modulo` listos
2. US1 -> licenciamiento activo (MVP parcial)
3. US2 -> ciclo de post-mortem completo (MVP completo del DoD)
4. US3 -> resto de `compliance` append-only
5. US4 -> rotación de API Keys, en paralelo a cualquier otra fase
6. Polish -> regresión, calidad, cierre de sprint

---

## Notes

- La excepción de mutabilidad de `post_mortem` (ADR-009) se verifica en
  T019 (código) y T016 (prueba de integración que confirma que
  `role_support` NO puede mutar) -- dos capas, no solo documentación.
- PN-04 reforzada (US3) es la única historia de este sprint verificada
  por análisis ESTÁTICO en vez de una petición HTTP -- "ausencia de
  método" no se puede probar invocando algo que no existe.
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes.
