"""Metricas Prometheus de continuidad operacional (Sprint S1.9, ADR-018).

Expuestas por `tools/continuidad_agente.py` via `prometheus_client.start_http_server`
-- mismo patron que `aerohub_fids.metricas` (S1.3): los objetos viven en el
registro global del proceso, sin depender de un framework HTTP propio.
"""

from __future__ import annotations

from prometheus_client import Gauge

ATRASO_STANDBY_SEGUNDOS = Gauge(
    "aerohub_standby_lag_seconds",
    "Atraso de la replica de respaldo respecto al primario, en segundos",
)

SNAPSHOT_EDAD_SEGUNDOS = Gauge(
    "aerohub_snapshot_edad_segundos",
    "Antiguedad del snapshot verificado mas reciente, en segundos",
)

PRUEBA_RESTAURACION_RTO_SEGUNDOS = Gauge(
    "aerohub_prueba_restauracion_rto_segundos",
    "Tiempo de recuperacion observado en la ultima prueba de restauracion",
)

PRUEBA_RESTAURACION_RPO_SEGUNDOS = Gauge(
    "aerohub_prueba_restauracion_rpo_segundos",
    "Ventana de perdida de datos observada en la ultima prueba de restauracion",
)


def observar_atraso_standby(segundos: float) -> None:
    ATRASO_STANDBY_SEGUNDOS.set(segundos)


def observar_edad_snapshot(segundos: float) -> None:
    SNAPSHOT_EDAD_SEGUNDOS.set(segundos)


def observar_prueba_restauracion(*, rto_segundos: float, rpo_segundos: float) -> None:
    PRUEBA_RESTAURACION_RTO_SEGUNDOS.set(rto_segundos)
    PRUEBA_RESTAURACION_RPO_SEGUNDOS.set(rpo_segundos)
