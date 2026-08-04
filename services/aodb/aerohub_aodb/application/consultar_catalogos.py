"""Catalogos de apoyo para el formulario de alta de vuelo (Sprint S1.15,
PLAN v3.0 §8-bis.1) -- sin esto, el formulario obligaria a pegar un id
Snowflake a mano (FR-010).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import listar_aerolineas as _listar_aerolineas
from ..infrastructure import listar_aeronaves as _listar_aeronaves
from ..infrastructure import listar_aeropuertos as _listar_aeropuertos
from ..infrastructure import listar_tipos_vuelo as _listar_tipos_vuelo
from ..infrastructure import sesion


@dataclass(frozen=True, slots=True)
class Aerolinea:
    id: int
    codigo_iata: str
    codigo_icao: str
    nombre: str


@dataclass(frozen=True, slots=True)
class Aeronave:
    id: int
    matricula: str
    aerolinea_id: int
    fabricante: str
    modelo: str


@dataclass(frozen=True, slots=True)
class TipoVuelo:
    id: int
    codigo: str
    descripcion: str


@dataclass(frozen=True, slots=True)
class Aeropuerto:
    id: int
    codigo_iata: str
    codigo_icao: str
    nombre: str
    ciudad: str


def consultar_aerolineas() -> list[Aerolinea]:
    with sesion() as conn:
        filas = _listar_aerolineas(conn)
    return [
        Aerolinea(id=f.id, codigo_iata=f.codigo_iata, codigo_icao=f.codigo_icao, nombre=f.nombre)
        for f in filas
    ]


def consultar_aeronaves() -> list[Aeronave]:
    with sesion() as conn:
        filas = _listar_aeronaves(conn)
    return [
        Aeronave(
            id=f.id,
            matricula=f.matricula,
            aerolinea_id=f.aerolinea_id,
            fabricante=f.fabricante,
            modelo=f.modelo,
        )
        for f in filas
    ]


def consultar_tipos_vuelo() -> list[TipoVuelo]:
    with sesion() as conn:
        filas = _listar_tipos_vuelo(conn)
    return [TipoVuelo(id=f.id, codigo=f.codigo, descripcion=f.descripcion) for f in filas]


def consultar_aeropuertos() -> list[Aeropuerto]:
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
