"""Catalogos de solo lectura de M9 Compliance para los formularios de
alta de incidente/reporte/evidencia (Sprint S1.19).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import (
    listar_controles_soc2,
    listar_tipos_incidente,
    listar_tipos_reporte_regulatorio,
    sesion,
)


@dataclass(frozen=True, slots=True)
class TipoIncidente:
    id: int
    codigo: str
    descripcion: str
    categoria: str


@dataclass(frozen=True, slots=True)
class TipoReporteRegulatorio:
    id: int
    codigo: str
    nombre: str
    periodicidad: str
    autoridad: str


@dataclass(frozen=True, slots=True)
class ControlSoc2:
    id: int
    codigo_control: str
    nombre: str
    categoria: str


def consultar_tipos_incidente() -> list[TipoIncidente]:
    with sesion() as conn:
        filas = listar_tipos_incidente(conn)
    return [
        TipoIncidente(id=f.id, codigo=f.codigo, descripcion=f.descripcion, categoria=f.categoria)
        for f in filas
    ]


def consultar_tipos_reporte() -> list[TipoReporteRegulatorio]:
    with sesion() as conn:
        filas = listar_tipos_reporte_regulatorio(conn)
    return [
        TipoReporteRegulatorio(
            id=f.id,
            codigo=f.codigo,
            nombre=f.nombre,
            periodicidad=f.periodicidad,
            autoridad=f.autoridad,
        )
        for f in filas
    ]


def consultar_controles_soc2() -> list[ControlSoc2]:
    with sesion() as conn:
        filas = listar_controles_soc2(conn)
    return [
        ControlSoc2(
            id=f.id, codigo_control=f.codigo_control, nombre=f.nombre, categoria=f.categoria
        )
        for f in filas
    ]
