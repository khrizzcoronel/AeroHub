# ADR-018 — Continuidad operacional de MonetDB: journal transaccional, snapshot programado y standby caliente

| Campo | Contenido |
|:---|:---|
| **Estado** | Aceptado — **cierre de RNF-R01 condicionado a demostración sostenida** |
| **Fecha** | 2026-07-30 |
| **Decide sobre** | Mecanismo técnico de RTO/RPO ante la ausencia de PITR nativo |
| **Deriva de** | AEROHUB-SRS-001 v2.0 §2.7, §5.2 (RNF-R01), §11 · Análisis v6.0 Acción 1b · ADR-013 |
| **Requisitos relacionados** | RNF-R01, RF-O09, RNF-S04, OP7 |

---

## Contexto

ADR-013 adopta MonetDB como motor operacional. La consecuencia declarada es la pérdida de tres capacidades: RLS (resuelta por ADR-014 y ADR-019), triggers nativos (resuelta trasladando la auditoría a la capa de repositorio) y **PITR / replicación streaming**, que permanecía sin resolver.

La SRS declara el problema en tres lugares y en los tres se niega a darlo por cerrado:

- §2.7: *"riesgo abierto asumido por diseño… no puede darse por satisfecho hasta que la prueba de restauración semanal lo demuestre de forma sostenida"*.
- §5.2, RNF-R01: RTO < 15 min y RPO ≤ 5 min, con estado **"no se documenta como control cerrado"**.
- §11: *"ningún artefacto de diseño puede asumir RTO/RPO cumplidos por defecto"*.

El plan de acción (Acción 1b) prescribe "respaldo lógico programado + replicación de almacenamiento". Ese enunciado, por sí solo, **no alcanza el RPO**: un respaldo lógico programado cada N horas deja una ventana de pérdida de N horas, y la replicación de almacenamiento a nivel de bloque no garantiza consistencia transaccional en el punto de conmutación. El problema real no es la ausencia de respaldos, es la **ausencia de un flujo continuo de cambios con orden garantizado**.

---

## Decisión

Se construye un mecanismo de continuidad de **cuatro componentes**, aprovechando una propiedad que la propia arquitectura ya garantiza: **toda mutación pasa por un único punto de código** (la capa de repositorio, P1/ADR-014). Ese cuello de botella, que existe por razones de seguridad, se convierte aquí en el punto de captura de cambios que el motor no ofrece.

### C1 — Journal de mutaciones transaccional (patrón *outbox*)

Nuevo esquema `continuidad` en MonetDB:

```
continuidad.journal_mutacion
  lsn              BIGINT       NO   PK — secuencia monótona, orden total de aplicación
  esquema          VARCHAR(30)  NO
  tabla            VARCHAR(50)  NO
  operacion        VARCHAR(10)  NO   CHK IN ('INSERT','UPDATE','DELETE_LOGICO','DDL')
  clave_primaria   JSON         NO
  payload          JSON         NO   estado resultante de la fila
  tenant_id        BIGINT       SÍ
  ocurrido_en      TIMESTAMPTZ  NO
  checksum_sha256  CHAR(64)     NO   integridad de la entrada
  IDX (lsn)
```

La entrada del journal se escribe **en la misma transacción** que la mutación de negocio. La atomicidad la garantiza el motor: o se confirman ambas o ninguna. No existe ventana de doble escritura no atómica ni posibilidad de que una mutación quede sin registrar.

**Por qué un journal propio y no `compliance.log_auditoria`,** que ya almacena `valores_anteriores`/`valores_nuevos`: son artefactos con responsabilidades y ciclos de vida distintos. `log_auditoria` es evidencia de cumplimiento bajo control de D5, append-only, con política de archivado hacia almacenamiento frío (SDD-001 M-01) que destruiría el journal; carece además de orden total (`lsn`). Acoplar la continuidad a la auditoría haría que una decisión de retención de cumplimiento rompiera la recuperación ante desastres. Se separan deliberadamente: **retención del journal 48 h**, retención de la auditoría según política de compliance.

### C2 — Snapshot base programado

- `sys.hot_snapshot()` cada **6 horas** hacia almacenamiento de objetos replicado (MinIO/S3-compatible).
- Volcado lógico completo diario como respaldo de último recurso e independiente del formato interno del motor.
- Verificación de integridad por checksum de cada artefacto; catálogo de snapshots con su `lsn` de corte.

El snapshot fija el punto de partida; el journal aporta el delta continuo. **RPO = lag del journal, no periodicidad del snapshot.**

### C3 — Standby caliente con *shipper*

- Segunda instancia MonetDB, misma versión y misma DDL, restaurada desde el último snapshot.
- Proceso `shipper` que drena `journal_mutacion` por `lsn` creciente y lo aplica sobre el standby, registrando el último `lsn` aplicado. La reaplicación de un `lsn` ya procesado es no-op → **idempotente ante reintento**.
- El journal se replica además a almacenamiento de objetos: si el primario se pierde por completo, el journal sobrevive fuera de él.
- Métrica Prometheus `aerohub_standby_lag_seconds` publicada continuamente. **Alerta a los 120 s** — la mitad del presupuesto de RPO, para que la degradación sea visible antes de ser incumplimiento.

### C4 — Conmutación y verificación

- *Health check* del primario; ante fallo confirmado, drenaje del journal pendiente y conmutación mediante **cambio de DSN en la capa de repositorio**. Que exista un único emisor de SQL convierte el failover en un cambio de configuración en un solo lugar, no en una coordinación entre N servicios.
- Presupuesto de RTO: detección ≤ 60 s · drenaje ≤ 2 min · conmutación ≤ 1 min · verificación de consistencia ≤ 5 min → **≈ 9 min**, con holgura frente a los 15 min exigidos.
- **Prueba de restauración semanal automatizada** (RF-O09) y **game day mensual** con failover real sobre datos sintéticos, ambos publicando `rpo_observado_segundos` y `rto_observado_segundos`.

---

## Alternativas consideradas

| Alternativa | Motivo de descarte |
|:---|:---|
| Solo respaldo lógico programado (enunciado literal de la Acción 1b) | No alcanza RPO ≤ 5 min: la ventana de pérdida es la periodicidad del volcado. Se conserva como componente C2, no como solución. |
| Replicación de almacenamiento a nivel de bloque | No garantiza consistencia transaccional en el punto de conmutación; puede replicar un estado intermedio de escritura. Útil como defensa adicional del volumen, insuficiente como mecanismo de RPO. |
| Doble escritura desde la aplicación (primario y standby en paralelo) | Sin transacción distribuida, una escritura puede confirmarse y la otra fallar, produciendo divergencia silenciosa — exactamente el modo de fallo que se quiere evitar. El outbox transaccional lo elimina por construcción. |
| Revertir ADR-013 y volver a un motor con PITR nativo | Es una decisión de plataforma superior a este ADR; se mantiene como **plan de contingencia** si la demostración sostenida falla (ver Consecuencias). |

---

## Consecuencias

**Positivas**

- El RPO deja de depender de una periodicidad y pasa a ser una **métrica observable en tiempo real** (`aerohub_standby_lag_seconds`), con alerta antes del incumplimiento.
- La atomicidad mutación ↔ journal la garantiza el motor, no la disciplina del programador.
- El failover se ejecuta en un único punto de configuración, consecuencia directa de P1.
- El journal habilita, sin trabajo adicional, la reconstrucción forense de un intervalo y el *replay* selectivo por tenant.

**Negativas y costes asumidos**

- **Sobrecoste de latencia por escritura:** cada mutación paga una inserción adicional en la misma transacción. Debe medirse en S4.2 contra RNF-P01 (< 1 s de propagación de estado); si el margen se estrecha, se evalúa serializar el `payload` de forma más compacta antes que relajar el control.
- **El journal solo captura lo que pasa por la capa de repositorio.** Una migración DDL o una carga masiva ejecutada por fuera quedaría sin replicar. Regla derivada, verificada en CI: **toda migración se aplica a primario y standby por el mismo pipeline versionado**, y toda carga masiva se enruta por el repositorio o se acompaña de un nuevo snapshot base.
- **No es PITR real.** No permite restaurar a un instante arbitrario más allá de la retención del journal (48 h) combinada con los snapshots. Se documenta como limitación aceptada; ningún requisito vigente exige recuperación a un punto arbitrario del pasado remoto.
- **Mecanismo propio, no probado en batalla.** Un motor con PITR nativo ofrece una implementación madurada por años de uso. Este mecanismo es específico del proyecto y su fiabilidad depende de sus propias pruebas.

## Condición de cierre de RNF-R01

Este ADR **no cierra RNF-R01 por sí mismo**. La SRS lo prohíbe expresamente. RNF-R01 se declara cerrado únicamente cuando:

1. La prueba de restauración semanal automatizada reporte **4 semanas consecutivas** con RTO < 15 min y RPO ≤ 5 min.
2. Al menos un **game day con failover real** haya cumplido ambos objetivos.
3. `aerohub_standby_lag_seconds` no haya superado los 120 s en el periodo de observación.

Hasta ese momento, RNF-R01 se reporta como **riesgo abierto en cada cierre de fase**, ahora con mecanismo asignado y métrica de avance, en lugar de sin solución. Si al término de la Fase 4 la demostración no se sostiene, se activa el plan de contingencia: **ADR de revisión de ADR-013**, escalado a decisión de plataforma y no absorbido por el equipo de desarrollo.
