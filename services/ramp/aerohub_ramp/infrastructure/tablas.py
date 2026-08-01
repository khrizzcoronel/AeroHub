"""Objetos Table de SQLAlchemy Core para aerohub_ramp (Sprint S1.5,
SDD-DATA-001 §8). Definicion propia, no importada de aerohub_aodb -- el
contrato de independencia de modulos (.importlinter) prohibe que un modulo
de negocio importe infrastructure/ de otro.
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    MetaData,
    SmallInteger,
    String,
    Table,
)

metadata = MetaData()

vuelo = Table(
    "vuelo",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("aeronave_id", BigInteger),
    Column("numero_vuelo", String(10)),
    Column("sentido", CHAR(1)),
    Column("sta_utc", DateTime(timezone=True)),
    Column("std_utc", DateTime(timezone=True)),
    schema="ops",
)

tipo_tarea = Table(
    "tipo_tarea",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(20)),
    Column("nombre", String(100)),
    Column("duracion_estandar_min", SmallInteger),
    Column("es_ruta_critica", Boolean),
    schema="rampa",
)

tipo_incidencia_rampa = Table(
    "tipo_incidencia_rampa",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(20)),
    Column("descripcion", String(150)),
    schema="rampa",
)

turnaround = Table(
    "turnaround",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_llegada_id", BigInteger),
    Column("vuelo_salida_id", BigInteger),
    Column("aeronave_id", BigInteger),
    Column("inicio_previsto", DateTime(timezone=True)),
    Column("fin_previsto", DateTime(timezone=True)),
    Column("inicio_real", DateTime(timezone=True)),
    Column("fin_real", DateTime(timezone=True)),
    Column("estado", String(20)),
    schema="rampa",
)

tarea_turnaround = Table(
    "tarea_turnaround",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("turnaround_id", BigInteger),
    Column("tipo_tarea_id", BigInteger),
    Column("agente_usuario_id", BigInteger),
    Column("inicio_real", DateTime(timezone=True)),
    Column("fin_real", DateTime(timezone=True)),
    Column("estado", String(20)),
    schema="rampa",
)

incidencia_rampa = Table(
    "incidencia_rampa",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("tarea_turnaround_id", BigInteger),
    Column("tipo_incidencia_id", BigInteger),
    Column("descripcion", String(300)),
    Column("severidad", String(10)),
    Column("detectada_en", DateTime(timezone=True)),
    Column("resuelta_en", DateTime(timezone=True)),
    Column("resuelta_por_usuario_id", BigInteger),
    schema="rampa",
)
