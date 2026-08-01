"""Consulta de una pantalla FIDS por codigo (Sprint S1.3, Plan §8.3).

Usada por el reproductor al arrancar, para obtener la plantilla vigente
ANTES de suscribirse al WebSocket (que solo entrega cambios futuros).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..infrastructure import obtener_pantalla_por_codigo, obtener_plantilla_por_id, sesion


@dataclass(frozen=True, slots=True)
class PantallaConsultada:
    id: int
    codigo: str
    plantilla_id: int
    definicion_json: dict[str, Any]
    estado: str


def consultar_pantalla_por_codigo(codigo: str) -> PantallaConsultada | None:
    with sesion() as conn:
        fila_pantalla = obtener_pantalla_por_codigo(conn, codigo)
        if fila_pantalla is None:
            return None
        fila_plantilla = obtener_plantilla_por_id(conn, fila_pantalla.plantilla_id)
    if fila_plantilla is None:
        return None
    return PantallaConsultada(
        id=fila_pantalla.id,
        codigo=fila_pantalla.codigo,
        plantilla_id=fila_pantalla.plantilla_id,
        definicion_json=fila_plantilla.definicion_json,
        estado=fila_pantalla.estado,
    )
