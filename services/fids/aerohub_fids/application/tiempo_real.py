"""Suscripcion a cambios de plantilla en tiempo real (Sprint S1.3, Plan
§8.3, RF-T03). Envoltorio delgado sobre el broadcaster de infrastructure/
-- api/ no puede importar infrastructure/ directamente (ADR-017 regla 3).
"""

from __future__ import annotations

import queue

from ..infrastructure import EventoPlantillaPantalla, broadcaster_global

__all__ = ["suscribir_a_plantilla_pantalla", "desuscribir_de_plantilla_pantalla"]


def suscribir_a_plantilla_pantalla(pantalla_id: int) -> queue.Queue[EventoPlantillaPantalla]:
    return broadcaster_global.suscribir(pantalla_id)


def desuscribir_de_plantilla_pantalla(
    pantalla_id: int, cola: queue.Queue[EventoPlantillaPantalla]
) -> None:
    broadcaster_global.desuscribir(pantalla_id, cola)
