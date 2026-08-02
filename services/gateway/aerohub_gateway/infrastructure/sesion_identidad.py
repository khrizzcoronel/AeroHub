"""Lectura de tenants.sesion / tenants.usuario.debe_cambiar_password
(Sprint S1.10, research.md Decision 5). Tablas redeclaradas localmente --
mismo patron que tenants.licencia en licencia.py (S1.7): el contrato de
independencia de modulos (.importlinter) prohibe que aerohub_gateway
importe infrastructure/ de aerohub_tenancy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, MetaData, Table, select
from sqlalchemy.engine import Connection

metadata = MetaData()

sesion_tabla = Table(
    "sesion",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("usuario_id", BigInteger),
    Column("expira_en", DateTime(timezone=True)),
    Column("revocada_en", DateTime(timezone=True)),
    schema="tenants",
)

usuario_tabla = Table(
    "usuario",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("debe_cambiar_password", Boolean),
    schema="tenants",
)


@dataclass(frozen=True, slots=True)
class EstadoSesion:
    vigente: bool
    debe_cambiar_password: bool


def obtener_estado_sesion(conn: Connection, *, sesion_id: int, ahora: datetime) -> EstadoSesion:
    """Una sola consulta (join) para no sumar un segundo *round trip* al
    ya aceptado por `verificar_licencia` (research.md Decision 5, costo
    declarado explicitamente). Sesion inexistente (P5 prohibe DELETE
    sobre esta tabla, no deberia pasar) se trata como no vigente."""
    stmt = (
        select(
            sesion_tabla.c.revocada_en,
            sesion_tabla.c.expira_en,
            usuario_tabla.c.debe_cambiar_password,
        )
        .select_from(
            sesion_tabla.join(usuario_tabla, usuario_tabla.c.id == sesion_tabla.c.usuario_id)
        )
        .where(sesion_tabla.c.id == sesion_id)
    )
    fila = conn.execute(stmt).first()
    if fila is None:
        return EstadoSesion(vigente=False, debe_cambiar_password=False)
    vigente = fila.revocada_en is None and ahora < fila.expira_en
    return EstadoSesion(vigente=vigente, debe_cambiar_password=bool(fila.debe_cambiar_password))
