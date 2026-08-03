"""Catalogo de aeropuertos y planes para el workpanel de tenants (post
S1.13). `catalogo.aeropuerto` se redeclara localmente de solo lectura --
mismo patron que `ops.vuelo` en gates/ramp (independencia de modulos,
.importlinter): aerohub_tenancy no puede importar la Table de otro
modulo, y catalogo.aeropuerto no tiene un dueno claro entre los modulos
existentes (es referencia global, SDD-DATA-001 §18).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, MetaData, String, Table, select
from sqlalchemy.engine import Connection, Row

from .tablas import plan

_metadata = MetaData()

aeropuerto = Table(
    "aeropuerto",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo_iata", String(3)),
    Column("codigo_icao", String(4)),
    Column("nombre", String(150)),
    Column("ciudad", String(100)),
    schema="catalogo",
)


def listar_aeropuertos(conn: Connection) -> list[Row]:
    stmt = select(aeropuerto).order_by(aeropuerto.c.codigo_iata)
    return list(conn.execute(stmt))


def listar_planes(conn: Connection, *, solo_activos: bool = True) -> list[Row]:
    stmt = select(plan)
    if solo_activos:
        # MonetDB no acepta la sintaxis "IS true" que .is_(True) genera
        # (42000!syntax error, esperando sqlNULL/DISTINCT/NOT) -- hallazgo
        # empirico de este sprint. "= true" (comparacion de igualdad, no
        # el operador IS) si es valido.
        stmt = stmt.where(plan.c.activo == True)  # noqa: E712
    return list(conn.execute(stmt.order_by(plan.c.codigo)))
