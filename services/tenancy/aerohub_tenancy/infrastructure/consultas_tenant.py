"""Consultas de tenants.tenant para el workpanel (post S1.13). `tenant`
es alcance G1 'interno' (sin columna tenant_id, ver alcances.py) -- listar
todos los tenants es la operacion normal de `role_platform_admin` sobre su
propio esquema, no requiere `alcance_global()` (esa excepcion es solo para
cuando el actor NO tiene el rol/tenant en contexto que la consulta
necesita; aqui SI lo tiene: su propio rol vigente ya trae el SET ROLE con
los grants de la matriz 4.3.1).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Row

from .tablas import tenant, usuario


def listar_tenants(conn: Connection) -> list[Row]:
    return list(conn.execute(select(tenant).order_by(tenant.c.creado_en.desc())))


def obtener_tenant_por_id(conn: Connection, tenant_id: int) -> Row | None:
    return conn.execute(select(tenant).where(tenant.c.id == tenant_id)).first()


def existe_tenant_codigo(conn: Connection, codigo: str) -> bool:
    stmt = select(tenant.c.id).where(func.upper(tenant.c.codigo) == codigo.strip().upper())
    return conn.execute(stmt).first() is not None


def existe_usuario_email(conn: Connection, email: str) -> bool:
    stmt = select(usuario.c.id).where(func.lower(usuario.c.email) == email.strip().lower())
    return conn.execute(stmt).first() is not None
