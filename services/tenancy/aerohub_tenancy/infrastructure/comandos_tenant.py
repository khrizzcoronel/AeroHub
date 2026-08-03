"""Escritura de tenants.tenant para el workpanel (post S1.13). Solo
persiste -- domain/ ya valido la transicion de estado, application/
orquesta journal/auditoria.
"""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.engine import Connection

from .tablas import tenant


def actualizar_tenant(
    conn: Connection, *, id: int, razon_social: str, plan_id: int, es_sandbox: bool
) -> None:
    conn.execute(
        update(tenant)
        .where(tenant.c.id == id)
        .values(razon_social=razon_social, plan_id=plan_id, es_sandbox=es_sandbox)
    )


def cambiar_estado_tenant(conn: Connection, *, id: int, estado_nuevo: str) -> None:
    conn.execute(update(tenant).where(tenant.c.id == id).values(estado=estado_nuevo))
