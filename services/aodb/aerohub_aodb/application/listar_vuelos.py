"""Listado de vuelos del tenant, con filtros de fecha y estado actual
(Fase 3 de docs/diseno/PLAN_CORRECCION_MODULOS.md, causa raiz D: la vista
nucleo de M1 no podia mostrar nada al entrar -- dependia enteramente del
WebSocket de eventos en vivo).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..infrastructure import listar_vuelos as _listar_vuelos_infra
from ..infrastructure import sesion


@dataclass(frozen=True, slots=True)
class VueloListado:
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
    codigo_estado: str | None


def listar_vuelos(
    *, fecha_operacion: date | None = None, codigo_estado: str | None = None
) -> list[VueloListado]:
    with sesion() as conn:
        filas = _listar_vuelos_infra(
            conn, fecha_operacion=fecha_operacion, codigo_estado=codigo_estado
        )
    return [
        VueloListado(
            id=f.id,
            aerolinea_id=f.aerolinea_id,
            aeronave_id=f.aeronave_id,
            numero_vuelo=f.numero_vuelo,
            tipo_vuelo_id=f.tipo_vuelo_id,
            fecha_operacion=f.fecha_operacion,
            sentido=f.sentido,
            aeropuerto_origen_id=f.aeropuerto_origen_id,
            aeropuerto_destino_id=f.aeropuerto_destino_id,
            sta_utc=f.sta_utc,
            std_utc=f.std_utc,
            pax_estimado=f.pax_estimado,
            codigo_estado=f.codigo_estado,
        )
        for f in filas
    ]
