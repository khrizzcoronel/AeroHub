"""Consulta de asignaciones y puertas para el tablero (Sprint S1.4, Plan
§8.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..infrastructure import (
    listar_asignaciones,
    listar_puertas,
    listar_vuelos_sin_asignacion_con_envergadura,
    sesion,
)


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


@dataclass(frozen=True, slots=True)
class VueloSinAsignar:
    id: int
    numero_vuelo: str
    sta_utc: datetime
    std_utc: datetime
    envergadura_m: float


def consultar_vuelos_sin_asignacion() -> list[VueloSinAsignar]:
    """Sprint S1.4 ya tenia esta consulta (asignador automatico PuLP) sin
    ningun listado expuesto por API -- el formulario "Asignar puerta
    manualmente" pedia el id de vuelo a mano (hallazgo 2026-08-08, pedido
    directo del usuario: "deberia ser combo seleccioname")."""
    with sesion() as conn:
        filas = listar_vuelos_sin_asignacion_con_envergadura(conn)
    return [
        VueloSinAsignar(
            id=f.id,
            numero_vuelo=f.numero_vuelo,
            sta_utc=f.sta_utc,
            std_utc=f.std_utc,
            envergadura_m=float(f.envergadura_m),
        )
        for f in filas
    ]


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
