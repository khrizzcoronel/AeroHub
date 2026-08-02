"""Objetos Table de SQLAlchemy Core para aerohub_passenger (Sprint S1.6).
Definicion propia, no importada de otro modulo -- el contrato de
independencia de modulos (.importlinter) prohibe que un modulo de negocio
importe infrastructure/ de otro. `tiempo_espera_agregado` vive fisicamente
en el esquema SQL `billing`, pero es propiedad de este modulo (ver
specs/008-billing-passenger-experience/research.md, Decision 3) --
`aerohub_passenger` nunca importa `aerohub_billing`.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Time,
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
    Column("inicio_real", DateTime(timezone=True)),
    Column("fin_real", DateTime(timezone=True)),
    schema="ops",
)

turnaround = Table(
    "turnaround",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_llegada_id", BigInteger),
    Column("vuelo_salida_id", BigInteger),
    Column("inicio_real", DateTime(timezone=True)),
    Column("fin_real", DateTime(timezone=True)),
    schema="rampa",
)

# Fisicamente en el esquema `billing` (SDD-DATA-001 Sec9.8) -- ver
# docstring del modulo.
tiempo_espera_agregado = Table(
    "tiempo_espera_agregado",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("terminal_id", BigInteger),
    Column("fecha", Date),
    Column("franja_inicio", Time),
    Column("franja_fin", Time),
    Column("minutos_estimados", Numeric(6, 2)),
    Column("muestra_n", Integer),
    Column("calculado_en", DateTime(timezone=True)),
    schema="billing",
)
