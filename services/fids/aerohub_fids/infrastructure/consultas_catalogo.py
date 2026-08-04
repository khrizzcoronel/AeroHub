"""Catalogo de terminales para el formulario de registro de pantalla
(Sprint S1.16, PLAN v3.0 §8-bis.2). `ops.terminal` se redeclara aqui de
solo lectura -- mismo patron que `catalogo.aeropuerto` en tenancy (S1.13)
o `catalogo.aerolinea`/`aeronave`/`tipo_vuelo` en aodb (S1.15):
independencia de modulos, ADR-017 §5.4, `aerohub_fids` no importa
`aerohub_aodb` para leer una tabla que no le pertenece.

A diferencia de esos catalogos (verdaderamente globales, sin tenant_id),
`ops.terminal` SI tiene tenant_id -- cada tenant tiene sus propias
terminales, asi que esta consulta SI filtra por tenant (research.md
Decision 4), no es alcance_global().
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import BigInteger, Column, MetaData, String, Table, select
from sqlalchemy.engine import Connection, Row

_metadata = MetaData()

terminal = Table(
    "terminal",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("codigo", String(10)),
    Column("nombre", String(100)),
    schema="ops",
)


def listar_terminales(conn: Connection) -> list[Row]:
    stmt = (
        select(terminal)
        .where(terminal.c.tenant_id == contexto_tenant_id())
        .order_by(terminal.c.codigo)
    )
    return list(conn.execute(stmt))
