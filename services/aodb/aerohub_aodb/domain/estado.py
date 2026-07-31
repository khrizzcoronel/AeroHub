"""Transiciones validas de estado de vuelo (Sprint S1.1, Plan §8.1).

`catalogo.estado_vuelo_catalogo` es un catalogo ABIERTO (SDD-DATA-001 §5.8):
no hay una lista fija de codigos en el dominio, solo la marca `es_terminal`.
La unica regla de dominio expresable sin conocer los codigos concretos es
estructural: un estado terminal no admite ninguna transicion posterior --
"terminal" significa precisamente eso.
"""

from __future__ import annotations

from dataclasses import dataclass

_ORIGENES_CAMBIO_VALIDOS = ("manual", "api", "automatico")


class TransicionEstadoInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class EstadoVuelo:
    id: int
    codigo: str
    es_terminal: bool


def validar_transicion(estado_actual: EstadoVuelo | None, estado_nuevo: EstadoVuelo) -> None:
    """estado_actual=None: primer estado registrado para el vuelo, siempre valido."""
    if estado_actual is not None and estado_actual.es_terminal:
        raise TransicionEstadoInvalida(
            f"'{estado_actual.codigo}' es un estado terminal; no admite "
            f"transicion a '{estado_nuevo.codigo}'"
        )


def validar_origen_cambio(origen_cambio: str) -> None:
    if origen_cambio not in _ORIGENES_CAMBIO_VALIDOS:
        raise TransicionEstadoInvalida(
            f"origen_cambio debe ser uno de {_ORIGENES_CAMBIO_VALIDOS}: {origen_cambio!r}"
        )
