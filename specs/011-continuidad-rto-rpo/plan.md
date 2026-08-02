# Implementation Plan: Continuidad operacional (RTO/RPO)

**Branch**: `main` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/011-continuidad-rto-rpo/spec.md`

## Summary

Construye los tres componentes de ADR-018 que todavía no existen (C2
snapshot programado + catálogo verificado, C3 réplica caliente con
*shipper* idempotente y métrica de atraso, C4 conmutación de un único
punto + prueba de restauración semanal automatizada) sobre el componente
que ya existe desde S0.2 (C1, `continuidad.journal_mutacion`), al que este
sprint le agrega retención con purga automática. El mecanismo completo se
pone a medir; RNF-R01 **no se cierra** en este sprint (research.md
Decisión 1) -- se reporta como riesgo abierto con mecanismo y métrica,
exactamente como exige ADR-018 y el SRS §2.7/§5.2/§11.

## Technical Context

**Language/Version**: Python 3.12 (scripts y paquete nuevo), SQL DDL de
MonetDB (esquema `continuidad`, ampliado).

**Primary Dependencies**: `pymonetdb` directo (sin pasar por
`aerohub_repository`, research.md Decisión 2), `prometheus_client` (métrica
de atraso de réplica y de la última prueba de restauración, mismo patrón
que S1.3/S1.8), un cliente S3-compatible (`boto3`, dependencia nueva) para
subir snapshots/volcados a MinIO -- ya desplegado desde S0.1, sin tocar su
configuración.

**Storage**: MonetDB primario (`monetdb`) y standby (`monetdb-standby`,
ambos ya declarados en `infra/docker-compose.yml` desde S0.1, sin uso real
hasta este sprint) + un tercer contenedor MonetDB nuevo dedicado
exclusivamente a la prueba de restauración semanal (research.md Decisión
5). Esquema `continuidad` ampliado con dos tablas nuevas
(`snapshot_base`, `shipper_checkpoint`, `prueba_restauracion`) sobre la
tabla ya existente `journal_mutacion`. MinIO (ya desplegado) aloja los
artefactos de snapshot/volcado.

**Testing**: `pytest` unit (cálculo puro de checksum, decisión de
idempotencia del *shipper*, cálculo de atraso y de RTO/RPO observados) +
integración contra MonetDB primario + standby + contenedor de prueba de
restauración, los tres reales en Docker (Principio III de la
constitución) -- incluida una restauración de verdad, no solo simulada,
del snapshot más reciente contra el contenedor dedicado.

**Target Platform**: Docker Compose -- un contenedor nuevo de proceso
continuo (`continuidad-agente`) que corre los tres ciclos (snapshot
programado, *shipper*, prueba de restauración semanal) y expone
`/metrics`; un contenedor nuevo `monetdb-restore-test` dedicado a la
prueba de restauración; un volumen compartido nuevo entre `monetdb` y
`continuidad-agente` para el archivo que produce `sys.hot_snapshot()`.

**Performance Goals**: atraso de réplica < 120 s en operación normal
(alerta al mismo umbral, ADR-018); conmutación completa en < 3 min;
sobrecoste de latencia del journal sin degradar de forma perceptible
RNF-P01 (ya medido en S1.2/S1.4).

**Constraints**: RTO < 15 min, RPO ≤ 5 min (RNF-R01) -- este sprint
construye el mecanismo y lo pone a medir; el cierre formal de RNF-R01
exige 4 semanas consecutivas en verde + 1 *game day* en la Fase 4 (S4.2),
fuera de alcance de este sprint (spec.md, Assumptions).

**Scale/Scope**: 1 esquema ampliado (`continuidad`: 2 tablas nuevas +
retención sobre la existente), 1 paquete de plataforma nuevo
(`aerohub_continuidad`), 4 scripts de `tools/`, 1 contenedor de proceso
continuo nuevo + 1 contenedor de prueba de restauración nuevo, 1 volumen
compartido nuevo, 1 runbook de conmutación.

## Constitution Check

*GATE: Debe cumplirse antes de Fase 0. Re-evaluado después de Fase 1.*

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE. Las
  tres tablas nuevas de `continuidad` son de plataforma, sin `tenant_id`
  -- alcance `'interno'`, igual que `journal_mutacion`/
  `compliance.log_auditoria`. Ningún dato de tenant se expone por una vía
  nueva; el *shipper* replica el journal ya existente tal cual, sin
  interpretarlo por tenant.
- **Principio II (Arquitectura Modular por Capas e Independencia de
  Módulos)**: DESVIACIÓN JUSTIFICADA, documentada en research.md Decisión
  2 -- `aerohub_continuidad` NO es un módulo de negocio (no expone HTTP, no
  tiene actor de tenant) y no sigue las 4 capas de ADR-017 §5.4; es
  tooling de plataforma de la misma familia que `packages/repository`
  mismo (que tampoco las sigue) y que `db/migrations/apply.py`/
  `db/seeds/generate.py` (que ya usan `pymonetdb` directo como excepción
  documentada de arranque/DBA). Se le da su propio contrato de
  import-linter, más simple: `domain/` puro sin framework/driver, el resto
  puede usar `pymonetdb` porque son operaciones de administración del
  motor (snapshot, replay genérico cross-schema, conexión al standby) que
  el modelo guardado de `aerohub_repository` no expresa ni pretende
  cubrir.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE --
  primario, standby y contenedor de restauración reales en Docker;
  atomicidad, idempotencia y una restauración real medida, no solo
  simulada matemáticamente.
- **Principio IV (Calidad Continua en Verde)**: aplica sin excepción.
- **Principio V (Aprobación Explícita Antes de Acciones Irreversibles)**:
  aplica con énfasis adicional -- este sprint introduce contenedores y un
  volumen nuevos en `infra/docker-compose.yml` y ejecuta operaciones DBA
  reales (`sys.hot_snapshot()`, restauración) contra las instancias de
  MonetDB del entorno de desarrollo. Cualquier operación que pudiera
  afectar al primario en uso se prueba primero contra el standby o el
  contenedor de restauración, nunca directamente contra el primario sin
  antes confirmarlo explícitamente.
- **Requisitos Tecnológicos y de Infraestructura**: CUMPLE -- MonetDB
  standby y MinIO ya están declarados/desplegados desde S0.1; este sprint
  los pone a trabajar de verdad por primera vez, sin cambiar su
  configuración base.

Sin violaciones no justificadas -- la única desviación (Principio II) se
documenta en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-continuidad-rto-rpo/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── snapshot-catalogo.md
    ├── shipper-metrica.md
    └── conmutacion-runbook.md
```

### Source Code (repository root)

```text
db/ddl/monetdb/15_continuidad_snapshot.sql   # snapshot_base, shipper_checkpoint, prueba_restauracion
db/ddl/monetdb/99_grants_continuidad_ext.sql # grants de las 3 tablas nuevas

packages/continuidad/aerohub_continuidad/
├── domain/
│   ├── checksum.py           # calculo/verificacion de checksum de artefacto
│   ├── replicacion.py        # decision de idempotencia (lsn ya aplicado o no)
│   └── recuperacion.py       # calculo de RTO/RPO observados a partir de marcas de tiempo
├── operaciones/              # NO sigue ADR-017 (ver Constitution Check) -- pymonetdb directo
│   ├── snapshot.py           # invoca sys.hot_snapshot() / volcado logico, sube a MinIO, catalogo
│   ├── shipper.py            # drena journal_mutacion -> aplica en standby -> checkpoint
│   └── restauracion.py       # restaura ultimo snapshot en el contenedor de prueba, mide RTO/RPO
└── metricas.py                # prometheus_client: lag, edad de snapshot, RTO/RPO de la ultima prueba

tools/
├── continuidad_agente.py      # entrypoint del contenedor: 3 ciclos concurrentes + /metrics
└── continuidad_conmutar.py    # preflight de conmutacion (verifica lag, imprime pasos del runbook)

infra/docker-compose.yml       # + monetdb-restore-test, + continuidad-agente, + volumen snapshotstage
infra/prometheus/prometheus.yml # + scrape job continuidad-agente

docs/runbooks/continuidad_failover.md  # procedimiento de conmutacion paso a paso

tests/unit/continuidad/
tests/integration/test_continuidad_snapshot.py
tests/integration/test_continuidad_shipper.py
tests/integration/test_continuidad_restauracion.py
tests/negative/test_pn04_continuidad_purga_no_adelanta_al_shipper.py
```

**Structure Decision**: `aerohub_continuidad` vive en `packages/`, no en
`services/`, porque no es un módulo de negocio (research.md Decisión 2).
Los scripts de `tools/` son entrypoints delgados, mismo patrón que
`tools/verificar_error_budget.py` (S1.8): parsean argumentos/config y
llaman al paquete, sin lógica propia. El contenedor `continuidad-agente`
es el único proceso de larga duración nuevo; snapshot y *shipper* corren
como tareas asíncronas concurrentes dentro de él (mismo patrón que el
monitor de señal FIDS en `services/gateway/main.py`), no como DAGs de
Airflow -- Airflow se reserva para la Fase 2 (ETL/analítica, Plan §9),
introducirlo aquí adelantaría una pieza de infraestructura fuera del
alcance y el orden declarados por el propio plan (research.md Decisión
4).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `aerohub_continuidad` no sigue las 4 capas de ADR-017 §5.4 (Principio II) | Es tooling de administración de plataforma (snapshot, replay cross-schema genérico, conexión a un segundo motor) -- no tiene actor de tenant, no expone HTTP, y el modelo guardado de `aerohub_repository` (Table() tipado por módulo, guardián de tenant) no puede expresar un *replay* genérico de cualquier `(esquema, tabla, operación, payload)` sin conocer de antemano el esquema de cada módulo de negocio. | Forzar las 4 capas obligaría a `aerohub_continuidad` a importar `infrastructure/` de TODOS los módulos de negocio para poder reconstruir sus `Table()` y reproducir sus mutaciones -- viola directamente la independencia de módulos que el propio Principio II protege, un costo mayor que la excepción documentada. |
