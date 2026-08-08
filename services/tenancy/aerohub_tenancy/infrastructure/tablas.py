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
    Numeric,
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
    # String(30), no 20: sigue al DDL (chk_usuario_estado permite
    # 'eliminado_logicamente', 21 caracteres) -- la declaracion habia
    # quedado desalineada al ensanchar la columna real.
    Column("estado", String(30)),
    Column("mfa_habilitado", Boolean),
    # Hallazgo 3 de la auditoria de la capa operativa (2026-08-08): vinculo
    # usuario -> aerolinea que hace representable "solo sus itinerarios".
    Column("aerolinea_id", BigInt),
    Column("creado_en", DateTime(timezone=True)),
    # Columnas del ciclo de vida de la credencial, agregadas en S1.10
    # (data-model.md): `ultimo_acceso_en` ya existia sin usar desde S0.2.
    Column("email_verificado_en", DateTime(timezone=True)),
    Column("debe_cambiar_password", Boolean),
    Column("bloqueado_hasta", DateTime(timezone=True)),
    Column("ultimo_acceso_en", DateTime(timezone=True)),
    schema="tenants",
)

rol = Table(
    "rol",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("codigo", String(50)),
    Column("nombre", String(100)),
    Column("alcance", String(20)),
    schema="tenants",
)

usuario_rol = Table(
    "usuario_rol",
    metadata,
    Column("usuario_id", BigInt, primary_key=True),
    Column("rol_id", BigInt, primary_key=True),
    Column("otorgado_por", BigInt),
    Column("otorgado_en", DateTime(timezone=True)),
    Column("expira_en", DateTime(timezone=True)),
    schema="tenants",
)

sesion = Table(
    "sesion",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("usuario_id", BigInt),
    Column("emitida_en", DateTime(timezone=True)),
    Column("expira_en", DateTime(timezone=True)),
    Column("revocada_en", DateTime(timezone=True)),
    Column("motivo_revocacion", String(30)),
    Column("ip_origen", String(45)),
    schema="tenants",
)

token_acceso = Table(
    "token_acceso",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("usuario_id", BigInt),
    Column("tipo", String(20)),
    Column("hash_token", String(255)),
    Column("emitido_en", DateTime(timezone=True)),
    Column("expira_en", DateTime(timezone=True)),
    Column("consumido_en", DateTime(timezone=True)),
    schema="tenants",
)

invitacion = Table(
    "invitacion",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("tenant_id", BigInt),
    Column("email", String(254)),
    Column("rol_id", BigInt),
    Column("invitado_por_usuario_id", BigInt),
    Column("token_acceso_id", BigInt),
    Column("estado", String(20)),
    Column("creada_en", DateTime(timezone=True)),
    Column("aceptada_en", DateTime(timezone=True)),
    schema="tenants",
)

intento_acceso = Table(
    "intento_acceso",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("email_intentado", String(254)),
    Column("usuario_id", BigInt),
    Column("resultado", String(20)),
    Column("ocurrido_en", DateTime(timezone=True)),
    Column("ip_origen", String(45)),
    schema="tenants",
)

api_key = Table(
    "api_key",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("tenant_id", BigInt),
    Column("prefijo", String(12)),
    Column("hash_secreto", String(255)),
    Column("creada_en", DateTime(timezone=True)),
    Column("rotada_en", DateTime(timezone=True)),
    Column("expira_en", DateTime(timezone=True)),
    Column("estado", String(20)),
    schema="tenants",
)

# Sprint "workpanel de tenants" (post S1.13): catalogo de planes -- ya
# existia la tabla desde S0.2, nunca se habia declarado su Table() ni
# expuesto por API (aprovisionar_tenant solo recibia plan_id ya elegido
# de memoria). Alcance G1 'interno' (ya registrado en alcances.py).
plan = Table(
    "plan",
    metadata,
    Column("id", BigInt, primary_key=True),
    Column("codigo", String(30)),
    Column("nombre", String(100)),
    Column("tarifa_base_mensual", Numeric(12, 2)),
    Column("moneda", String(3)),
    Column("activo", Boolean),
    schema="tenants",
)
