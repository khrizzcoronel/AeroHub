"""Objetos Table de SQLAlchemy Core para el nucleo de ops (Sprint S1.1,
SDD-DATA-001 §7). Una sola definicion por tabla, compartida entre
consultas.py y comandos.py.
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Numeric,
    SmallInteger,
    String,
    Table,
)
from sqlalchemy import (
    MetaData as _MetaData,
)

metadata = _MetaData()

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
    Column("tipo_vuelo_id", BigInteger),
    Column("fecha_operacion", Date),
    Column("sentido", CHAR(1)),
    Column("aeropuerto_origen_id", BigInteger),
    Column("aeropuerto_destino_id", BigInteger),
    Column("sta_utc", DateTime(timezone=True)),
    Column("std_utc", DateTime(timezone=True)),
    Column("eta_utc", DateTime(timezone=True)),
    Column("etd_utc", DateTime(timezone=True)),
    Column("ata_utc", DateTime(timezone=True)),
    Column("atd_utc", DateTime(timezone=True)),
    Column("pax_estimado", SmallInteger),
    Column("creado_en", DateTime(timezone=True)),
    schema="ops",
)

vuelo_estado = Table(
    "vuelo_estado",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    Column("estado_id", BigInteger),
    Column("registrado_en", DateTime(timezone=True)),
    Column("registrado_por_usuario_id", BigInteger),
    Column("origen_cambio", String(20)),
    schema="ops",
)

vuelo_demora = Table(
    "vuelo_demora",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    Column("motivo_demora_id", BigInteger),
    Column("minutos", SmallInteger),
    Column("registrado_en", DateTime(timezone=True)),
    Column("registrado_por_usuario_id", BigInteger),
    schema="ops",
)

# Vista, no tabla -- pero SQLAlchemy Core no distingue: un Table() que
# describe sus columnas basta para construir SELECT contra ella. Se
# prefiere reutilizar la vista (10_ops.sql) antes que duplicar la logica
# de "estado mas reciente" aqui en Python.
v_vuelo_estado_actual = Table(
    "v_vuelo_estado_actual",
    metadata,
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    Column("estado_id", BigInteger),
    Column("registrado_en", DateTime(timezone=True)),
    Column("registrado_por_usuario_id", BigInteger),
    Column("origen_cambio", String(20)),
    schema="ops",
)
