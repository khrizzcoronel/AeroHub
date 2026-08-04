"""Lecturas de ops.plantilla_fids y ops.pantalla_fids (Sprint S1.3).

Mismo patron que el resto del proyecto: toda consulta de negocio filtra
por `tabla.c.tenant_id == contexto_tenant_id()` (PN-01) -- salvo
`listar_pantallas_para_monitoreo`, deliberadamente SIN ese filtro: el
monitor de senal (RNF-R04) es un proceso de plataforma sin tenant propio,
analogo a la autenticacion de API Key de S1.2, y debe ejecutarse bajo
`alcance_global()` (ADR-019 G3).
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Row

from .tablas import pantalla_fids, plantilla_fids


def obtener_plantilla_por_id(conn: Connection, plantilla_id: int) -> Row | None:
    stmt = select(plantilla_fids).where(
        plantilla_fids.c.tenant_id == contexto_tenant_id(), plantilla_fids.c.id == plantilla_id
    )
    return conn.execute(stmt).first()


def obtener_pantalla_por_id(conn: Connection, pantalla_id: int) -> Row | None:
    stmt = select(pantalla_fids).where(
        pantalla_fids.c.tenant_id == contexto_tenant_id(), pantalla_fids.c.id == pantalla_id
    )
    return conn.execute(stmt).first()


def obtener_pantalla_por_codigo(conn: Connection, codigo: str) -> Row | None:
    stmt = select(pantalla_fids).where(
        pantalla_fids.c.tenant_id == contexto_tenant_id(), pantalla_fids.c.codigo == codigo
    )
    return conn.execute(stmt).first()


def obtener_ultima_version_plantilla(conn: Connection, nombre: str) -> int | None:
    """Version mas alta ya publicada para `nombre`, o None si es la primera."""
    stmt = select(func.max(plantilla_fids.c.version)).where(
        plantilla_fids.c.tenant_id == contexto_tenant_id(), plantilla_fids.c.nombre == nombre
    )
    return conn.execute(stmt).scalar()


def listar_plantillas(conn: Connection) -> list[Row]:
    """Sprint S1.16 -- solo la ultima version de cada `nombre` (research.md
    Decision 2): `publicar_plantilla` nunca actualiza, cada publicacion es
    un INSERT inmutable con `version` autoincremental por nombre -- listar
    todas mostraria filas casi identicas sin indicar cual es la vigente
    para asignar a una pantalla nueva.

    Anti-join (NOT EXISTS) en vez de JOIN contra un GROUP BY/subquery:
    hallazgo empirico contra MonetDB real (verificado con
    tests/integration/test_fids_administracion.py) -- el patron
    "JOIN (SELECT nombre, max(version) ... GROUP BY nombre)" es rechazado
    con `42000!SELECT: cannot use non GROUP BY column ... without an
    aggregate function`, aunque el GROUP BY vive enteramente dentro de la
    subconsulta. El anti-join es ademas mas portable entre motores.
    """
    otra = plantilla_fids.alias("otra_version")
    existe_version_mas_nueva = (
        select(otra.c.id)
        .where(
            otra.c.tenant_id == plantilla_fids.c.tenant_id,
            otra.c.nombre == plantilla_fids.c.nombre,
            otra.c.version > plantilla_fids.c.version,
        )
        .exists()
    )
    stmt = (
        select(plantilla_fids)
        .where(
            plantilla_fids.c.tenant_id == contexto_tenant_id(),
            ~existe_version_mas_nueva,
        )
        .order_by(plantilla_fids.c.nombre)
    )
    return list(conn.execute(stmt))


def listar_pantallas(conn: Connection) -> list[Row]:
    """Sprint S1.16 -- tablero de telemetria: expone `estado` y
    `ultima_senal_en` tal como el backend ya los mantiene (registrar_heartbeat
    / marcar_pantalla_sin_senal), sin recalcular nada (research.md
    Decision 3).
    """
    stmt = (
        select(pantalla_fids)
        .where(pantalla_fids.c.tenant_id == contexto_tenant_id())
        .order_by(pantalla_fids.c.codigo)
    )
    return list(conn.execute(stmt))


def listar_pantallas_para_monitoreo(conn: Connection) -> list[Row]:
    """SIN filtro de tenant -- uso exclusivo del monitor de senal
    (RNF-R04), que debe evaluar TODAS las pantallas de TODOS los tenants
    en cada ciclo. El llamador DEBE envolver esto en `alcance_global()`.
    """
    stmt = select(pantalla_fids)
    return list(conn.execute(stmt))
