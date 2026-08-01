"""Reintento ante conflictos de concurrencia (Sprint S1.2, RNF-P01).

MonetDB usa control de concurrencia OPTIMISTA (aislamiento tipo snapshot):
bajo escritura concurrente sobre datos relacionados, una transaccion puede
abortar EN EL COMMIT con SQLSTATE 40001 ("transaction is aborted because of
concurrency conflicts, will ROLLBACK instead") en vez de bloquear/esperar
como haria un motor con locking pesimista. Hallazgo empirico de S1.2: se
reproduce con apenas 10 `POST /vuelos/{id}/estados` concurrentes sobre el
MISMO vuelo, exactamente el escenario que RNF-P01 exige medir (100 cambios
de estado concurrentes).

Segundo hallazgo, mas sutil: tras el 40001 en el commit, SQLAlchemy intenta
un rollback de limpieza automatico -- pero MonetDB ya CERRO la conexion al
abortar la transaccion, asi que ese rollback falla con
`pymonetdb.exceptions.Error("connection closed")`, que SQLAlchemy envuelve
como `DBAPIError` GENERICO, no como `OperationalError` (pymonetdb no lo
tipa como tal). Capturar solo `OperationalError` deja pasar este segundo
error sin reintentar -- de ahi que el catch sea sobre `DBAPIError` (la
base), filtrando por contenido del mensaje, no por el subtipo exacto.
`pool_pre_ping=True` (base.py) se encarga de que el siguiente intento
obtenga una conexion viva del pool, no la que quedo muerta.

El reintento envuelve la funcion de caso de uso COMPLETA (no solo el
commit): `sesion()` es un context manager de un solo uso, la transaccion ya
fallo para cuando el error llega al llamador, asi que la unica forma de
recuperarse es volver a ejecutar toda la operacion desde el principio.
Esto es seguro porque cada mutacion de negocio vuelve a LEER el estado
vigente antes de decidir (p. ej. registrar_cambio_estado relee
v_vuelo_estado_actual) -- no hay una version en memoria que pueda quedar
obsoleta entre intentos.

Tercer hallazgo (S1.4, aerohub_gates -- "bloqueo de fila" simulado via
UPDATE sin efecto sobre `ops.puerta`, ver
aerohub_gates.infrastructure.comandos.bloquear_puerta_para_asignacion):
cuando DOS transacciones intentan escribir la MISMA fila en simultaneo (no
solo tablas transversales compartidas como en el hallazgo original de
S1.2), MonetDB aborta la perdedora de inmediato, EN EL PROPIO UPDATE, con
SQLSTATE 42000 y el mensaje "Update failed due to conflict with another
transaction" -- un SQLSTATE y una redaccion distintos del 40001
("...will ROLLBACK instead") documentado arriba, aunque la misma categoria
de conflicto de concurrencia optimista. Verificado empiricamente con dos
peticiones HTTP concurrentes reales sobre la misma puerta (PN-05).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from sqlalchemy.exc import DBAPIError

P = ParamSpec("P")
T = TypeVar("T")

_INTENTOS_POR_DEFECTO = 40
_ESPERA_BASE_S = 0.005
_ESPERA_MAXIMA_S = 0.15


def _es_conflicto_de_concurrencia(exc: DBAPIError) -> bool:
    mensaje = str(exc).lower()
    if "40001" in mensaje and "concurrency conflict" in mensaje:
        return True
    # Tercer hallazgo del docstring del modulo (S1.4): conflicto
    # inmediato sobre la MISMA fila, SQLSTATE 42000, redaccion distinta.
    if "conflict with another transaction" in mensaje:
        return True
    # Efecto secundario del conflicto (ver docstring del modulo): el
    # rollback de limpieza falla porque el motor ya cerro la conexion.
    return "connection closed" in mensaje


def reintentar_en_conflicto(
    *,
    intentos: int = _INTENTOS_POR_DEFECTO,
    espera_base_s: float = _ESPERA_BASE_S,
    espera_maxima_s: float = _ESPERA_MAXIMA_S,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorador(fn: Callable[P, T]) -> Callable[P, T]:
        @wraps(fn)
        def envoltura(*args: P.args, **kwargs: P.kwargs) -> T:
            for intento in range(intentos):
                try:
                    return fn(*args, **kwargs)
                except DBAPIError as exc:
                    if not _es_conflicto_de_concurrencia(exc) or intento == intentos - 1:
                        raise
                    # Jitter completo (no solo backoff exponencial): bajo
                    # alta contencion, varios hilos que reintentan con el
                    # MISMO cronograma determinista vuelven a chocar entre
                    # si una y otra vez -- el jitter descorrelaciona los
                    # reintentos entre hilos (hallazgo empirico de S1.2,
                    # RNF-P01 con 100 escrituras concurrentes).
                    techo = min(espera_maxima_s, espera_base_s * (2**intento))
                    time.sleep(random.uniform(0, techo))  # nosec: B311
            raise AssertionError("inalcanzable")  # el bucle siempre retorna o relanza

        return envoltura

    return decorador
