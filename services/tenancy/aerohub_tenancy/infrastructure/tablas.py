"""Objetos Table de SQLAlchemy Core para tenants.tenant y tenants.usuario
(SDD-DATA-001 §6.3, §6.5). Compartidos entre consultas.py y
provisionamiento.py -- una sola definicion por tabla, coherente con el
resto del modulo.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger as BigInt,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
)

metadata = MetaData()

tenant = Table(
    "tenant",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("codigo", String(30)),
    Column("razon_social", String(200)),
    Column("aeropuerto_id", BigInt),
    Column("plan_id", BigInt),
    Column("es_sandbox", Boolean),
    Column("estado", String(20)),
    Column("creado_en", DateTime(timezone=True)),
    schema="tenants",
)

usuario = Table(
    "usuario",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("tenant_id", BigInt),
    Column("email", String(254)),
    Column("hash_credencial", String(255)),
    Column("nombre", String(150)),
    Column("estado", String(20)),
    Column("mfa_habilitado", Boolean),
    Column("creado_en", DateTime(timezone=True)),
    schema="tenants",
)
