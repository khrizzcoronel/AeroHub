"""Escritura de support.* (Sprint S1.8). `actualizar_estado_ticket` y
`fijar_primera_respuesta` son de uso EXCLUSIVO de role_support bajo
`alcance_global()` (research.md Decision 5) -- sin filtro de tenant en el
WHERE: el guardian G2 no lo exige mientras ese alcance este activo, y
role_support (rol de plataforma) no tiene un `tenant_id` propio en su JWT
del cual filtrar.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import (
    articulo_kb,
    articulo_kb_etiqueta,
    changelog,
    changelog_item,
    etiqueta,
    ticket,
    ticket_mensaje,
)


def insertar_ticket(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    categoria_id: int,
    creado_por_usuario_id: int,
    severidad: str,
    asunto: str,
    sla_objetivo_min: int,
) -> None:
    conn.execute(
        insert(ticket).values(
            id=id,
            tenant_id=tenant_id,
            categoria_id=categoria_id,
            creado_por_usuario_id=creado_por_usuario_id,
            severidad=severidad,
            estado="abierto",
            asunto=asunto,
            sla_objetivo_min=sla_objetivo_min,
        )
    )


def actualizar_estado_ticket(
    conn: Connection, *, id: int, estado: str, resuelto_en: datetime | None = None
) -> None:
    valores: dict[str, object] = {"estado": estado}
    if resuelto_en is not None:
        valores["resuelto_en"] = resuelto_en
    conn.execute(update(ticket).where(ticket.c.id == id).values(**valores))


def fijar_primera_respuesta(conn: Connection, *, id: int, primera_respuesta_en: datetime) -> None:
    """FR-003: condicional -- solo si aun es NULL, para que un segundo
    mensaje de role_support nunca la modifique."""
    conn.execute(
        update(ticket)
        .where(ticket.c.id == id, ticket.c.primera_respuesta_en.is_(None))
        .values(primera_respuesta_en=primera_respuesta_en)
    )


def insertar_ticket_mensaje(
    conn: Connection,
    *,
    id: int,
    ticket_id: int,
    autor_usuario_id: int,
    cuerpo: str,
    es_interno: bool,
) -> None:
    conn.execute(
        insert(ticket_mensaje).values(
            id=id,
            ticket_id=ticket_id,
            autor_usuario_id=autor_usuario_id,
            cuerpo=cuerpo,
            es_interno=es_interno,
        )
    )


def insertar_articulo_kb(
    conn: Connection,
    *,
    id: int,
    titulo: str,
    cuerpo: str,
    version: int,
    autor_usuario_id: int,
) -> None:
    conn.execute(
        insert(articulo_kb).values(
            id=id,
            titulo=titulo,
            cuerpo=cuerpo,
            version=version,
            estado="borrador",
            autor_usuario_id=autor_usuario_id,
        )
    )


def publicar_articulo_kb(conn: Connection, *, id: int, publicado_en: datetime) -> None:
    conn.execute(
        update(articulo_kb)
        .where(articulo_kb.c.id == id)
        .values(estado="publicado", publicado_en=publicado_en)
    )


def insertar_etiqueta(conn: Connection, *, id: int, nombre: str) -> None:
    conn.execute(insert(etiqueta).values(id=id, nombre=nombre))


def asociar_etiqueta_articulo(conn: Connection, *, articulo_id: int, etiqueta_id: int) -> None:
    conn.execute(
        insert(articulo_kb_etiqueta).values(articulo_id=articulo_id, etiqueta_id=etiqueta_id)
    )


def insertar_changelog(
    conn: Connection, *, id: int, version_producto: str, resumen: str, publicado_en: datetime
) -> None:
    conn.execute(
        insert(changelog).values(
            id=id, version_producto=version_producto, resumen=resumen, publicado_en=publicado_en
        )
    )


def insertar_changelog_item(
    conn: Connection,
    *,
    id: int,
    changelog_id: int,
    modulo_id: int,
    tipo_cambio: str,
    descripcion: str,
) -> None:
    conn.execute(
        insert(changelog_item).values(
            id=id,
            changelog_id=changelog_id,
            modulo_id=modulo_id,
            tipo_cambio=tipo_cambio,
            descripcion=descripcion,
        )
    )
