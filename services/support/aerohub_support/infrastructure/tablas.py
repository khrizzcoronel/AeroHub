"""Objetos Table de SQLAlchemy Core para aerohub_support (Sprint S1.8,
SDD-DATA-001 Sec11). `catalogo.modulo` se redeclara localmente (patron ya
usado en aerohub_gates/aerohub_ramp/aerohub_gateway): el contrato de
independencia de modulos (.importlinter) prohibe importar la definicion de
otro modulo, y `changelog_item.modulo_id` necesita referenciarla.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

categoria_ticket = Table(
    "categoria_ticket",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(30)),
    Column("nombre", String(100)),
    schema="support",
)

ticket = Table(
    "ticket",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("categoria_id", BigInteger),
    Column("creado_por_usuario_id", BigInteger),
    Column("asignado_a_usuario_id", BigInteger),
    Column("severidad", String(10)),
    Column("estado", String(20)),
    Column("asunto", String(200)),
    Column("creado_en", DateTime(timezone=True)),
    Column("primera_respuesta_en", DateTime(timezone=True)),
    Column("resuelto_en", DateTime(timezone=True)),
    Column("sla_objetivo_min", Integer),
    schema="support",
)

ticket_mensaje = Table(
    "ticket_mensaje",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("ticket_id", BigInteger),
    Column("autor_usuario_id", BigInteger),
    Column("cuerpo", Text),
    Column("enviado_en", DateTime(timezone=True)),
    Column("es_interno", Boolean),
    schema="support",
)

articulo_kb = Table(
    "articulo_kb",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("titulo", String(200)),
    Column("cuerpo", Text),
    Column("version", Integer),
    Column("estado", String(20)),
    Column("publicado_en", DateTime(timezone=True)),
    Column("autor_usuario_id", BigInteger),
    Column("embedding_ref", String(200)),
    schema="support",
)

etiqueta = Table(
    "etiqueta",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("nombre", String(50)),
    schema="support",
)

articulo_kb_etiqueta = Table(
    "articulo_kb_etiqueta",
    metadata,
    Column("articulo_id", BigInteger, primary_key=True),
    Column("etiqueta_id", BigInteger, primary_key=True),
    schema="support",
)

changelog = Table(
    "changelog",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("version_producto", String(20)),
    Column("resumen", String(500)),
    Column("publicado_en", DateTime(timezone=True)),
    schema="support",
)

changelog_item = Table(
    "changelog_item",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("changelog_id", BigInteger),
    Column("modulo_id", BigInteger),
    Column("tipo_cambio", String(20)),
    Column("descripcion", String(500)),
    schema="support",
)

# Redeclaracion local de catalogo.modulo (ya definida en
# aerohub_gateway.infrastructure.tablas / aerohub_gates / aerohub_ramp) --
# solo para poder construir un join/FK tipado desde este modulo sin importar
# infrastructure/ de otro (.importlinter).
modulo = Table(
    "modulo",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(4)),
    Column("nombre", String(100)),
    Column("departamento_id", BigInteger),
    schema="catalogo",
)
