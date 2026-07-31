"""Primera funcion de lectura real del esquema tenants -- sirve de ejemplo
canonico de como escribir una consulta que el guardian (ADR-019 G2) acepte,
y de sujeto de prueba para la suite cruzada por introspeccion (G4,
tests/cross_tenant/).

El patron obligatorio: TODA consulta sobre una tabla de alcance 'tenant'
incluye `tabla.c.tenant_id == contexto_tenant_id()` en su WHERE, sin
excepcion -- no porque el guardian lo exija (lo exige), sino porque es la
unica forma correcta de que "obtener por id" no cruce tenants: si el id
pedido pertenece a otro tenant, la fila simplemente no aparece (0 filas),
en vez de lanzar una excepcion que distinga "no existe" de "no es tuyo"
(mismo principio que PN-01: 404, no 403).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, MetaData, String, Table, select
from sqlalchemy.engine import Connection, Row

from ..contexto import contexto_tenant_id

_metadata = MetaData()

usuario = Table(
    "usuario",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("email", String(254)),
    Column("nombre", String(150)),
    Column("estado", String(20)),
    Column("mfa_habilitado", Boolean),
    schema="tenants",
)


def obtener_usuario_por_id(conn: Connection, usuario_id: int) -> Row | None:
    """None si el usuario no existe O pertenece a otro tenant -- ambos
    casos son indistinguibles desde afuera, por diseno (ver docstring del
    modulo).
    """
    stmt = select(
        usuario.c.id,
        usuario.c.email,
        usuario.c.nombre,
        usuario.c.estado,
        usuario.c.mfa_habilitado,
    ).where(usuario.c.tenant_id == contexto_tenant_id(), usuario.c.id == usuario_id)
    return conn.execute(stmt).first()
