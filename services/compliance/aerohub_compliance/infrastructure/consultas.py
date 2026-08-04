"""Lecturas de compliance.* (Sprint S1.7). Toda consulta sobre una tabla
alcance='tenant' filtra por `contexto_tenant_id()`, sin excepcion
(PN-01). `post_mortem_accion` (alcance='interno', sin tenant_id propio) se
aisla transitivamente vía `post_mortem_id`, cuyo padre ya se valido contra
el tenant del contexto por el llamador.
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import select
from sqlalchemy.engine import Connection, Row

from .tablas import (
    acceso_auditor,
    evidencia_soc2,
    incidente_seguridad,
    post_mortem,
    post_mortem_accion,
    reporte_dgac,
    tipo_incidente,
)


def obtener_tipo_incidente_por_id(conn: Connection, tipo_incidente_id: int) -> Row | None:
    stmt = select(tipo_incidente).where(tipo_incidente.c.id == tipo_incidente_id)
    return conn.execute(stmt).first()


def listar_incidentes(conn: Connection) -> list[Row]:
    stmt = select(incidente_seguridad).where(
        incidente_seguridad.c.tenant_id == contexto_tenant_id()
    )
    return list(conn.execute(stmt))


def obtener_post_mortem_por_id(conn: Connection, post_mortem_id: int) -> Row | None:
    stmt = select(post_mortem).where(
        post_mortem.c.tenant_id == contexto_tenant_id(), post_mortem.c.id == post_mortem_id
    )
    return conn.execute(stmt).first()


def listar_acciones_de_post_mortem(conn: Connection, *, post_mortem_id: int) -> list[Row]:
    stmt = select(post_mortem_accion).where(post_mortem_accion.c.post_mortem_id == post_mortem_id)
    return list(conn.execute(stmt))


def obtener_post_mortem_accion_por_id(conn: Connection, accion_id: int) -> Row | None:
    stmt = select(post_mortem_accion).where(post_mortem_accion.c.id == accion_id)
    return conn.execute(stmt).first()


def listar_post_mortems(conn: Connection) -> list[Row]:
    """Sprint S1.19 -- listado que faltaba desde S1.7 (solo existia
    obtener_post_mortem_por_id, sin forma de descubrir los ids)."""
    stmt = select(post_mortem).where(post_mortem.c.tenant_id == contexto_tenant_id())
    return list(conn.execute(stmt))


def listar_reportes_dgac(conn: Connection) -> list[Row]:
    stmt = select(reporte_dgac).where(reporte_dgac.c.tenant_id == contexto_tenant_id())
    return list(conn.execute(stmt))


def listar_accesos_auditor(conn: Connection) -> list[Row]:
    stmt = select(acceso_auditor).where(acceso_auditor.c.tenant_id == contexto_tenant_id())
    return list(conn.execute(stmt))


def listar_evidencia_soc2(conn: Connection) -> list[Row]:
    stmt = select(evidencia_soc2).where(evidencia_soc2.c.tenant_id == contexto_tenant_id())
    return list(conn.execute(stmt))
