"""Informes operativos de Tenancy (Sprint S1.18, RF-I01/RF-I02): tenants
con filtros, y tenants agrupados por (plan, estado) con conteo de
usuarios activos y licencias vigentes. Alcance 'interno' (sin filtro de
tenant, igual que `listar_tenants` desde S1.14) -- es un listado de
plataforma, no de un tenant especifico. GROUP BY usa un alias de tabla
(hallazgo empirico de MonetDB, ver CLAUDE.md).
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc
from sqlalchemy import func, or_, select
from sqlalchemy.engine import Connection, Row

from .licencia import licencia
from .tablas import tenant, usuario


def listar_tenants_informe(conn: Connection, *, estado: str | None = None) -> list[Row]:
    condiciones = []
    if estado is not None:
        condiciones.append(tenant.c.estado == estado)
    stmt = select(tenant).where(*condiciones).order_by(tenant.c.codigo)
    return list(conn.execute(stmt))


def agrupar_tenants_por_plan_estado(conn: Connection) -> list[Row]:
    ahora = ahora_utc()
    t = tenant.alias("t")
    u = usuario.alias("u")
    lic = licencia.alias("lic")

    usuarios_activos = (
        select(func.count())
        .select_from(u)
        .where(u.c.tenant_id == t.c.id, u.c.estado == "activo")
        .correlate(t)
        .scalar_subquery()
    )
    licencias_vigentes = (
        select(func.count())
        .select_from(lic)
        .where(
            lic.c.tenant_id == t.c.id,
            or_(lic.c.activa_hasta.is_(None), lic.c.activa_hasta > ahora),
        )
        .correlate(t)
        .scalar_subquery()
    )
    stmt = (
        select(
            t.c.plan_id,
            t.c.estado,
            func.count().label("cantidad_tenants"),
            func.sum(usuarios_activos).label("usuarios_activos"),
            func.sum(licencias_vigentes).label("licencias_vigentes"),
        )
        .group_by(t.c.plan_id, t.c.estado)
        .order_by(t.c.plan_id, t.c.estado)
    )
    return list(conn.execute(stmt))
