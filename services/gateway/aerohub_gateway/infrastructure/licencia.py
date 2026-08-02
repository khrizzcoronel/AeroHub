"""Lectura de tenants.licencia / catalogo.modulo (Sprint S1.7). Tablas
redeclaradas localmente -- el contrato de independencia de modulos
(.importlinter) prohibe que aerohub_gateway importe infrastructure/ de
aerohub_tenancy, mismo patron que ops.vuelo en gates/ramp (S1.4/S1.5).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    select,
)
from sqlalchemy.engine import Connection

metadata = MetaData()

modulo = Table(
    "modulo",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(4)),
    schema="catalogo",
)

licencia = Table(
    "licencia",
    metadata,
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
    """`activa_desde <= ahora < activa_hasta`, o `activa_hasta` nula
    (vigencia indefinida) -- intervalo cerrado por la izquierda, abierto
    por la derecha (spec.md, Edge Cases)."""
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
