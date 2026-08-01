"""Lecturas de rampa.* y ops.vuelo (Sprint S1.5). Mismo patron que
aerohub_gates.infrastructure.consultas: toda consulta sobre una tabla
alcance='tenant' filtra por `contexto_tenant_id()`, sin excepcion (PN-01).

`listar_tareas_de_turnaround` implementa el minimo privilegio de
role_ramp_agent (Plan §8.5, compuerta de pruebas: "no lee ni escribe
turnarounds ajenos") -- MonetDB no soporta RLS nativo, el filtro por
agente_usuario_id se aplica aqui, en la capa de aplicacion (mismo patron
documentado para role_airline_coordinator/role_ramp_agent sobre `ops` en
96_grants_ops.sql).
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import select
from sqlalchemy.engine import Connection, Row

from .tablas import (
    incidencia_rampa,
    tarea_turnaround,
    tipo_incidencia_rampa,
    tipo_tarea,
    turnaround,
    vuelo,
)

_ROL_CON_ACCESO_RESTRINGIDO = "role_ramp_agent"


def obtener_vuelo_por_id(conn: Connection, vuelo_id: int) -> Row | None:
    stmt = select(vuelo).where(vuelo.c.tenant_id == contexto_tenant_id(), vuelo.c.id == vuelo_id)
    return conn.execute(stmt).first()


def obtener_tipo_tarea_por_id(conn: Connection, tipo_tarea_id: int) -> Row | None:
    stmt = select(tipo_tarea).where(tipo_tarea.c.id == tipo_tarea_id)
    return conn.execute(stmt).first()


def obtener_tipo_incidencia_por_codigo(conn: Connection, codigo: str) -> Row | None:
    stmt = select(tipo_incidencia_rampa).where(tipo_incidencia_rampa.c.codigo == codigo)
    return conn.execute(stmt).first()


def obtener_turnaround_por_id(conn: Connection, turnaround_id: int) -> Row | None:
    stmt = select(turnaround).where(
        turnaround.c.tenant_id == contexto_tenant_id(), turnaround.c.id == turnaround_id
    )
    return conn.execute(stmt).first()


def obtener_turnaround_por_vuelo_llegada(conn: Connection, vuelo_llegada_id: int) -> Row | None:
    """Pre-chequeo de uq_turnaround_tenant_vuelo_llegada -- mismo motivo
    que aerohub_fids valida version antes de insertar: un 409 legible en
    vez de dejar que la UNIQUE del motor produzca un error generico."""
    stmt = select(turnaround).where(
        turnaround.c.tenant_id == contexto_tenant_id(),
        turnaround.c.vuelo_llegada_id == vuelo_llegada_id,
    )
    return conn.execute(stmt).first()


def obtener_tarea_turnaround_por_id(conn: Connection, tarea_id: int) -> Row | None:
    stmt = select(tarea_turnaround).where(
        tarea_turnaround.c.tenant_id == contexto_tenant_id(), tarea_turnaround.c.id == tarea_id
    )
    return conn.execute(stmt).first()


def listar_tareas_de_turnaround(
    conn: Connection, *, turnaround_id: int, rol_actor: str, usuario_id: int | None
) -> list[Row]:
    condiciones = [
        tarea_turnaround.c.tenant_id == contexto_tenant_id(),
        tarea_turnaround.c.turnaround_id == turnaround_id,
    ]
    if rol_actor == _ROL_CON_ACCESO_RESTRINGIDO:
        condiciones.append(tarea_turnaround.c.agente_usuario_id == usuario_id)
    stmt = select(tarea_turnaround).where(*condiciones)
    return list(conn.execute(stmt))


def listar_turnarounds(conn: Connection) -> list[Row]:
    vuelo_llegada = vuelo.alias("vuelo_llegada")
    vuelo_salida = vuelo.alias("vuelo_salida")
    stmt = (
        select(
            turnaround.c.id,
            turnaround.c.vuelo_llegada_id,
            vuelo_llegada.c.numero_vuelo.label("numero_vuelo_llegada"),
            turnaround.c.vuelo_salida_id,
            vuelo_salida.c.numero_vuelo.label("numero_vuelo_salida"),
            turnaround.c.aeronave_id,
            turnaround.c.inicio_previsto,
            turnaround.c.fin_previsto,
            turnaround.c.estado,
        )
        .select_from(
            turnaround.join(
                vuelo_llegada, vuelo_llegada.c.id == turnaround.c.vuelo_llegada_id
            ).join(vuelo_salida, vuelo_salida.c.id == turnaround.c.vuelo_salida_id)
        )
        .where(
            turnaround.c.tenant_id == contexto_tenant_id(),
            vuelo_llegada.c.tenant_id == contexto_tenant_id(),
            vuelo_salida.c.tenant_id == contexto_tenant_id(),
        )
    )
    return list(conn.execute(stmt))


def listar_incidencias(conn: Connection) -> list[Row]:
    stmt = (
        select(
            incidencia_rampa.c.id,
            incidencia_rampa.c.tarea_turnaround_id,
            tipo_incidencia_rampa.c.codigo.label("tipo_incidencia_codigo"),
            incidencia_rampa.c.descripcion,
            incidencia_rampa.c.severidad,
            incidencia_rampa.c.detectada_en,
        )
        .select_from(
            incidencia_rampa.join(
                tipo_incidencia_rampa,
                tipo_incidencia_rampa.c.id == incidencia_rampa.c.tipo_incidencia_id,
            )
        )
        .where(incidencia_rampa.c.tenant_id == contexto_tenant_id())
    )
    return list(conn.execute(stmt))
