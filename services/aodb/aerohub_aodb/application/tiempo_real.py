"""Suscripcion a eventos de estado de vuelo en tiempo real (Sprint S1.2,
Plan §8.2, RF-O04). Envoltorio delgado sobre el broadcaster de
infrastructure/ -- api/ no puede importar infrastructure/ directamente
(ADR-017 regla 3).
"""

from __future__ import annotations

import queue

from ..infrastructure import EventoEstadoVuelo, broadcaster_global

__all__ = ["suscribir_a_estado_vuelo", "desuscribir_de_estado_vuelo"]


def suscribir_a_estado_vuelo(tenant_id: int) -> queue.Queue[EventoEstadoVuelo]:
    return broadcaster_global.suscribir(tenant_id)


def desuscribir_de_estado_vuelo(tenant_id: int, cola: queue.Queue[EventoEstadoVuelo]) -> None:
    broadcaster_global.desuscribir(tenant_id, cola)
