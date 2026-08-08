"""Consultas de tenants.usuario -- movido desde packages/repository en
S1.1 (ver alcances.py: ese paquete ya no posee logica de acceso a datos
por dominio, solo lo transversal). Sirve de ejemplo canonico de como
escribir una consulta que el guardian (ADR-019 G2) acepte, y de sujeto de
prueba para la suite cruzada por introspeccion (G4, tests/cross_tenant/).

El patron obligatorio: TODA consulta sobre una tabla de alcance 'tenant'
incluye `tabla.c.tenant_id == contexto_tenant_id()` en su WHERE, sin
excepcion -- no porque el guardian lo exija (lo exige), sino porque es la
unica forma correcta de que "obtener por id" no cruce tenants: si el id
pedido pertenece a otro tenant, la fila simplemente no aparece (0 filas),
en vez de lanzar una excepcion que distinga "no existe" de "no es tuyo"
(mismo principio que PN-01: 404, no 403).
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import select
from sqlalchemy.engine import Connection, Row

from .tablas import api_key, rol, usuario, usuario_rol


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


def obtener_usuario_con_rol_por_id(conn: Connection, usuario_id: int) -> Row | None:
    """Version de detalle de `obtener_usuario_por_id`, con el rol vigente
    incluido -- misma indistincion "no existe" vs. "es de otro tenant"
    (PN-01, ver docstring del modulo)."""
    stmt = (
        select(
            usuario.c.id,
            usuario.c.email,
            usuario.c.nombre,
            usuario.c.estado,
            usuario.c.creado_en,
            usuario.c.ultimo_acceso_en,
            # Hallazgo 3 de la auditoria de la capa operativa (2026-08-08):
            # el workpanel de usuarios necesita mostrar/editar la aerolinea.
            usuario.c.aerolinea_id,
            rol.c.codigo.label("rol_codigo"),
            rol.c.nombre.label("rol_nombre"),
        )
        .select_from(
            usuario.outerjoin(usuario_rol, usuario_rol.c.usuario_id == usuario.c.id).outerjoin(
                rol, rol.c.id == usuario_rol.c.rol_id
            )
        )
        .where(usuario.c.tenant_id == contexto_tenant_id(), usuario.c.id == usuario_id)
    )
    return conn.execute(stmt).first()


def obtener_api_key_por_id(conn: Connection, api_key_id: int) -> Row | None:
    """Tenant-scoped -- uso normal de gestion (CU: role_tenant_admin revoca
    SU PROPIA api_key, PN-01 aplica igual que a cualquier otro recurso).

    La busqueda POR PREFIJO (sin filtro de tenant, necesaria para que
    services/gateway autentique una API Key sin conocer aun su tenant_id)
    NO vive aqui: aerohub_gateway no puede importar aerohub_tenancy
    (contrato de independencia de modulos, .importlinter), asi que declara
    su propia Table de solo lectura sobre tenants.api_key
    (aerohub_gateway/infrastructure/api_key.py) -- el guardian de G1/G2
    resuelve el alcance por (esquema, tabla), no por que modulo declaro el
    objeto Table, asi que ambas declaraciones conviven sin conflicto.
    """
    stmt = select(api_key).where(
        api_key.c.tenant_id == contexto_tenant_id(), api_key.c.id == api_key_id
    )
    return conn.execute(stmt).first()


def listar_api_keys_del_tenant(conn: Connection) -> list[Row]:
    stmt = (
        select(api_key)
        .where(api_key.c.tenant_id == contexto_tenant_id())
        .order_by(api_key.c.creada_en.desc())
    )
    return list(conn.execute(stmt).fetchall())
