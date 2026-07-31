"""Escritura de tenants.api_key (Sprint S1.2, Plan §8.2, RF-O12).

Solo persiste: domain/ ya valido, application/ ya genero el id, el prefijo
y el hash del secreto. No decide journal/auditoria -- eso lo orquesta
application/, igual que el resto del modulo.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import api_key


def insertar_api_key(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    prefijo: str,
    hash_secreto: str,
    creada_en: datetime,
    expira_en: datetime | None = None,
) -> None:
    conn.execute(
        insert(api_key).values(
            id=id,
            tenant_id=tenant_id,
            prefijo=prefijo,
            hash_secreto=hash_secreto,
            creada_en=creada_en,
            expira_en=expira_en,
            estado="activa",
        )
    )


def actualizar_estado_api_key(conn: Connection, *, id: int, tenant_id: int, estado: str) -> None:
    """El WHERE incluye tenant_id -- no solo por el guardian (ADR-019 G2 lo
    exige de todos modos), sino porque es la propia garantia de que un
    tenant nunca puede revocar la api_key de otro (PN-01).
    """
    conn.execute(
        update(api_key)
        .where(api_key.c.id == id, api_key.c.tenant_id == tenant_id)
        .values(estado=estado)
    )
