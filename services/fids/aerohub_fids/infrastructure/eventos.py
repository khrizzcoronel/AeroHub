"""Publicacion en tiempo real de cambios de plantilla (Sprint S1.3, Plan
§8.3, RF-T03, RNF-P02: "propagacion < 1 s").

Mismo patron que aerohub_aodb.infrastructure.eventos (S1.2): broadcaster en
proceso con `queue.Queue` thread-safe (no `asyncio.Queue`, ver el docstring
de ese modulo para el porque). Se suscribe por PANTALLA (id), no por
tenant: un reproductor FIDS solo le interesan los cambios de SU PROPIA
pantalla, a diferencia del dashboard de vuelos que quiere todo el tenant.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class EventoPlantillaPantalla:
    tenant_id: int
    pantalla_id: int
    plantilla_id: int
    definicion_json: dict[str, Any]
    ocurrido_en: datetime


class BroadcasterFids:
    def __init__(self) -> None:
        self._suscriptores: dict[int, set[queue.Queue[EventoPlantillaPantalla]]] = {}
        self._candado = Lock()

    def suscribir(self, pantalla_id: int) -> queue.Queue[EventoPlantillaPantalla]:
        cola: queue.Queue[EventoPlantillaPantalla] = queue.Queue()
        with self._candado:
            self._suscriptores.setdefault(pantalla_id, set()).add(cola)
        return cola

    def desuscribir(self, pantalla_id: int, cola: queue.Queue[EventoPlantillaPantalla]) -> None:
        with self._candado:
            suscriptores = self._suscriptores.get(pantalla_id)
            if suscriptores is not None:
                suscriptores.discard(cola)

    def publicar(self, evento: EventoPlantillaPantalla) -> None:
        with self._candado:
            colas = list(self._suscriptores.get(evento.pantalla_id, ()))
        for cola in colas:
            cola.put_nowait(evento)


broadcaster_global = BroadcasterFids()
