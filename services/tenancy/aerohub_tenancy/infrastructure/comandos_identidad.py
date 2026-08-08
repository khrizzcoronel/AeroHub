"""Escritura de identidad y acceso (Sprint S1.10). Solo persiste --
domain/ ya valido, application/ ya genero ids y hashes; no decide
journal/auditoria, eso lo orquesta application/.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from .tablas import intento_acceso, invitacion, sesion, token_acceso, usuario, usuario_rol


def insertar_intento_acceso(
    conn: Connection,
    *,
    id: int,
    email_intentado: str,
    usuario_id: int | None,
    resultado: str,
    ip_origen: str | None,
) -> None:
    conn.execute(
        insert(intento_acceso).values(
            id=id,
            email_intentado=email_intentado,
            usuario_id=usuario_id,
            resultado=resultado,
            ip_origen=ip_origen,
        )
    )


def insertar_sesion(
    conn: Connection, *, id: int, usuario_id: int, expira_en: datetime, ip_origen: str | None
) -> None:
    conn.execute(
        insert(sesion).values(
            id=id, usuario_id=usuario_id, expira_en=expira_en, ip_origen=ip_origen
        )
    )


def revocar_sesion(conn: Connection, *, id: int, motivo: str, revocada_en: datetime) -> None:
    conn.execute(
        update(sesion)
        .where(sesion.c.id == id, sesion.c.revocada_en.is_(None))
        .values(revocada_en=revocada_en, motivo_revocacion=motivo)
    )


def revocar_sesiones_del_usuario(
    conn: Connection,
    *,
    usuario_id: int,
    motivo: str,
    revocada_en: datetime,
    excepto_sesion_id: int | None = None,
) -> None:
    condiciones = [sesion.c.usuario_id == usuario_id, sesion.c.revocada_en.is_(None)]
    if excepto_sesion_id is not None:
        condiciones.append(sesion.c.id != excepto_sesion_id)
    conn.execute(
        update(sesion)
        .where(*condiciones)
        .values(revocada_en=revocada_en, motivo_revocacion=motivo)
    )


def actualizar_ultimo_acceso(conn: Connection, *, usuario_id: int, momento: datetime) -> None:
    conn.execute(
        update(usuario).where(usuario.c.id == usuario_id).values(ultimo_acceso_en=momento)
    )


def fijar_bloqueo(conn: Connection, *, usuario_id: int, bloqueado_hasta: datetime) -> None:
    conn.execute(
        update(usuario).where(usuario.c.id == usuario_id).values(bloqueado_hasta=bloqueado_hasta)
    )


def marcar_password_cambiada(conn: Connection, *, usuario_id: int, hash_credencial: str) -> None:
    conn.execute(
        update(usuario)
        .where(usuario.c.id == usuario_id)
        .values(hash_credencial=hash_credencial, debe_cambiar_password=False)
    )


def marcar_correo_verificado(conn: Connection, *, usuario_id: int, momento: datetime) -> None:
    conn.execute(
        update(usuario).where(usuario.c.id == usuario_id).values(email_verificado_en=momento)
    )


def insertar_token_acceso(
    conn: Connection,
    *,
    id: int,
    usuario_id: int | None,
    tipo: str,
    hash_token: str,
    expira_en: datetime,
) -> None:
    conn.execute(
        insert(token_acceso).values(
            id=id, usuario_id=usuario_id, tipo=tipo, hash_token=hash_token, expira_en=expira_en
        )
    )


def consumir_token(conn: Connection, *, id: int, consumido_en: datetime) -> None:
    conn.execute(
        update(token_acceso)
        .where(token_acceso.c.id == id, token_acceso.c.consumido_en.is_(None))
        .values(consumido_en=consumido_en)
    )


def invalidar_tokens(conn: Connection, *, ids: list[int], invalidado_en: datetime) -> None:
    if not ids:
        return
    conn.execute(
        update(token_acceso)
        .where(token_acceso.c.id.in_(ids), token_acceso.c.consumido_en.is_(None))
        .values(consumido_en=invalidado_en)
    )


def insertar_invitacion(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    email: str,
    rol_id: int,
    invitado_por_usuario_id: int,
    token_acceso_id: int,
) -> None:
    conn.execute(
        insert(invitacion).values(
            id=id,
            tenant_id=tenant_id,
            email=email,
            rol_id=rol_id,
            invitado_por_usuario_id=invitado_por_usuario_id,
            token_acceso_id=token_acceso_id,
            estado="pendiente",
        )
    )


def marcar_invitacion_aceptada(conn: Connection, *, id: int, aceptada_en: datetime) -> None:
    conn.execute(
        update(invitacion)
        .where(invitacion.c.id == id)
        .values(estado="aceptada", aceptada_en=aceptada_en)
    )


def insertar_usuario_invitado(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    email: str,
    hash_credencial: str,
    nombre: str,
    momento: datetime,
) -> None:
    conn.execute(
        insert(usuario).values(
            id=id,
            tenant_id=tenant_id,
            email=email,
            hash_credencial=hash_credencial,
            nombre=nombre,
            estado="activo",
            mfa_habilitado=False,
            debe_cambiar_password=False,
            email_verificado_en=momento,
        )
    )


def insertar_usuario_rol(
    conn: Connection, *, usuario_id: int, rol_id: int, otorgado_por: int, otorgado_en: datetime
) -> None:
    conn.execute(
        insert(usuario_rol).values(
            usuario_id=usuario_id, rol_id=rol_id, otorgado_por=otorgado_por, otorgado_en=otorgado_en
        )
    )


def reasignar_rol_usuario(
    conn: Connection,
    *,
    usuario_id: int,
    rol_id_nuevo: int,
    otorgado_por: int | None,
    otorgado_en: datetime,
) -> None:
    """Reemplaza el rol vigente del usuario -- se asume un solo rol activo
    por usuario en la practica (ver docstring de consultas_identidad.py::
    listar_roles_vigentes_del_usuario), aunque el esquema (PK compuesta
    usuario_id+rol_id) permitiria varios.

    UPSERT (SELECT + UPDATE o INSERT), NO delete+insert (hallazgo
    empirico 2026-08-05): `role_tenant_admin` solo tiene GRANT
    SELECT/INSERT/UPDATE sobre `tenants.usuario_rol`
    (92_grants_tenants.sql), sin DELETE -- el DELETE+INSERT original
    era inalcanzable para el unico rol que usa este workpanel desde la
    UI, con `42000!DELETE FROM: insufficient privileges`. Un UPDATE
    puro (sin verificar existencia primero) tampoco alcanza: un usuario
    sin fila previa en usuario_rol (dato real encontrado en el tenant
    canario) deja el UPDATE afectando 0 filas -- "exito" silencioso sin
    asignar ningun rol. Por eso se verifica primero con SELECT.
    `expira_en` se resetea a NULL para igualar el comportamiento del
    INSERT original (rol nuevo, sin vencimiento)."""
    existe = conn.execute(
        select(usuario_rol.c.usuario_id).where(usuario_rol.c.usuario_id == usuario_id)
    ).first()
    if existe is not None:
        conn.execute(
            update(usuario_rol)
            .where(usuario_rol.c.usuario_id == usuario_id)
            .values(
                rol_id=rol_id_nuevo,
                otorgado_por=otorgado_por,
                otorgado_en=otorgado_en,
                expira_en=None,
            )
        )
    else:
        conn.execute(
            insert(usuario_rol).values(
                usuario_id=usuario_id,
                rol_id=rol_id_nuevo,
                otorgado_por=otorgado_por,
                otorgado_en=otorgado_en,
            )
        )


def actualizar_aerolinea_usuario(
    conn: Connection, *, id: int, tenant_id: int, aerolinea_id: int | None
) -> None:
    """Asigna (o desasigna, con None) la aerolinea de un usuario -- hallazgo
    3 de la auditoria de la capa operativa (2026-08-08).

    Filtra por tenant_id explicito por el mismo motivo que
    `actualizar_estado_usuario` mas abajo: sin el, el guardian G2 rechaza
    el UPDATE con TenantScopeViolation."""
    conn.execute(
        update(usuario)
        .where(usuario.c.id == id, usuario.c.tenant_id == tenant_id)
        .values(aerolinea_id=aerolinea_id)
    )


def actualizar_estado_usuario(
    conn: Connection, *, id: int, tenant_id: int, estado_nuevo: str
) -> None:
    """A diferencia de fijar_bloqueo/marcar_password_cambiada/etc. (que
    corren bajo alcance_global() durante login/recuperacion, antes de que
    exista contexto de tenant), esto se invoca desde una sesion ya
    autenticada de un tenant admin -- PN-02 exige filtrar por tenant_id
    explicito, no confiar solo en el id. Hallazgo empirico (2026-08-05):
    sin este filtro, el guardian (ADR-019 G2) rechaza el UPDATE con
    TenantScopeViolation -- "cambiar estado de usuario" era inalcanzable
    desde el workpanel."""
    conn.execute(
        update(usuario)
        .where(usuario.c.id == id, usuario.c.tenant_id == tenant_id)
        .values(estado=estado_nuevo)
    )
