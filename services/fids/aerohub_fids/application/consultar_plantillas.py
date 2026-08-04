"""Listado de plantillas FIDS (Sprint S1.16, PLAN v3.0 §8-bis.2) -- solo
la ultima version de cada nombre, ver
infrastructure/consultas.py::listar_plantillas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..infrastructure import listar_plantillas as _listar_plantillas
from ..infrastructure import sesion


@dataclass(frozen=True, slots=True)
class PlantillaResumen:
    id: int
    nombre: str
    definicion_json: dict[str, Any]
    version: int
    vigente_desde: datetime


def consultar_plantillas() -> list[PlantillaResumen]:
    with sesion() as conn:
        filas = _listar_plantillas(conn)
    return [
        PlantillaResumen(
            id=f.id,
            nombre=f.nombre,
            definicion_json=f.definicion_json,
            version=f.version,
            vigente_desde=f.vigente_desde,
        )
        for f in filas
    ]
