"""Catalogo de conceptos de cargo para el formulario de alta de concepto
de tarifario (Sprint S1.17) -- sin esto, el formulario obligaria a pegar
un id Snowflake a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import listar_conceptos_cargo, sesion


@dataclass(frozen=True, slots=True)
class ConceptoCargo:
    id: int
    codigo: str
    nombre: str
    unidad_medida: str
    base_calculo: str


def consultar_conceptos_cargo() -> list[ConceptoCargo]:
    with sesion() as conn:
        filas = listar_conceptos_cargo(conn)
    return [
        ConceptoCargo(
            id=f.id,
            codigo=f.codigo,
            nombre=f.nombre,
            unidad_medida=f.unidad_medida,
            base_calculo=f.base_calculo,
        )
        for f in filas
    ]
