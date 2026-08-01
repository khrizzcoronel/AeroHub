"""Metricas Prometheus de FIDS (Sprint S1.3, Plan §8.3, "metricas de
latencia WebSocket por pantalla en Grafana").

Modulo transversal deliberadamente FUERA de domain/application/infrastructure/
api: no es logica de negocio ni toca la base de datos, es instrumentacion
de observabilidad que api/ (el handler WS) llama directamente. Los objetos
`Counter`/`Histogram` de `prometheus_client` viven en el registro GLOBAL
del proceso -- `services/gateway/main.py` (fuera de este paquete, ver su
propio docstring sobre independencia de modulos) expone `/metrics` leyendo
ese mismo registro, sin necesitar importar `aerohub_fids` para hacerlo.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    from .infrastructure import EventoPlantillaPantalla

LATENCIA_PROPAGACION_SEGUNDOS = Histogram(
    "fids_latencia_propagacion_segundos",
    "Latencia entre la publicacion de un cambio de plantilla y su entrega por WS a la pantalla",
    labelnames=("pantalla",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

HEARTBEATS_RECIBIDOS_TOTAL = Counter(
    "fids_heartbeats_recibidos_total",
    "Heartbeats de pantalla FIDS recibidos",
    labelnames=("pantalla",),
)

PANTALLAS_SIN_SENAL_TOTAL = Counter(
    "fids_pantallas_sin_senal_total",
    "Transiciones de una pantalla FIDS a estado sin_senal, detectadas por el monitor",
)


def observar_latencia_propagacion(*, pantalla: str, evento: EventoPlantillaPantalla) -> None:
    """`pantalla` es cualquier identificador estable de la pantalla (codigo
    o id como string) -- el llamador usa el que tenga a mano sin necesidad
    de una consulta adicional solo para etiquetar la metrica.
    """
    latencia_s = max(0.0, time.time() - evento.ocurrido_en.timestamp())
    LATENCIA_PROPAGACION_SEGUNDOS.labels(pantalla=pantalla).observe(latencia_s)


def contar_heartbeat(*, pantalla: str) -> None:
    HEARTBEATS_RECIBIDOS_TOTAL.labels(pantalla=pantalla).inc()


def contar_pantalla_sin_senal(*, cantidad: int) -> None:
    if cantidad:
        PANTALLAS_SIN_SENAL_TOTAL.inc(cantidad)
