"""Escritura de rampa.turnaround / tarea_turnaround / incidencia_rampa
(Sprint S1.5). Solo persiste -- domain/ ya valido, application/ ya genero
el id y decide journal/auditoria.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import incidencia_rampa, tarea_turnaround, turnaround


def insertar_turnaround(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    vuelo_llegada_id: int,
    vuelo_salida_id: int,
    aeronave_id: int,
    inicio_previsto: datetime,
    fin_previsto: datetime,
) -> None:
    conn.execute(
        insert(turnaround).values(
            id=id,
            tenant_id=tenant_id,
            vuelo_llegada_id=vuelo_llegada_id,
            vuelo_salida_id=vuelo_salida_id,
            aeronave_id=aeronave_id,
            inicio_previsto=inicio_previsto,
            fin_previsto=fin_previsto,
            estado="planificado",
        )
    )


def insertar_tarea_turnaround(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    turnaround_id: int,
    tipo_tarea_id: int,
    agente_usuario_id: int,
    inicio_real: datetime,
) -> None:
    conn.execute(
        insert(tarea_turnaround).values(
            id=id,
            tenant_id=tenant_id,
            turnaround_id=turnaround_id,
            tipo_tarea_id=tipo_tarea_id,
            agente_usuario_id=agente_usuario_id,
            inicio_real=inicio_real,
            estado="en_curso",
        )
    )


def finalizar_tarea_turnaround(
    conn: Connection, *, id: int, tenant_id: int, fin_real: datetime
) -> None:
    conn.execute(
        update(tarea_turnaround)
        .where(tarea_turnaround.c.id == id, tarea_turnaround.c.tenant_id == tenant_id)
        .values(fin_real=fin_real, estado="completada")
    )


def insertar_incidencia_rampa(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    tarea_turnaround_id: int,
    tipo_incidencia_id: int,
    descripcion: str,
    severidad: str,
) -> None:
    conn.execute(
        insert(incidencia_rampa).values(
            id=id,
            tenant_id=tenant_id,
            tarea_turnaround_id=tarea_turnaround_id,
            tipo_incidencia_id=tipo_incidencia_id,
            descripcion=descripcion,
            severidad=severidad,
        )
    )
