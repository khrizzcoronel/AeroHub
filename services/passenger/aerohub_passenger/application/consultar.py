"""Lectura de tiempos de espera publicados (Sprint S1.6). Proyeccion
limitada a las columnas del contrato -- ningun campo de pasajero, vuelo o
agente individual (PN-11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from ..infrastructure import listar_tiempos_espera, sesion


@dataclass(frozen=True, slots=True)
class FranjaTiempoEspera:
    franja_inicio: time
    franja_fin: time
    minutos_estimados: Decimal
    muestra_n: int
    calculado_en: datetime


def consultar_tiempos_espera(*, terminal_id: int, fecha: date) -> list[FranjaTiempoEspera]:
    with sesion() as conn:
        filas = listar_tiempos_espera(conn, terminal_id=terminal_id, fecha=fecha)
    return [
        FranjaTiempoEspera(
            franja_inicio=f.franja_inicio,
            franja_fin=f.franja_fin,
            minutos_estimados=f.minutos_estimados,
            muestra_n=f.muestra_n,
            calculado_en=f.calculado_en,
        )
        for f in filas
    ]
