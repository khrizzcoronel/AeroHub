"""Consulta de un vuelo por id (Sprint S1.1, Plan §8.1; PN-01).

Un vuelo de otro tenant es indistinguible de un vuelo que no existe: esta
funcion devuelve `None` en ambos casos, nunca lanza una excepcion que el
llamador de api/ pudiera traducir a un 403 (eso confirmaria la existencia
del recurso ajeno, exactamente lo que PN-01 prohibe).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..infrastructure import obtener_vuelo_por_id, sesion


@dataclass(frozen=True, slots=True)
class VueloConsultado:
    id: int
    aerolinea_id: int
    aeronave_id: int
    numero_vuelo: str
    tipo_vuelo_id: int
    fecha_operacion: date
    sentido: str
    aeropuerto_origen_id: int
    aeropuerto_destino_id: int
    sta_utc: datetime
    std_utc: datetime
    pax_estimado: int | None


def consultar_vuelo(vuelo_id: int) -> VueloConsultado | None:
    with sesion() as conn:
        fila = obtener_vuelo_por_id(conn, vuelo_id)
    if fila is None:
        return None
    return VueloConsultado(
        id=fila.id,
        aerolinea_id=fila.aerolinea_id,
        aeronave_id=fila.aeronave_id,
        numero_vuelo=fila.numero_vuelo,
        tipo_vuelo_id=fila.tipo_vuelo_id,
        fecha_operacion=fila.fecha_operacion,
        sentido=fila.sentido,
        aeropuerto_origen_id=fila.aeropuerto_origen_id,
        aeropuerto_destino_id=fila.aeropuerto_destino_id,
        sta_utc=fila.sta_utc,
        std_utc=fila.std_utc,
        pax_estimado=fila.pax_estimado,
    )
