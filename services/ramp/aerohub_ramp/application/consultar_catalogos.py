"""Catalogos de solo lectura de rampa (Sprint post-S1.20, cierre de
brechas de workpanel): `rampa.tipo_tarea` no tenia ningun endpoint de
listado -- el formulario de "iniciar tarea" pedia el id a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import listar_tipos_tarea, sesion


@dataclass(frozen=True, slots=True)
class TipoTarea:
    id: int
    codigo: str
    nombre: str
    duracion_estandar_min: int


def consultar_tipos_tarea() -> list[TipoTarea]:
    with sesion() as conn:
        filas = listar_tipos_tarea(conn)
    return [
        TipoTarea(
            id=f.id,
            codigo=f.codigo,
            nombre=f.nombre,
            duracion_estandar_min=f.duracion_estandar_min,
        )
        for f in filas
    ]
