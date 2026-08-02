"""Objetos Table de SQLAlchemy Core para aerohub_billing (Sprint S1.6,
SDD-DATA-001 Sec9). Definicion propia, no importada de otro modulo -- el
contrato de independencia de modulos (.importlinter) prohibe que un modulo
de negocio importe infrastructure/ de otro.
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    BigInteger,
    Column,
    Date,
    DateTime,
    MetaData,
    Numeric,
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
    Column("aerolinea_id", BigInteger),
    Column("fecha_operacion", Date),
    Column("pax_estimado", SmallInteger),
    schema="ops",
)

concepto_cargo = Table(
    "concepto_cargo",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(30)),
    Column("nombre", String(150)),
    Column("unidad_medida", String(20)),
    Column("base_calculo", String(30)),
    schema="billing",
)

tarifario = Table(
    "tarifario",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("nombre", String(100)),
    Column("moneda", CHAR(3)),
    Column("vigente_desde", Date),
    Column("vigente_hasta", Date),
    Column("estado", String(20)),
    Column("creado_por_usuario_id", BigInteger),
    schema="billing",
)

tarifario_concepto = Table(
    "tarifario_concepto",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tarifario_id", BigInteger),
    Column("concepto_cargo_id", BigInteger),
    Column("tarifa_unitaria", Numeric(14, 4)),
    Column("monto_minimo", Numeric(14, 2)),
    Column("monto_maximo", Numeric(14, 2)),
    schema="billing",
)

cargo_aeronautico = Table(
    "cargo_aeronautico",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    Column("concepto_cargo_id", BigInteger),
    Column("tarifario_concepto_id", BigInteger),
    Column("cantidad", Numeric(12, 2)),
    Column("tarifa_aplicada", Numeric(14, 4)),
    Column("monto_calculado", Numeric(14, 2)),
    Column("calculado_en", DateTime(timezone=True)),
    schema="billing",
)

factura = Table(
    "factura",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("aerolinea_id", BigInteger),
    Column("periodo_inicio", Date),
    Column("periodo_fin", Date),
    Column("moneda", CHAR(3)),
    Column("estado", String(20)),
    Column("emitida_en", DateTime(timezone=True)),
    Column("vence_en", DateTime(timezone=True)),
    schema="billing",
)

factura_linea = Table(
    "factura_linea",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("factura_id", BigInteger),
    Column("cargo_aeronautico_id", BigInteger),
    Column("descripcion", String(200)),
    Column("cantidad", Numeric(12, 2)),
    Column("precio_unitario", Numeric(14, 4)),
    Column("monto", Numeric(14, 2)),
    schema="billing",
)

conciliacion_pax = Table(
    "conciliacion_pax",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    Column("periodo", String(7)),
    Column("pax_reportado_aerolinea", SmallInteger),
    Column("pax_registrado_sistema", SmallInteger),
    Column("fuente_reporte", String(50)),
    Column("conciliado_en", DateTime(timezone=True)),
    Column("conciliado_por_usuario_id", BigInteger),
    schema="billing",
)
