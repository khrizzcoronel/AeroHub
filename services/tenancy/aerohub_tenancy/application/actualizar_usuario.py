"""Workpanel de usuarios (post-S1.13): ver detalle, editar rol y cambiar
estado -- espejo de `gestionar_tenant.py`, mismo criterio (domain valida
primero, mutacion + journal + auditoria en la misma transaccion, PN-01
para "no encontrado").
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import ahora_utc

from ..domain import TransicionUsuarioInvalida, validar_transicion_estado_usuario
from .gestionar_invitacion import RolDestinoInvalido
from ..infrastructure import (
    actualizar_estado_usuario as _actualizar_estado_usuario,
)
from ..infrastructure import (
    contexto_usuario_id,
    escribir_journal,
    obtener_rol_por_codigo,
    reasignar_rol_usuario,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from ..infrastructure import contexto_tenant_id as _contexto_tenant_id
from ..infrastructure import obtener_usuario_con_rol_por_id as _obtener_usuario_con_rol_por_id


class UsuarioDelTenantNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class UsuarioDetalle:
    id: int
    email: str
    nombre: str
    estado: str
    rol_codigo: str | None
    rol_nombre: str | None


def _fila_a_detalle(f: object) -> UsuarioDetalle:
    return UsuarioDetalle(
        id=f.id,  # type: ignore[attr-defined]
        email=f.email,  # type: ignore[attr-defined]
        nombre=f.nombre,  # type: ignore[attr-defined]
        estado=f.estado,  # type: ignore[attr-defined]
        rol_codigo=f.rol_codigo,  # type: ignore[attr-defined]
        rol_nombre=f.rol_nombre,  # type: ignore[attr-defined]
    )


def obtener_usuario_del_tenant(usuario_id: int) -> UsuarioDetalle:
    with sesion() as conn:
        fila = _obtener_usuario_con_rol_por_id(conn, usuario_id)
    if fila is None:
        raise UsuarioDelTenantNoEncontrado(f"usuario {usuario_id} no encontrado")
    return _fila_a_detalle(fila)


@reintentar_en_conflicto()
def actualizar_rol_usuario(*, usuario_id: int, rol_codigo: str) -> UsuarioDetalle:
    tenant_id = _contexto_tenant_id()
    quien_edita = contexto_usuario_id()
    ahora = ahora_utc()

    with sesion() as conn:
        fila_actual = _obtener_usuario_con_rol_por_id(conn, usuario_id)
        if fila_actual is None:
            raise UsuarioDelTenantNoEncontrado(f"usuario {usuario_id} no encontrado")

        fila_rol = obtener_rol_por_codigo(conn, rol_codigo)
        if fila_rol is None:
            raise RolDestinoInvalido(f"rol {rol_codigo!r} no existe")

        reasignar_rol_usuario(
            conn,
            usuario_id=usuario_id,
            rol_id_nuevo=fila_rol.id,
            otorgado_por=quien_edita,
            otorgado_en=ahora,
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario_rol",
            operacion="UPDATE",
            clave_primaria={"usuario_id": usuario_id},
            payload={"rol_codigo": rol_codigo},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario_rol",
            registro_id=usuario_id,
            operacion="UPDATE",
            valores_anteriores={"rol_codigo": fila_actual.rol_codigo},
            valores_nuevos={"rol_codigo": rol_codigo},
            tenant_id=tenant_id,
        )

    return obtener_usuario_del_tenant(usuario_id)


@reintentar_en_conflicto()
def cambiar_estado_usuario(*, usuario_id: int, estado_nuevo: str) -> UsuarioDetalle:
    tenant_id = _contexto_tenant_id()

    with sesion() as conn:
        fila_actual = _obtener_usuario_con_rol_por_id(conn, usuario_id)
        if fila_actual is None:
            raise UsuarioDelTenantNoEncontrado(f"usuario {usuario_id} no encontrado")

        try:
            validar_transicion_estado_usuario(fila_actual.estado, estado_nuevo)
        except TransicionUsuarioInvalida:
            raise

        _actualizar_estado_usuario(conn, id=usuario_id, estado_nuevo=estado_nuevo)
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario",
            operacion="UPDATE",
            clave_primaria={"id": usuario_id},
            payload={"estado": estado_nuevo},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=usuario_id,
            operacion="UPDATE",
            valores_anteriores={"estado": fila_actual.estado},
            valores_nuevos={"estado": estado_nuevo},
            tenant_id=tenant_id,
        )

    return obtener_usuario_del_tenant(usuario_id)
