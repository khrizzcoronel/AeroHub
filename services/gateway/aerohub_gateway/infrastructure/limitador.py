"""Rate limiting y cuotas en memoria, por proceso (Sprint S1.2, Plan §8.2,
"rate limiting y cuotas por API Key").

Limitacion deliberada de alcance: un cubo de fichas (token bucket) POR
PROCESO, en un diccionario en memoria protegido por un lock -- funciona
para un unico worker de desarrollo/pruebas, pero NO se comparte entre
replicas en un despliegue multi-proceso (eso requeriria un backend
compartido, p. ej. Redis, fuera de alcance de este sprint). Documentado
aqui, no escondido, para que nadie lo asuma valido en produccion tal cual.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

CAPACIDAD_POR_DEFECTO = 100  # peticiones de rafaga permitidas
TASA_RECARGA_POR_DEFECTO = 20.0  # peticiones/segundo en regimen sostenido


@dataclass
class _Cubo:
    fichas: float
    actualizado_en: float


class LimitadorTasa:
    def __init__(
        self,
        *,
        capacidad: int = CAPACIDAD_POR_DEFECTO,
        tasa_recarga: float = TASA_RECARGA_POR_DEFECTO,
    ) -> None:
        self._capacidad = capacidad
        self._tasa_recarga = tasa_recarga
        self._cubos: dict[str, _Cubo] = {}
        self._candado = Lock()

    def permitir(self, clave: str) -> bool:
        """Cubo de fichas clasico: cada clave (p. ej. "tenant_id:rol" o el
        prefijo de una API Key) tiene su propio cupo independiente.
        """
        ahora = time.monotonic()
        with self._candado:
            cubo = self._cubos.get(clave)
            if cubo is None:
                self._cubos[clave] = _Cubo(fichas=self._capacidad - 1, actualizado_en=ahora)
                return True
            transcurrido = ahora - cubo.actualizado_en
            cubo.fichas = min(self._capacidad, cubo.fichas + transcurrido * self._tasa_recarga)
            cubo.actualizado_en = ahora
            if cubo.fichas < 1:
                return False
            cubo.fichas -= 1
            return True


limitador_global = LimitadorTasa()
