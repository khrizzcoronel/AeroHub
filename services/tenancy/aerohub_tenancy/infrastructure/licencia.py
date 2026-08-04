"""Lectura de tenants.licencia / catalogo.modulo, reutilizada por el
calculo de modulos visibles de S1.10 (contracts/perfil-acceso.md).

Mismo `Table()` y misma logica de vigencia que
`aerohub_gateway.infrastructure.licencia.existe_licencia_vigente` (S1.7),
sin modificar ese codigo -- este modulo YA es propietario de
`tenants.licencia` (alcance G1 'tenant', ver alcances.py), asi que declara
su propia copia de solo lectura en vez de importar la de
`aerohub_gateway` (el contrato de independencia de modulos, .importlinter,
prohibe justo esa direccion de import).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, select
from sqlalchemy.engine import Connection, Row

_metadata = MetaData()

modulo = Table(
    "modulo",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(4)),
    Column("nombre", String(100)),
    schema="catalogo",
)

licencia = Table(
    "licencia",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("modulo_id", BigInteger),
    Column("activa_desde", DateTime(timezone=True)),
    Column("activa_hasta", DateTime(timezone=True)),
    schema="tenants",
)


def existe_licencia_vigente(
    conn: Connection, *, tenant_id: int, modulo_codigo: str, ahora: datetime
) -> bool:
    stmt = (
        select(licencia.c.id)
        .select_from(licencia.join(modulo, modulo.c.id == licencia.c.modulo_id))
        .where(
            licencia.c.tenant_id == tenant_id,
            modulo.c.codigo == modulo_codigo,
            licencia.c.activa_desde <= ahora,
            (licencia.c.activa_hasta.is_(None)) | (licencia.c.activa_hasta > ahora),
        )
    )
    return conn.execute(stmt).first() is not None


def listar_licencias_del_tenant(conn: Connection, tenant_id: int) -> list[Row]:
    stmt = (
        select(
            licencia.c.id,
            licencia.c.activa_desde,
            licencia.c.activa_hasta,
            modulo.c.codigo.label("modulo_codigo"),
            modulo.c.nombre.label("modulo_nombre"),
        )
        .select_from(licencia.join(modulo, modulo.c.id == licencia.c.modulo_id))
        .where(licencia.c.tenant_id == tenant_id)
        .order_by(modulo.c.codigo.asc())
    )
    return list(conn.execute(stmt).fetchall())
