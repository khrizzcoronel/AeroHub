"""Catalogo de terminales para el formulario de registro de pantalla
(Sprint S1.16, PLAN v3.0 §8-bis.2) -- sin esto, el formulario obligaria a
pegar un id Snowflake a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import listar_terminales as _listar_terminales
from ..infrastructure import sesion


@dataclass(frozen=True, slots=True)
class Terminal:
    id: int
    codigo: str
    nombre: str


def consultar_terminales() -> list[Terminal]:
    with sesion() as conn:
        filas = _listar_terminales(conn)
    return [Terminal(id=f.id, codigo=f.codigo, nombre=f.nombre) for f in filas]
