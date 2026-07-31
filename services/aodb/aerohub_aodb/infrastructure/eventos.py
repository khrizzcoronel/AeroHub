"""Publicacion en tiempo real de cambios de estado de vuelo (Sprint S1.2,
Plan §8.2, RF-O04, RNF-P01: "propagacion < 1 s").

Broadcaster en proceso: cada conexion WebSocket abierta se suscribe con su
propia `queue.Queue` (no `asyncio.Queue` -- application/registrar_cambio_estado
publica desde un handler FastAPI SINCRONO, que FastAPI ejecuta en un hilo de
threadpool, no en el hilo del event loop; escribir a un `asyncio.Queue`
desde otro hilo no es seguro sin `call_soon_threadsafe`. `queue.Queue` es
thread-safe de fabrica, y el endpoint WS -- async -- hace la espera
bloqueante en un hilo aparte via `asyncio.to_thread`, sin bloquear el
event loop).

Igual que el limitador de tasa (aerohub_gateway): por PROCESO, no
compartido entre replicas -- produccion necesitaria un backend pub/sub
real (p. ej. Redis Streams) para propagar entre workers/instancias.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass
from datetime import datetime
from threading import Lock


@dataclass(frozen=True, slots=True)
class EventoEstadoVuelo:
    tenant_id: int
    vuelo_id: int
    vuelo_estado_id: int
    estado_id: int
    codigo_estado: str
    ocurrido_en: datetime


class BroadcasterEstadoVuelo:
    def __init__(self) -> None:
        self._suscriptores: dict[int, set[queue.Queue[EventoEstadoVuelo]]] = {}
        self._candado = Lock()

    def suscribir(self, tenant_id: int) -> queue.Queue[EventoEstadoVuelo]:
        cola: queue.Queue[EventoEstadoVuelo] = queue.Queue()
        with self._candado:
            self._suscriptores.setdefault(tenant_id, set()).add(cola)
        return cola

    def desuscribir(self, tenant_id: int, cola: queue.Queue[EventoEstadoVuelo]) -> None:
        with self._candado:
            suscriptores = self._suscriptores.get(tenant_id)
            if suscriptores is not None:
                suscriptores.discard(cola)

    def publicar(self, evento: EventoEstadoVuelo) -> None:
        with self._candado:
            colas = list(self._suscriptores.get(evento.tenant_id, ()))
        for cola in colas:
            cola.put_nowait(evento)


broadcaster_global = BroadcasterEstadoVuelo()
