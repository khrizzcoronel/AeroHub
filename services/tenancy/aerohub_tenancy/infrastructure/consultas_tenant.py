"""Consultas de tenants.tenant para el workpanel (post S1.13). `tenant`
es alcance G1 'interno' (sin columna tenant_id, ver alcances.py) -- listar
todos los tenants es la operacion normal de `role_platform_admin` sobre su
propio esquema, no requiere `alcance_global()` (esa excepcion es solo para
cuando el actor NO tiene el rol/tenant en contexto que la consulta
necesita; aqui SI lo tiene: su propio rol vigente ya trae el SET ROLE con
los grants de la matriz 4.3.1).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Connection, Row

from .tablas import tenant


def listar_tenants(conn: Connection) -> list[Row]:
    return list(conn.execute(select(tenant).order_by(tenant.c.creado_en.desc())))


def obtener_tenant_por_id(conn: Connection, tenant_id: int) -> Row | None:
    return conn.execute(select(tenant).where(tenant.c.id == tenant_id)).first()
