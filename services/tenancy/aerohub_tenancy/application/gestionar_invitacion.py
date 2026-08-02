"""CU-IA04/CU-IA05 -- Invitar personas a la organizacion, exclusivo
`role_tenant_admin` (US4, FR-015..FR-020) (Sprint S1.10).

`invitar_usuario` envia el correo ANTES de persistir nada (contracts/
auth-api.md: "el correo no pudo enviarse; la invitacion NO queda
registrada") -- evita depender de que un rollback de transaccion
deshaga un efecto externo que ya ocurrio (el correo, si salio, salio).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from aerohub_kernel import ahora_utc, generar_id, hash_credencial
from aerohub_kernel import verificar_credencial as _verificar_credencial

from ..domain import token_canjeable, validar_password
from ..infrastructure import (
    alcance_global,
    consumir_token,
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
    enviar_correo,
    escribir_journal,
    insertar_invitacion,
    insertar_token_acceso,
    insertar_usuario_invitado,
    insertar_usuario_rol,
    marcar_invitacion_aceptada,
    obtener_invitacion_por_token_id,
    obtener_rol_por_codigo,
    obtener_tenant_por_id_global,
    obtener_token_vigente_por_id,
    obtener_usuario_por_email,
    obtener_usuario_por_id_global,
    registrar_auditoria,
    sesion,
)
from .plantillas_correo import mensaje_invitacion

_ROL_AUTORIZADO = "role_tenant_admin"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"
_MOTIVO_ALCANCE_GLOBAL = "gestion_invitacion"
_VENCIMIENTO_INVITACION = timedelta(days=7)


class RolNoAutorizado(Exception):
    pass


class CorreoYaRegistrado(Exception):
    pass


class RolDestinoInvalido(Exception):
    pass


class TokenInvalido(Exception):
    """Token de invitacion inexistente, ya consumido o vencido -- 410."""


@dataclass(frozen=True, slots=True)
class ResultadoInvitar:
    invitacion_id: int
    expira_en: datetime


def invitar_usuario(*, email: str, rol_codigo: str) -> ResultadoInvitar:
    if contexto_rol_actor() != _ROL_AUTORIZADO:
        raise RolNoAutorizado("solo role_tenant_admin puede invitar usuarios a su tenant")
    tenant_id = contexto_tenant_id()
    invitado_por_usuario_id = contexto_usuario_id()
    if invitado_por_usuario_id is None:
        # role_tenant_admin siempre es una sesion humana (JWT de login,
        # nunca API Key) -- llegar aqui sin usuario_id es un estado
        # inconsistente, no un caso de negocio a manejar.
        raise RolNoAutorizado("la identidad autenticada no tiene un usuario asociado")
    ahora = ahora_utc()

    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        if obtener_usuario_por_email(conn, email) is not None:
            raise CorreoYaRegistrado(f"ya existe una cuenta con el correo {email!r}")

        fila_rol = obtener_rol_por_codigo(conn, rol_codigo)
        if fila_rol is None:
            raise RolDestinoInvalido(f"rol {rol_codigo!r} no existe")

        fila_tenant = obtener_tenant_por_id_global(conn, tenant_id)
        fila_invitador = (
            obtener_usuario_por_id_global(conn, invitado_por_usuario_id)
            if invitado_por_usuario_id is not None
            else None
        )

    # Generar el token y enviar el correo ANTES de persistir -- si el
    # envio falla, no queda ninguna invitacion "fantasma" en la base.
    token_id = generar_id()
    token_en_claro = f"{token_id}.{secrets.token_urlsafe(32)}"
    mensaje = mensaje_invitacion(
        destinatario=email,
        token_en_claro=token_en_claro,
        invitado_por_nombre=fila_invitador.nombre if fila_invitador else "Un administrador",
        tenant_razon_social=fila_tenant.razon_social if fila_tenant else "tu organizacion",
    )
    enviar_correo(mensaje)  # EnvioDeCorreoFallo se propaga tal cual -- 502 en el router

    invitacion_id = generar_id()
    expira_en = ahora + _VENCIMIENTO_INVITACION
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        insertar_token_acceso(
            conn,
            id=token_id,
            usuario_id=None,
            tipo="invitacion",
            hash_token=hash_credencial(token_en_claro),
            expira_en=expira_en,
        )
        insertar_invitacion(
            conn,
            id=invitacion_id,
            tenant_id=tenant_id,
            email=email,
            rol_id=fila_rol.id,
            invitado_por_usuario_id=invitado_por_usuario_id,
            token_acceso_id=token_id,
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="invitacion",
            operacion="INSERT",
            clave_primaria={"id": invitacion_id},
            payload={"id": invitacion_id, "email": email, "rol_codigo": rol_codigo},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="invitacion",
            registro_id=invitacion_id,
            operacion="INSERT",
            valores_nuevos={"email": email, "rol_codigo": rol_codigo},
            tenant_id=tenant_id,
        )

    return ResultadoInvitar(invitacion_id=invitacion_id, expira_en=expira_en)


@dataclass(frozen=True, slots=True)
class ResultadoAceptarInvitacion:
    usuario_id: int
    tenant_id: int


def aceptar_invitacion(*, token: str, nombre: str, password: str) -> ResultadoAceptarInvitacion:
    validar_password(password)

    try:
        token_id_str, _secreto = token.split(".", 1)
        token_id = int(token_id_str)
    except (ValueError, AttributeError):
        raise TokenInvalido("token con formato invalido") from None

    ahora = ahora_utc()
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        fila_token = obtener_token_vigente_por_id(conn, token_id)
        if (
            fila_token is None
            or fila_token.tipo != "invitacion"
            or not _verificar_credencial(token, fila_token.hash_token)
            or not token_canjeable(
                consumido_en=fila_token.consumido_en, expira_en=fila_token.expira_en, ahora=ahora
            )
        ):
            raise TokenInvalido("token de invitacion inexistente, ya usado o vencido")

        fila_invitacion = obtener_invitacion_por_token_id(conn, token_id)
        if fila_invitacion is None or fila_invitacion.estado != "pendiente":
            raise TokenInvalido("invitacion inexistente o ya resuelta")

        usuario_id = generar_id()
        insertar_usuario_invitado(
            conn,
            id=usuario_id,
            tenant_id=fila_invitacion.tenant_id,
            email=fila_invitacion.email,
            hash_credencial=hash_credencial(password),
            nombre=nombre,
            momento=ahora,
        )
        insertar_usuario_rol(
            conn,
            usuario_id=usuario_id,
            rol_id=fila_invitacion.rol_id,
            otorgado_por=fila_invitacion.invitado_por_usuario_id,
            otorgado_en=ahora,
        )
        consumir_token(conn, id=token_id, consumido_en=ahora)
        marcar_invitacion_aceptada(conn, id=fila_invitacion.id, aceptada_en=ahora)
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario",
            operacion="INSERT",
            clave_primaria={"id": usuario_id},
            payload={"id": usuario_id, "email": fila_invitacion.email},
            tenant_id=fila_invitacion.tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=usuario_id,
            operacion="INSERT",
            valores_nuevos={"email": fila_invitacion.email, "via": "invitacion"},
            tenant_id=fila_invitacion.tenant_id,
        )

    return ResultadoAceptarInvitacion(usuario_id=usuario_id, tenant_id=fila_invitacion.tenant_id)
