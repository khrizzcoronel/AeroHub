"""Catalogos para poblar los selects del formulario de tenant (post
S1.13): antes se pedia el id de memoria en un campo de texto libre.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import listar_aeropuertos as _listar_aeropuertos
from ..infrastructure import listar_planes as _listar_planes
from ..infrastructure import sesion


@dataclass(frozen=True, slots=True)
class Aeropuerto:
    id: int
    codigo_iata: str
    codigo_icao: str
    nombre: str
    ciudad: str


@dataclass(frozen=True, slots=True)
class Plan:
    id: int
    codigo: str
    nombre: str
    tarifa_base_mensual: str
    moneda: str


def listar_aeropuertos() -> list[Aeropuerto]:
    with sesion() as conn:
        filas = _listar_aeropuertos(conn)
    return [
        Aeropuerto(
            id=f.id,
            codigo_iata=f.codigo_iata,
            codigo_icao=f.codigo_icao,
            nombre=f.nombre,
            ciudad=f.ciudad,
        )
        for f in filas
    ]


def listar_planes() -> list[Plan]:
    with sesion() as conn:
        filas = _listar_planes(conn)
    return [
        Plan(
            id=f.id,
            codigo=f.codigo,
            nombre=f.nombre,
            tarifa_base_mensual=str(f.tarifa_base_mensual),
            moneda=f.moneda,
        )
        for f in filas
    ]
