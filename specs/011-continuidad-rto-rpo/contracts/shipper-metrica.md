# Contrato: métricas de continuidad (`continuidad-agente`, C3/C4)

Expuestas en `GET /metrics` del propio contenedor `continuidad-agente`
(mismo mecanismo `prometheus_client` que `services/gateway/main.py` desde
S1.3), scrapeadas por un job nuevo en `infra/prometheus/prometheus.yml`.

## `aerohub_standby_lag_seconds` (Gauge)

Atraso actual, en segundos, entre la entrada más antigua de
`continuidad.journal_mutacion` que el *shipper* todavía no aplicó sobre
el standby y el momento presente. `0` si el *shipper* está al día (sin
entradas pendientes).

- **Alerta**: `aerohub_standby_lag_seconds > 120` sostenido por más de 30 s
  (regla nueva en `infra/prometheus/alertas.yml`, mismo archivo que S1.8
  agregó para disponibilidad de AODB/FIDS) -- la mitad del presupuesto de
  RPO (ADR-018), para que la degradación sea visible antes del
  incumplimiento.

## `aerohub_snapshot_edad_segundos` (Gauge)

Antigüedad, en segundos, del snapshot `'verificado'` más reciente en
`continuidad.snapshot_base`. Complementa SC-001 de spec.md (un snapshot
verificado con antigüedad máxima igual al intervalo programado): un valor
sostenido por encima de 6 h (21600 s) indica que el ciclo programado dejó
de producir snapshots verificados, aunque no haya disparado una alerta
explícita todavía en este sprint (research.md documenta el mecanismo, no
agota cada regla de alerta posible).

## `aerohub_prueba_restauracion_rto_segundos` / `aerohub_prueba_restauracion_rpo_segundos` (Gauge)

Resultado de la ejecución MÁS RECIENTE de la prueba de restauración
semanal (C4) -- refleja `continuidad.prueba_restauracion`, última fila por
`ejecutado_en`. Permite ver en Grafana, sin consultar la base
directamente, si la última corrida cumplió RTO < 15 min / RPO ≤ 5 min --
insumo directo para la condición de cierre de RNF-R01 (ADR-018), aunque
ese cierre no ocurre en este sprint (spec.md, Assumptions).
