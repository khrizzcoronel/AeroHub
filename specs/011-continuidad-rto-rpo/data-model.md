# Data Model: Continuidad operacional (RTO/RPO) (S1.9)

Amplía el esquema `continuidad` (ADR-018) ya existente desde S0.2
(`continuidad.journal_mutacion`). Las tres tablas nuevas son alcance G1
**interno** (plataforma, sin `tenant_id`), mismo tratamiento que
`journal_mutacion`/`compliance.log_auditoria` (research.md de S1.9,
Decisión 2 y el propio ADR-018).

## `continuidad.snapshot_base`

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `tipo` | VARCHAR(20) | NO | CHK IN ('programado','volcado_diario') |
| `lsn_corte` | BIGINT | NO | último `lsn` de `journal_mutacion` incluido en el snapshot |
| `generado_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `ruta_artefacto` | VARCHAR(500) | NO | ubicación en MinIO/S3 |
| `hash_artefacto` | CHAR(64) | NO | checksum SHA-256 |
| `estado` | VARCHAR(20) | NO | CHK IN ('generado','verificado','corrupto') |
| `verificado_en` | TIMESTAMPTZ | SÍ | |

**Transición de estado**: `generado` → (`verificado` \| `corrupto`), sin
retorno. Un snapshot `corrupto` nunca se usa como origen de restauración
(FR-004) -- se filtra en la consulta que resuelve "el último snapshot
verificado".

## `continuidad.shipper_checkpoint`

Una única fila lógica por réplica de respaldo (hoy, una sola: el
standby). Se actualiza (`UPDATE`, no `INSERT`) en cada ciclo exitoso del
*shipper* -- única tabla mutable de este esquema además de la excepción ya
existente para `journal_mutacion` (purga, FR-015/FR-016).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `standby_nombre` | VARCHAR(50) | NO | UQ -- identifica la réplica (hoy: `"monetdb-standby"`) |
| `ultimo_lsn_aplicado` | BIGINT | NO | DEFAULT 0 |
| `actualizado_en` | TIMESTAMPTZ | NO | DEFAULT now() |

El atraso observado (`aerohub_standby_lag_seconds`, contracts/shipper-metrica.md)
se deriva en tiempo de consulta comparando `ocurrido_en` de la entrada de
`journal_mutacion` con `lsn = ultimo_lsn_aplicado + 1` (la más antigua
pendiente) contra el reloj actual -- no se persiste como columna, para no
duplicar una fuente de verdad derivable (mismo criterio que S1.8,
research.md Decisión 1 de esa feature, aplicado aquí a la métrica de
atraso).

## `continuidad.prueba_restauracion`

Append-only -- cada fila es una ejecución histórica de la prueba semanal,
nunca se actualiza ni se borra (evidencia acumulada, spec.md SC-004/US4).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `snapshot_id` | BIGINT | NO | FK → `snapshot_base.id` -- el snapshot restaurado en esta prueba |
| `ejecutado_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `rto_observado_segundos` | INTEGER | NO | tiempo real de recuperación de esta corrida |
| `rpo_observado_segundos` | INTEGER | NO | ventana real de pérdida de datos de esta corrida |
| `resultado` | VARCHAR(20) | NO | CHK IN ('exitosa','fallida') |
| `detalle` | VARCHAR(500) | SÍ | motivo si `resultado = 'fallida'` |

## `continuidad.journal_mutacion` (existente desde S0.2 -- sin cambio de esquema)

Este sprint no le agrega columnas -- le agrega la **regla de purga**
(research.md Decisión 7): una entrada se elimina únicamente si su
antigüedad supera 48 h Y su `lsn` ya fue confirmado aplicado por TODAS las
réplicas registradas en `shipper_checkpoint` (hoy, una sola). Sin esa
segunda condición, la retención por antigüedad podría destruir una
entrada que el *shipper* todavía no replicó (spec.md, Edge Cases).
