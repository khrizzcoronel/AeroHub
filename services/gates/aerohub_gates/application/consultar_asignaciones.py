"""Consulta de asignaciones y puertas para el tablero (Sprint S1.4, Plan
§8.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..infrastructure import listar_asignaciones, listar_puertas, sesion


@dataclass(frozen=True, slots=True)
class AsignacionTablero:
    id: int
    puerta_id: int
    puerta_codigo: str
    vuelo_id: int
    numero_vuelo: str
    inicio_previsto: datetime
    fin_previsto: datetime
    estado: str


@dataclass(frozen=True, slots=True)
class PuertaTablero:
    id: int
    terminal_id: int
    codigo: str
    tipo: str
    envergadura_max_m: float
    tiene_pasarela: bool


def consultar_tablero_de_puertas() -> tuple[list[PuertaTablero], list[AsignacionTablero]]:
    with sesion() as conn:
        puertas = listar_puertas(conn)
        asignaciones = listar_asignaciones(conn)
    return (
        [
            PuertaTablero(
                id=p.id,
                terminal_id=p.terminal_id,
                codigo=p.codigo,
                tipo=p.tipo,
                envergadura_max_m=float(p.envergadura_max_m),
                tiene_pasarela=p.tiene_pasarela,
            )
            for p in puertas
        ],
        [
            AsignacionTablero(
                id=a.id,
                puerta_id=a.puerta_id,
                puerta_codigo=a.puerta_codigo,
                vuelo_id=a.vuelo_id,
                numero_vuelo=a.numero_vuelo,
                inicio_previsto=a.inicio_previsto,
                fin_previsto=a.fin_previsto,
                estado=a.estado,
            )
            for a in asignaciones
        ],
    )
