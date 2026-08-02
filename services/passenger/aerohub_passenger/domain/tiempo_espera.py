"""Agregacion de tiempo de espera por franja horaria (Sprint S1.6, CU-O19,
RF-O17). Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017
Sec5.4, regla 1).

`franja_de` bucketiza un instante en una franja de ancho fijo -- el mismo
criterio usado por infrastructure/ para leer y para escribir, garantiza
que ambos lados bucketicen igual.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import ROUND_HALF_UP, Decimal
from statistics import fmean

_CUANTIZACION = Decimal("0.01")


class FranjaInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoAgregacion:
    minutos_estimados: Decimal
    muestra_n: int


def franja_de(momento: time, *, franja_minutos: int) -> tuple[time, time]:
    if franja_minutos <= 0 or franja_minutos > 24 * 60:
        raise FranjaInvalida(f"franja_minutos debe estar en (0, 1440]: {franja_minutos}")
    minutos_del_dia = momento.hour * 60 + momento.minute
    inicio_min = (minutos_del_dia // franja_minutos) * franja_minutos
    fin_min = min(inicio_min + franja_minutos, 24 * 60 - 1)
    return (
        time(hour=inicio_min // 60, minute=inicio_min % 60),
        time(hour=fin_min // 60, minute=fin_min % 60),
    )


def agregacion_por_franja(duraciones_minutos: list[Decimal]) -> ResultadoAgregacion:
    """Sin ningun dato individual de pasajero, vuelo o agente en la
    entrada -- solo una lista de duraciones en minutos (PN-11)."""
    muestra_n = len(duraciones_minutos)
    if muestra_n == 0:
        return ResultadoAgregacion(minutos_estimados=Decimal("0"), muestra_n=0)
    promedio = Decimal(fmean(float(d) for d in duraciones_minutos))
    return ResultadoAgregacion(
        minutos_estimados=promedio.quantize(_CUANTIZACION, rounding=ROUND_HALF_UP),
        muestra_n=muestra_n,
    )


def descarta_por_muestra_insuficiente(muestra_n: int) -> bool:
    """RF-O17/edge case de spec.md: sin muestras, no se inventa un
    estimado -- la franja no se publica."""
    return muestra_n == 0
