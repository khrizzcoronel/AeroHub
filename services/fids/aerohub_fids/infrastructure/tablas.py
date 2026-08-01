"""Objetos Table de SQLAlchemy Core para ops.plantilla_fids y
ops.pantalla_fids (SDD-DATA-001 §7.7-7.8, Sprint S1.3).
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
)

metadata = MetaData()

plantilla_fids = Table(
    "plantilla_fids",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("nombre", String(100)),
    Column("definicion_json", JSON),
    Column("version", Integer),
    Column("vigente_desde", DateTime(timezone=True)),
    Column("creada_por_usuario_id", BigInteger),
    schema="ops",
)

pantalla_fids = Table(
    "pantalla_fids",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("terminal_id", BigInteger),
    Column("codigo", String(20)),
    Column("ubicacion_descripcion", String(150)),
    Column("plantilla_id", BigInteger),
    Column("ultima_senal_en", DateTime(timezone=True)),
    Column("version_firmware", String(20)),
    Column("estado", String(20)),
    schema="ops",
)
