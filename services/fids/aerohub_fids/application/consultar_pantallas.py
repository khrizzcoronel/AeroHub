"""Listado de pantallas FIDS con telemetria -- el "tablero de
telemetria" del plan (Sprint S1.16, PLAN v3.0 §8-bis.2, research.md
Decision 3). Expone `estado`/`ultima_senal_en` tal como el backend ya
los mantiene, sin recalcular nada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..infrastructure import listar_pantallas as _listar_pantallas
from ..infrastructure import sesion


@dataclass(frozen=True, slots=True)
class PantallaResumen:
    id: int
    terminal_id: int
    codigo: str
    plantilla_id: int
    ubicacion_descripcion: str | None
    estado: str
    ultima_senal_en: datetime | None
    version_firmware: str | None


def consultar_pantallas() -> list[PantallaResumen]:
    with sesion() as conn:
        filas = _listar_pantallas(conn)
    return [
        PantallaResumen(
            id=f.id,
            terminal_id=f.terminal_id,
            codigo=f.codigo,
            plantilla_id=f.plantilla_id,
            ubicacion_descripcion=f.ubicacion_descripcion,
            estado=f.estado,
            ultima_senal_en=f.ultima_senal_en,
            version_firmware=f.version_firmware,
        )
        for f in filas
    ]
