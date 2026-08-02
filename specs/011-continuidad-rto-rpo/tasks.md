# Tasks: Continuidad operacional (RTO/RPO)

**Input**: Design documents from `specs/011-continuidad-rto-rpo/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: incluidas -- Principio III/IV de la constitución.

**Organización**: por historia de usuario (US1-US5 de `spec.md`), en
orden de prioridad (P1, P1, P1, P2, P3).

## Phase 1: Setup

- [X] T001 Crear `packages/continuidad/pyproject.toml` (paquete
      `aerohub_continuidad`; dependencias: `pymonetdb`, `boto3`,
      `prometheus-client`, `aerohub-kernel`, `aerohub-repository` --
      necesita `aerohub-repository` solo para la LECTURA guardada del
      journal, research.md Decisión 3) y registrarlo en
      `tool.uv.workspace.members` del `pyproject.toml` raíz
- [X] T002 [P] Agregar `aerohub_continuidad` a `.importlinter` con su
      propio contrato simplificado (regla única: `domain/` no importa
      `pymonetdb`/`boto3`/`prometheus_client` -- sin la exigencia de las 4
      capas de un módulo de negocio, research.md Decisión 2/plan.md
      Complexity Tracking)
- [X] T003 [P] Scaffold de `packages/continuidad/aerohub_continuidad/`:
      `__init__.py`, `domain/__init__.py`, `operaciones/__init__.py`,
      `metricas.py` (vacío)
- [X] T004 [P] Scaffold de `tools/continuidad_agente.py` y
      `tools/continuidad_conmutar.py` (estructura base con
      `argparse`, sin lógica todavía)

---

## Phase 2: Foundational (bloqueante para US1-US5)

**Propósito**: esquema `continuidad` ampliado + contenedores nuevos --
ninguna historia puede implementarse ni verificarse sin esto.

**⚠️ CRÍTICO**: ninguna tarea de US1-US5 empieza antes de cerrar esta fase.

- [X] T005 `db/ddl/monetdb/15_continuidad_snapshot.sql`: las 3 tablas
      nuevas de [data-model.md](./data-model.md)
      (`snapshot_base`, `shipper_checkpoint`, `prueba_restauracion`) con
      sus CHECK/FK, transcritas al primario, al standby y al contenedor
      de restauración (mismo DDL, research.md Decisión 5: los tres
      motores comparten esquema)
- [X] T006 `db/ddl/monetdb/99_grants_continuidad_ext.sql`: grants sobre
      las 3 tablas nuevas -- `role_platform_admin` con INSERT/UPDATE/SELECT
      (único escritor, el propio `continuidad-agente` corre bajo este
      rol vía `alcance_global`); `role_sre`/`role_data_engineer`/
      `role_elt_reader` con SELECT (diagnóstico de plataforma, mismo
      criterio que `94_grants_continuidad.sql` sobre `journal_mutacion`)
- [X] T007 [P] Registrar alcance G1 `'interno'` de las 3 tablas nuevas en
      `packages/repository/alcances.py` (registro centralizado, mismo
      archivo que ya registra `journal_mutacion`/`log_auditoria` --
      tablas de infraestructura transversal, no propiedad de un módulo
      de negocio)
- [X] T008 [P] `infra/docker-compose.yml`: agregar volumen nuevo
      `snapshotstage`, montado en `monetdb` y en `continuidad-agente`
      (research.md Decisión 6 -- traspaso del archivo de
      `sys.hot_snapshot()`)
- [X] T009 [P] `infra/docker-compose.yml`: agregar servicio
      `monetdb-restore-test` (mismo patrón que `monetdb-standby`,
      research.md Decisión 5)
- [X] T010 `infra/docker-compose.yml`: agregar servicio
      `continuidad-agente` (Dockerfile propio en
      `packages/continuidad/Dockerfile`, mismo patrón que
      `services/gateway/Dockerfile`; variables de entorno para DSN del
      primario, DSN del standby, DSN de `monetdb-restore-test`, endpoint
      de MinIO)
- [X] T011 [P] `infra/prometheus/prometheus.yml`: agregar job de scrape
      `continuidad_agente`
- [X] T012 Verificación empírica: levantar `monetdb`, `monetdb-standby`,
      `monetdb-restore-test` en Docker, aplicar el DDL de T005 contra los
      tres, confirmar las 3 tablas creadas en cada uno con sus
      constraints (Principio III)

**Checkpoint**: esquema y contenedores listos -- US1-US5 pueden empezar.

---

## Phase 3: User Story 1 - Punto de partida recuperable siempre disponible (Priority: P1) 🎯 MVP (parte 1/2)

**Goal**: un snapshot verificado y catalogado existe siempre, con una
antigüedad máxima de 6 horas, sin intervención manual.

**Independent Test**: forzar un ciclo de snapshot y verificar una fila
nueva en `continuidad.snapshot_base` con `estado='verificado'`,
`lsn_corte` y `hash_artefacto` no nulos, y el artefacto presente en MinIO
-- Escenario 1 de `quickstart.md`.

### Tests para US1

- [X] T013 [P] [US1] Test unitario: cálculo y verificación de checksum
      (coincide/no coincide) en `tests/unit/continuidad/test_checksum.py`
- [X] T014 [P] [US1] Test de integración: ciclo de snapshot forzado
      contra MonetDB + MinIO reales, catálogo resultante con
      `estado='verificado'`, y un snapshot con artefacto corrupto queda
      `estado='corrupto'` (fixture), en
      `tests/integration/test_continuidad_snapshot.py`

### Implementación de US1

- [X] T015 [P] [US1] `packages/continuidad/aerohub_continuidad/domain/checksum.py`:
      `calcular_checksum_sha256(ruta)`, `checksums_coinciden(a, b)` --
      puro, sin I/O de red (recibe bytes/ruta ya leídos)
- [X] T016 [US1] `packages/continuidad/aerohub_continuidad/operaciones/snapshot.py`:
      invoca `sys.hot_snapshot()` (tipo `'programado'`) o el volcado
      lógico (tipo `'volcado_diario'`) sobre el primario vía `pymonetdb`
      directo (research.md Decisión 2), sube el artefacto a MinIO
      (`boto3`), inserta y luego actualiza el catálogo en
      `continuidad.snapshot_base` vía `aerohub_repository.sesion()` bajo
      `alcance_global(motivo="ciclo_snapshot", rol="role_platform_admin")`
      (depende de T015)
- [X] T017 [US1] `tools/continuidad_agente.py` (parcial): ciclo `asyncio`
      del snapshot programado (cada 6 h) + volcado diario, flag
      `--forzar-snapshot {programado|volcado_diario}` para verificación
      manual (contracts/snapshot-catalogo.md)
- [X] T018 [US1] `packages/continuidad/aerohub_continuidad/metricas.py`
      (parcial): `aerohub_snapshot_edad_segundos` (Gauge,
      contracts/shipper-metrica.md)

**Checkpoint**: US1 funcional -- SC-001 verificable.

---

## Phase 4: User Story 2 - Réplica caliente con atraso siempre visible (Priority: P1) 🎯 MVP (parte 2/2)

**Goal**: la réplica de respaldo recibe cada cambio del primario en
orden, de forma idempotente, con su atraso publicado de forma continua.

**Independent Test**: aplicar una mutación sintética al primario,
verificar que aparece en el standby tras el siguiente ciclo del
*shipper*, que reaplicar el mismo `lsn` no produce efecto adicional, y
que `aerohub_standby_lag_seconds` refleja el atraso real -- Escenario 2
de `quickstart.md`. Depende de Foundational, no de US1 (para pruebas
aisladas el standby puede partir vacío con el mismo DDL aplicado,
spec.md Independent Test de US2); en producción SÍ depende de un
snapshot de US1 para sembrar una réplica nueva desde cero.

### Tests para US2

- [X] T019 [P] [US2] Test unitario: decisión de aplicar o descartar una
      entrada según su `lsn` frente al último aplicado (idempotencia
      pura) en `tests/unit/continuidad/test_replicacion.py`
- [X] T020 [P] [US2] Test de integración: mutación real en el primario
      se replica al standby en el siguiente ciclo, reintentar el mismo
      `lsn` no duplica ni falla, en
      `tests/integration/test_continuidad_shipper.py`

### Implementación de US2

- [X] T021 [P] [US2] `packages/continuidad/aerohub_continuidad/domain/replicacion.py`:
      `debe_aplicar(lsn, ultimo_lsn_aplicado) -> bool` -- puro
- [X] T022 [US2] `packages/continuidad/aerohub_continuidad/operaciones/shipper.py`:
      lee `continuidad.journal_mutacion` con `lsn > ultimo_lsn_aplicado`
      del primario vía `aerohub_repository.sesion()` bajo
      `alcance_global(motivo="shipper_continuidad", rol="role_platform_admin")`
      (research.md Decisión 3); aplica cada entrada sobre el standby vía
      `pymonetdb` directo, construyendo el `INSERT`/`UPDATE` genérico
      desde `esquema`/`tabla`/`clave_primaria`/`payload`; actualiza
      `continuidad.shipper_checkpoint` (depende de T021)
- [X] T023 [US2] `tools/continuidad_agente.py` (parcial): ciclo continuo
      del *shipper* (intervalo corto, p. ej. cada pocos segundos)
- [X] T024 [US2] `packages/continuidad/aerohub_continuidad/metricas.py`
      (parcial): `aerohub_standby_lag_seconds` (Gauge,
      contracts/shipper-metrica.md; data-model.md: derivado en tiempo de
      consulta, no persistido)
- [X] T025 [P] [US2] `infra/prometheus/alertas.yml`: regla de alerta
      `aerohub_standby_lag_seconds > 120` sostenida 30 s

**Checkpoint**: US2 funcional -- SC-002/SC-005/SC-006 verificables.
US1+US2 = MVP del sprint (cubre el núcleo de C2/C3 de ADR-018).

---

## Phase 5: User Story 3 - Conmutación desde un único punto (Priority: P2)

**Goal**: un responsable de plataforma puede redirigir toda la
aplicación hacia el standby cambiando un único punto de configuración,
con un procedimiento documentado y una herramienta de *preflight*.

**Independent Test**: simular la caída del primario, ejecutar el
*preflight*, verificar que reporta el atraso pendiente y el DSN sugerido
(o rechaza con código de salida `1` si el atraso supera el umbral) --
Escenario 3 de `quickstart.md`. Depende de US2 (necesita
`shipper_checkpoint` poblado).

### Tests para US3

- [X] T026 [US3] Test de integración: los 3 casos del *preflight*
      (atraso 0 -> código 0 con DSN sugerido; atraso bajo el umbral ->
      código 0 con advertencia; atraso sobre el umbral -> código 1, sin
      DSN sugerido), en
      `tests/integration/test_continuidad_conmutacion.py`

### Implementación de US3

- [X] T027 [US3] `tools/continuidad_conmutar.py`: lógica completa --
      consulta `shipper_checkpoint` y el `lsn` máximo de
      `journal_mutacion`, decide código de salida según
      [contracts/conmutacion-runbook.md](./contracts/conmutacion-runbook.md)
      (depende de T022 para el esquema de `shipper_checkpoint`)
- [X] T028 [US3] `docs/runbooks/continuidad_failover.md`: procedimiento
      completo -- confirmación de fallo real, ejecución del *preflight*,
      cambio de `AEROHUB_DB_DSN` y reinicio del `gateway`, verificación
      post-conmutación, y qué hacer si el primario original vuelve
      (spec.md, Edge Cases)

**Checkpoint**: US3 funcional -- SC-003 verificado en escenario simulado.

---

## Phase 6: User Story 4 - Evidencia semanal automática de recuperación (Priority: P2)

**Goal**: cada semana, sin intervención manual, se restaura el último
snapshot verificado en un contenedor dedicado y se mide/publica el RTO y
el RPO observados de esa corrida.

**Independent Test**: forzar una ejecución de la prueba, verificar que
`monetdb-restore-test` queda con los datos del último snapshot
verificado y que aparece una fila nueva en
`continuidad.prueba_restauracion` con ambas métricas y
`resultado='exitosa'` -- Escenario 4 de `quickstart.md`. Depende de US1
(necesita un snapshot verificado que restaurar).

### Tests para US4

- [X] T029 [US4] Test de integración: prueba de restauración forzada
      contra `monetdb-restore-test` real, fila resultante en
      `prueba_restauracion` con `rto_observado_segundos`/
      `rpo_observado_segundos` coherentes y `resultado='exitosa'`; un
      snapshot `'corrupto'` catalogado nunca se elige como origen, en
      `tests/integration/test_continuidad_restauracion.py`

### Implementación de US4

- [X] T030 [P] [US4] `packages/continuidad/aerohub_continuidad/domain/recuperacion.py`:
      `calcular_rto_observado_segundos(inicio, fin)`,
      `calcular_rpo_observado_segundos(lsn_corte_snapshot, ultima_entrada_journal)`
      -- puro
- [X] T031 [US4] `packages/continuidad/aerohub_continuidad/operaciones/restauracion.py`:
      resuelve el último snapshot `'verificado'`
      (contracts/snapshot-catalogo.md), lo restaura en
      `monetdb-restore-test` vía `pymonetdb` directo, mide tiempos,
      inserta la fila resultante en `continuidad.prueba_restauracion`
      (depende de T030)
- [X] T032 [US4] `tools/continuidad_agente.py` (parcial): ciclo semanal +
      flag `--forzar-prueba-restauracion`
- [X] T033 [US4] `packages/continuidad/aerohub_continuidad/metricas.py`
      (parcial): `aerohub_prueba_restauracion_rto_segundos` /
      `_rpo_segundos` (Gauge, última corrida)

**Checkpoint**: US4 funcional -- SC-004 verificado, RF-O09 cubierto.

---

## Phase 7: User Story 5 - El registro de cambios no crece sin límite (Priority: P3)

**Goal**: `continuidad.journal_mutacion` se depura automáticamente pasada
su ventana de retención (48 h), sin arriesgar una entrada que el
*shipper* todavía no aplicó.

**Independent Test**: con entradas sintéticas más antiguas que 48 h,
verificar que se purgan solo las ya confirmadas por
`shipper_checkpoint`, nunca las pendientes -- Escenario 5 de
`quickstart.md`. Depende de US2 (`shipper_checkpoint` debe existir y
poblarse).

### Tests para US5

- [X] T034 [US5] Test de integración: purga elimina entradas antiguas Y
      confirmadas; NO elimina una entrada antigua pero con `lsn` mayor al
      último confirmado, en
      `tests/integration/test_continuidad_purga.py`
- [X] T035 [P] [US5] Test negativo (PN-04 reforzada): análisis estático
      confirma que la función de purga SIEMPRE incluye ambas condiciones
      (antigüedad Y avance del *shipper*) en su cláusula `WHERE`, en
      `tests/negative/test_pn04_continuidad_purga_no_adelanta_al_shipper.py`

### Implementación de US5

- [X] T036 [US5] `packages/continuidad/aerohub_continuidad/operaciones/purga.py`:
      `purgar_journal_confirmado()` -- `DELETE` condicionado a
      `ocurrido_en < ahora - 48h` Y `lsn <= MIN(ultimo_lsn_aplicado)` de
      `shipper_checkpoint` (research.md Decisión 7; depende de T022)
- [X] T037 [US5] `tools/continuidad_agente.py` (parcial): ciclo de purga
      (junto al *shipper* o en su propio intervalo, p. ej. cada hora)

**Checkpoint**: US5 funcional -- FR-015/FR-016 verificados. Las 5
historias completas e independientemente probadas.

---

## Phase 8: Polish & Cross-Cutting

- [X] T038 Regresión completa de pruebas negativas PN-01 a PN-15 y suite
      cruzada existentes -- confirmar que `aerohub_continuidad` y los
      contenedores nuevos no rompen nada
- [X] T039 `ruff check .`, `mypy .`, `bandit -r packages/continuidad tools`,
      `lint-imports` en verde, corriendo dentro del contenedor del
      gateway (Docker); confirmar que
      `.github/workflows/ci.yml` (`bandit -r services packages pipelines ml -ll`)
      ya cubre `packages/continuidad` sin cambios adicionales
- [X] T040 Ejecutar los 5 escenarios de [quickstart.md](./quickstart.md)
      completos contra Docker real (primario + standby + restore-test +
      MinIO + Prometheus)
- [X] T041 Medir el sobrecoste de latencia del journal (comparación con
      RNF-P01 ya medido en S1.2/S1.4) -- documentar el resultado en
      `docs/runbooks/monetdb.md` o `CLAUDE.md`; si el margen se estrecha,
      evaluar serializar el `payload` de forma más compacta (ADR-018,
      nunca relajar el control)
- [X] T042 Actualizar `CLAUDE.md`: fila S1.9 en "Estado del plan" con el
      hash del commit y nota explícita de que RNF-R01 queda como riesgo
      abierto con mecanismo y métrica (no cerrado), una vez cerrado el
      sprint

---

## Dependencies & Execution Order

### Fases

- **Setup (Fase 1)**: sin dependencias
- **Foundational (Fase 2)**: depende de Setup -- BLOQUEA US1-US5
- **US1 (Fase 3, P1)**: depende de Foundational -- MVP junto con US2
- **US2 (Fase 4, P1)**: depende de Foundational (no de US1 para pruebas
  aisladas, spec.md); en producción real depende de un snapshot de US1
  para sembrar una réplica nueva
- **US3 (Fase 5, P2)**: depende de US2 (`shipper_checkpoint`)
- **US4 (Fase 6, P2)**: depende de US1 (necesita un snapshot verificado
  que restaurar)
- **US5 (Fase 7, P3)**: depende de US2 (`shipper_checkpoint` poblado)
- **Polish (Fase 8)**: depende de todas las historias incluidas

### Oportunidades de paralelismo

- Dentro de Foundational: T007-T011 en paralelo (archivos distintos)
- Dentro de cada historia: dominio [P] e infraestructura/operaciones en
  paralelo cuando no comparten archivo; `tools/continuidad_agente.py` es
  compartido entre US1/US2/US4/US5 (cada historia agrega su propio ciclo
  al mismo archivo) -- esas tareas específicas son secuenciales entre sí
- US3 y US4 pueden desarrollarse en paralelo entre sí una vez cerradas
  US1/US2 (archivos distintos: `tools/continuidad_conmutar.py` vs.
  `operaciones/restauracion.py`)

---

## Parallel Example: User Story 1

```bash
# Tests de US1 en paralelo:
Task: "Test de checksum en tests/unit/continuidad/test_checksum.py"
Task: "Test de integracion de snapshot en tests/integration/test_continuidad_snapshot.py"

# Dominio de US1 (sin dependencias):
Task: "domain/checksum.py"
```

---

## Implementation Strategy

### MVP primero (US1 + US2)

1. Fase 1: Setup
2. Fase 2: Foundational (crítica para todas las historias)
3. Fase 3: US1 -- snapshot programado y catálogo verificado (SC-001)
4. Fase 4: US2 -- réplica caliente con atraso visible (SC-002/SC-005/SC-006)
5. **Validar**: Escenario 1 y 2 de `quickstart.md`
6. Cubre el núcleo real de continuidad (C2+C3 de ADR-018) -- entregable
   mínimo con valor real, aunque RNF-R01 siga sin cerrarse

### Entrega incremental

1. Setup + Foundational -> esquema y contenedores listos
2. US1 -> snapshot verificado (parte de C2)
3. US2 -> réplica al día con métrica de atraso (C3, MVP completo del DoD)
4. US3 -> conmutación guiada + runbook (parte de C4)
5. US4 -> prueba de restauración semanal con evidencia (RF-O09, resto de C4)
6. US5 -> purga segura del journal (cierre de C1)
7. Polish -> regresión, calidad, medición de sobrecoste, cierre de sprint

---

## Notes

- Ninguna historia de este sprint declara cerrado RNF-R01 -- eso requiere
  4 semanas consecutivas en verde + 1 *game day* en la Fase 4 (S4.2),
  fuera de alcance (spec.md, Assumptions; research.md Decisión 1).
- La conmutación real de producción NUNCA se ejecuta sin confirmación
  explícita del usuario (Principio V) -- T026-T028 se verifican con el
  primario simulado/pausado, nunca deteniendo una instancia en uso real
  sin avisar primero.
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes.
