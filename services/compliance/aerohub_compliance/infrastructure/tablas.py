"""Objetos Table de SQLAlchemy Core para aerohub_compliance (Sprint S1.7,
SDD-DATA-001 Sec10). `compliance.log_auditoria` NO se redeclara aqui --
vive en `aerohub_repository.audit` (paquete transversal), no es propiedad
de este modulo.
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Column,
    Date,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

tipo_incidente = Table(
    "tipo_incidente",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(30)),
    Column("descripcion", String(200)),
    Column("categoria", String(50)),
    schema="compliance",
)

incidente_seguridad = Table(
    "incidente_seguridad",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("tipo_incidente_id", BigInteger),
    Column("descripcion", String(500)),
    Column("severidad", String(10)),
    Column("detectado_en", DateTime(timezone=True)),
    Column("reportado_por_usuario_id", BigInteger),
    Column("estado", String(20)),
    schema="compliance",
)

tipo_reporte_regulatorio = Table(
    "tipo_reporte_regulatorio",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(30)),
    Column("nombre", String(150)),
    Column("periodicidad", String(20)),
    Column("autoridad", String(20)),
    schema="compliance",
)

reporte_dgac = Table(
    "reporte_dgac",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("tipo_reporte_id", BigInteger),
    Column("periodo_inicio", Date),
    Column("periodo_fin", Date),
    Column("contenido_ref", String(500)),
    Column("hash_contenido", CHAR(64)),
    Column("emitido_por_usuario_id", BigInteger),
    Column("emitido_en", DateTime(timezone=True)),
    schema="compliance",
)

acceso_auditor = Table(
    "acceso_auditor",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("auditor_usuario_id", BigInteger),
    Column("otorgado_por_usuario_id", BigInteger),
    Column("inicio", DateTime(timezone=True)),
    Column("fin", DateTime(timezone=True)),
    Column("alcance_json", JSON),
    Column("motivo", String(300)),
    schema="compliance",
)

post_mortem = Table(
    "post_mortem",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("incidente_ref", String(100)),
    Column("severidad", String(10)),
    Column("causa_raiz", Text),
    Column("estado", String(20)),
    Column("iniciado_en", DateTime(timezone=True)),
    Column("publicado_en", DateTime(timezone=True)),
    Column("tiempo_resolucion_min", BigInteger),
    schema="compliance",
)

post_mortem_accion = Table(
    "post_mortem_accion",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("post_mortem_id", BigInteger),
    Column("descripcion", String(300)),
    Column("responsable_usuario_id", BigInteger),
    Column("ticket_ref", String(50)),
    Column("estado", String(20)),
    Column("vence_en", DateTime(timezone=True)),
    Column("completada_en", DateTime(timezone=True)),
    schema="compliance",
)

control_soc2 = Table(
    "control_soc2",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo_control", String(20)),
    Column("nombre", String(200)),
    Column("categoria", String(50)),
    schema="compliance",
)

evidencia_soc2 = Table(
    "evidencia_soc2",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("control_soc2_id", BigInteger),
    Column("tenant_id", BigInteger),
    Column("periodo_inicio", Date),
    Column("periodo_fin", Date),
    Column("referencia_log_id", BigInteger),
    Column("ruta_artefacto", String(500)),
    Column("hash_artefacto", CHAR(64)),
    Column("generado_en", DateTime(timezone=True)),
    schema="compliance",
)
