"""Lecturas de support.* (Sprint S1.8). Toda consulta sobre `ticket`
(alcance='tenant') filtra por `contexto_tenant_id()`, salvo las variantes
`_global` -- validas UNICAMENTE bajo `alcance_global()` (role_support,
research.md Decision 5), donde el guardian G2 ya no exige ese filtro.
`ticket_mensaje` (alcance='interno', sin tenant_id propio) se aisla
transitivamente via `ticket_id`, cuyo padre ya valido el llamador.
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import and_, or_, select
from sqlalchemy.engine import Connection, Row

from .tablas import (
    articulo_kb,
    articulo_kb_etiqueta,
    categoria_ticket,
    changelog,
    changelog_item,
    etiqueta,
    modulo,
    ticket,
    ticket_mensaje,
)


def obtener_categoria_ticket_por_id(conn: Connection, categoria_id: int) -> Row | None:
    stmt = select(categoria_ticket).where(categoria_ticket.c.id == categoria_id)
    return conn.execute(stmt).first()


def obtener_ticket_por_id_de_tenant(conn: Connection, *, ticket_id: int) -> Row | None:
    """Uso de un actor de tenant: PN-01, nunca revela un ticket ajeno."""
    stmt = select(ticket).where(
        ticket.c.tenant_id == contexto_tenant_id(), ticket.c.id == ticket_id
    )
    return conn.execute(stmt).first()


def obtener_ticket_por_id_global(conn: Connection, *, ticket_id: int) -> Row | None:
    """Uso EXCLUSIVO de role_support bajo alcance_global() -- sin filtro de
    tenant (atiende tickets de cualquier tenant, research.md Decision 5)."""
    stmt = select(ticket).where(ticket.c.id == ticket_id)
    return conn.execute(stmt).first()


def listar_tickets_de_tenant(conn: Connection) -> list[Row]:
    stmt = select(ticket).where(ticket.c.tenant_id == contexto_tenant_id())
    return list(conn.execute(stmt))


def listar_tickets_global(
    conn: Connection, *, estado: str | None = None, severidad: str | None = None
) -> list[Row]:
    """Uso EXCLUSIVO de role_support bajo alcance_global()."""
    condiciones = []
    if estado is not None:
        condiciones.append(ticket.c.estado == estado)
    if severidad is not None:
        condiciones.append(ticket.c.severidad == severidad)
    stmt = select(ticket)
    if condiciones:
        stmt = stmt.where(and_(*condiciones))
    return list(conn.execute(stmt))


def listar_mensajes_de_ticket(conn: Connection, *, ticket_id: int) -> list[Row]:
    stmt = (
        select(ticket_mensaje)
        .where(ticket_mensaje.c.ticket_id == ticket_id)
        .order_by(ticket_mensaje.c.enviado_en)
    )
    return list(conn.execute(stmt))


def obtener_version_maxima_articulo(conn: Connection, *, titulo: str) -> int:
    stmt = select(articulo_kb.c.version).where(articulo_kb.c.titulo == titulo)
    filas = conn.execute(stmt).all()
    return max((f.version for f in filas), default=0)


def obtener_articulo_kb_por_id(conn: Connection, articulo_id: int) -> Row | None:
    stmt = select(articulo_kb).where(
        articulo_kb.c.id == articulo_id, articulo_kb.c.estado == "publicado"
    )
    return conn.execute(stmt).first()


def obtener_etiqueta_por_nombre(conn: Connection, nombre: str) -> Row | None:
    stmt = select(etiqueta).where(etiqueta.c.nombre == nombre)
    return conn.execute(stmt).first()


def _join_articulo_kb_etiqueta():
    return articulo_kb_etiqueta.join(etiqueta, etiqueta.c.id == articulo_kb_etiqueta.c.etiqueta_id)


def listar_etiquetas_de_articulo(conn: Connection, *, articulo_id: int) -> list[str]:
    stmt = (
        select(etiqueta.c.nombre)
        .select_from(_join_articulo_kb_etiqueta())
        .where(articulo_kb_etiqueta.c.articulo_id == articulo_id)
    )
    return [f.nombre for f in conn.execute(stmt)]


def buscar_articulos_kb(
    conn: Connection, *, texto: str | None = None, etiqueta_nombre: str | None = None
) -> list[Row]:
    """FR-014: ILIKE sobre titulo/cuerpo y/o etiqueta -- solo articulos
    publicados (SC-005; un archivado deja de aparecer, spec.md Edge Cases)."""
    columnas = (
        articulo_kb.c.id,
        articulo_kb.c.titulo,
        articulo_kb.c.cuerpo,
        articulo_kb.c.version,
        articulo_kb.c.publicado_en,
    )
    stmt = select(*columnas).where(articulo_kb.c.estado == "publicado")
    if etiqueta_nombre is not None:
        stmt = stmt.where(
            articulo_kb.c.id.in_(
                select(articulo_kb_etiqueta.c.articulo_id)
                .select_from(_join_articulo_kb_etiqueta())
                .where(etiqueta.c.nombre == etiqueta_nombre)
            )
        )
    if texto is not None:
        patron = f"%{texto}%"
        stmt = stmt.where(
            or_(articulo_kb.c.titulo.ilike(patron), articulo_kb.c.cuerpo.ilike(patron))
        )
    stmt = stmt.distinct()
    return list(conn.execute(stmt))


def obtener_modulo_por_codigo(conn: Connection, codigo: str) -> Row | None:
    stmt = select(modulo).where(modulo.c.codigo == codigo)
    return conn.execute(stmt).first()


def listar_changelog(conn: Connection) -> list[Row]:
    stmt = select(changelog).order_by(changelog.c.publicado_en.desc())
    return list(conn.execute(stmt))


def listar_items_de_changelog(conn: Connection, *, changelog_id: int) -> list[Row]:
    stmt = select(changelog_item).where(changelog_item.c.changelog_id == changelog_id)
    return list(conn.execute(stmt))
