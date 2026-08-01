"""Objetos Table de SQLAlchemy Core para aerohub_gates (Sprint S1.4,
SDD-DATA-001 §7.5). Definicion propia, no importada de aerohub_aodb --
el contrato de independencia de modulos (.importlinter) prohibe que un
modulo de negocio importe infrastructure/ de otro.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    MetaData,
    Numeric,
    String,
    Table,
)

metadata = MetaData()

terminal = Table(
    "terminal",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("codigo", String(10)),
    Column("nombre", String(100)),
    schema="ops",
)

puerta = Table(
    "puerta",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("terminal_id", BigInteger),
    Column("codigo", String(10)),
    Column("tipo", String(20)),
    Column("envergadura_max_m", Numeric(5, 2)),
    Column("tiene_pasarela", Boolean),
    schema="ops",
)

vuelo = Table(
    "vuelo",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("aerolinea_id", BigInteger),
    Column("aeronave_id", BigInteger),
    Column("numero_vuelo", String(10)),
    Column("sta_utc", DateTime(timezone=True)),
    Column("std_utc", DateTime(timezone=True)),
    schema="ops",
)

asignacion_puerta = Table(
    "asignacion_puerta",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    Column("puerta_id", BigInteger),
    Column("inicio_previsto", DateTime(timezone=True)),
    Column("fin_previsto", DateTime(timezone=True)),
    Column("inicio_real", DateTime(timezone=True)),
    Column("fin_real", DateTime(timezone=True)),
    Column("asignado_por_usuario_id", BigInteger),
    Column("asignado_en", DateTime(timezone=True)),
    Column("estado", String(20)),
    schema="ops",
)
