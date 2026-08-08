"""Consultas de identidad y acceso (Sprint S1.10). A diferencia de
`consultas.py` (obtener_usuario_por_id, tenant-scoped), estas corren bajo
`alcance_global()` -- se invocan ANTES de conocer el tenant de quien
llama (login, canje de token, resolucion de rol vigente).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Row

from ..domain import RolAsignado
from .tablas import (
    intento_acceso,
    invitacion,
    rol,
    sesion,
    tenant,
    token_acceso,
    usuario,
    usuario_rol,
)


def obtener_usuario_por_email(conn: Connection, email: str) -> Row | None:
    """Global -- el correo es unico en todo el sistema desde la migracion
    de S1.10 (research.md Decision 2), no hace falta tenant_id."""
    return conn.execute(select(usuario).where(usuario.c.email == email)).first()


def obtener_usuario_por_id_global(conn: Connection, usuario_id: int) -> Row | None:
    return conn.execute(select(usuario).where(usuario.c.id == usuario_id)).first()


def listar_roles_vigentes_del_usuario(conn: Connection, usuario_id: int) -> list[RolAsignado]:
    stmt = (
        select(rol.c.id, rol.c.codigo, rol.c.nombre, usuario_rol.c.expira_en)
        .select_from(usuario_rol.join(rol, rol.c.id == usuario_rol.c.rol_id))
        .where(usuario_rol.c.usuario_id == usuario_id)
    )
    return [
        RolAsignado(
            rol_id=fila.id, codigo=fila.codigo, nombre=fila.nombre, expira_en=fila.expira_en
        )
        for fila in conn.execute(stmt)
    ]


def contar_intentos_fallidos_recientes(
    conn: Connection, usuario_id: int, *, desde: datetime
) -> int:
    stmt = select(func.count()).where(
        intento_acceso.c.usuario_id == usuario_id,
        intento_acceso.c.resultado != "exitoso",
        intento_acceso.c.ocurrido_en >= desde,
    )
    return conn.execute(stmt).scalar_one()


def listar_usuarios_del_tenant(conn: Connection, tenant_id: int) -> list[Row]:
    stmt = (
        select(
            usuario.c.id,
            usuario.c.email,
            usuario.c.nombre,
            usuario.c.estado,
            usuario.c.creado_en,
            usuario.c.ultimo_acceso_en,
            # Hallazgo 3 de la auditoria de la capa operativa (2026-08-08).
            usuario.c.aerolinea_id,
            rol.c.codigo.label("rol_codigo"),
            rol.c.nombre.label("rol_nombre"),
        )
        .select_from(
            usuario.outerjoin(usuario_rol, usuario_rol.c.usuario_id == usuario.c.id).outerjoin(
                rol, rol.c.id == usuario_rol.c.rol_id
            )
        )
        .where(usuario.c.tenant_id == tenant_id)
        .order_by(usuario.c.creado_en.desc())
    )
    return list(conn.execute(stmt).fetchall())


def obtener_sesion_por_id(conn: Connection, sesion_id: int) -> Row | None:
    return conn.execute(select(sesion).where(sesion.c.id == sesion_id)).first()


def obtener_token_vigente_por_id(conn: Connection, token_id: int) -> Row | None:
    return conn.execute(select(token_acceso).where(token_acceso.c.id == token_id)).first()


def listar_tokens_previos_no_consumidos(
    conn: Connection, *, usuario_id: int | None, tipo: str
) -> list[Row]:
    stmt = select(token_acceso).where(
        token_acceso.c.usuario_id == usuario_id,
        token_acceso.c.tipo == tipo,
        token_acceso.c.consumido_en.is_(None),
    )
    return list(conn.execute(stmt))


def obtener_invitacion_por_token_id(conn: Connection, token_acceso_id: int) -> Row | None:
    return conn.execute(
        select(invitacion).where(invitacion.c.token_acceso_id == token_acceso_id)
    ).first()


def obtener_tenant_por_id_global(conn: Connection, tenant_id: int) -> Row | None:
    return conn.execute(select(tenant).where(tenant.c.id == tenant_id)).first()


def obtener_rol_por_codigo(conn: Connection, codigo: str) -> Row | None:
    return conn.execute(select(rol).where(rol.c.codigo == codigo)).first()
