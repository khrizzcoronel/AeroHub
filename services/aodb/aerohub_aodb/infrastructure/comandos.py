"""Escritura de ops.vuelo y ops.vuelo_estado (Sprint S1.1). Solo persiste --
domain/ ya valido, application/ ya genero el id y orquesta journal/auditoria.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import insert
from sqlalchemy.engine import Connection

from .tablas import vuelo, vuelo_estado


def insertar_vuelo(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    aerolinea_id: int,
    aeronave_id: int,
    numero_vuelo: str,
    tipo_vuelo_id: int,
    fecha_operacion: date,
    sentido: str,
    aeropuerto_origen_id: int,
    aeropuerto_destino_id: int,
    sta_utc: datetime,
    std_utc: datetime,
    pax_estimado: int | None = None,
) -> None:
    conn.execute(
        insert(vuelo).values(
            id=id,
            tenant_id=tenant_id,
            aerolinea_id=aerolinea_id,
            aeronave_id=aeronave_id,
            numero_vuelo=numero_vuelo,
            tipo_vuelo_id=tipo_vuelo_id,
            fecha_operacion=fecha_operacion,
            sentido=sentido,
            aeropuerto_origen_id=aeropuerto_origen_id,
            aeropuerto_destino_id=aeropuerto_destino_id,
            sta_utc=sta_utc,
            std_utc=std_utc,
            pax_estimado=pax_estimado,
        )
    )


def insertar_vuelo_estado(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    vuelo_id: int,
    estado_id: int,
    origen_cambio: str,
    registrado_por_usuario_id: int | None = None,
) -> None:
    conn.execute(
        insert(vuelo_estado).values(
            id=id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            estado_id=estado_id,
            origen_cambio=origen_cambio,
            registrado_por_usuario_id=registrado_por_usuario_id,
        )
    )
