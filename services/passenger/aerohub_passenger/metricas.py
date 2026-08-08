"""Metricas Prometheus de M6 Experiencia del Pasajero (RF-O17, 2026-08-08).

Modulo transversal deliberadamente FUERA de domain/application/infrastructure/
api -- mismo criterio y mismo docstring que `aerohub_fids.metricas`: no es
logica de negocio ni toca la base, es instrumentacion. Los objetos viven en
el registro GLOBAL de prometheus_client, que `services/gateway/main.py`
expone en `/metrics` sin necesidad de importar este paquete.

Por que estas 3 y no otras: RF-O17 exige que el estimado se refresque cada
<= 15 min. Lo que hay que poder observar es si el ciclo efectivamente
corre (`ultimo_ciclo_timestamp`, del que se deriva la antiguedad), cuanto
publica (`franjas_actualizadas_total`) y si esta fallando en silencio
(`terminales_con_error_total`) -- un ciclo que corre pero falla en todas
las terminales se veria "sano" mirando solo la frecuencia.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge

RECALCULO_ULTIMO_CICLO_TIMESTAMP = Gauge(
    "passenger_recalculo_ultimo_ciclo_timestamp_segundos",
    "Marca de tiempo UNIX del ultimo ciclo de recalculo de tiempos de espera completado",
)

RECALCULO_FRANJAS_ACTUALIZADAS_TOTAL = Counter(
    "passenger_recalculo_franjas_actualizadas_total",
    "Franjas de tiempo de espera publicadas o actualizadas por el ciclo programado",
)

RECALCULO_TERMINALES_CON_ERROR_TOTAL = Counter(
    "passenger_recalculo_terminales_con_error_total",
    "Terminales cuyo recalculo fallo dentro de un ciclo programado",
)


def observar_ciclo_recalculo(
    *, momento_unix: float, franjas_actualizadas: int, terminales_con_error: int
) -> None:
    RECALCULO_ULTIMO_CICLO_TIMESTAMP.set(momento_unix)
    if franjas_actualizadas:
        RECALCULO_FRANJAS_ACTUALIZADAS_TOTAL.inc(franjas_actualizadas)
    if terminales_con_error:
        RECALCULO_TERMINALES_CON_ERROR_TOTAL.inc(terminales_con_error)
