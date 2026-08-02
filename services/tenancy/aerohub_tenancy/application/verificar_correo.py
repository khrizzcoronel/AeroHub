"""CU-IA07b -- Verificar titularidad del correo (US5, FR-019 apoyo,
RF-IA en spec.md) (Sprint S1.10). Enlace de un solo uso, mismo patron de
token que invitacion/recuperacion.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from aerohub_kernel import ahora_utc, generar_id, hash_credencial
from aerohub_kernel import verificar_credencial as _verificar_credencial

from ..domain import token_canjeable
from ..infrastructure import (
    alcance_global,
    consumir_token,
    contexto_usuario_id,
    enviar_correo,
    insertar_token_acceso,
    invalidar_tokens,
    listar_tokens_previos_no_consumidos,
    marcar_correo_verificado,
    obtener_token_vigente_por_id,
    obtener_usuario_por_id_global,
    registrar_auditoria,
    sesion,
)
from .plantillas_correo import mensaje_verificacion

_MOTIVO_ALCANCE_GLOBAL = "verificacion_correo"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"
_VENCIMIENTO_TOKEN_VERIFICACION = timedelta(hours=24)


class TokenInvalido(Exception):
    """Token de verificacion inexistente, ya consumido o vencido -- 410."""


def solicitar_verificacion() -> None:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        return

    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        fila_usuario = obtener_usuario_por_id_global(conn, usuario_id)
        if fila_usuario is None:
            return

        anteriores = listar_tokens_previos_no_consumidos(
            conn, usuario_id=usuario_id, tipo="verificacion"
        )
        ahora = ahora_utc()
        if anteriores:
            invalidar_tokens(conn, ids=[fila.id for fila in anteriores], invalidado_en=ahora)

        token_id = generar_id()
        token_en_claro = f"{token_id}.{secrets.token_urlsafe(32)}"
        insertar_token_acceso(
            conn,
            id=token_id,
            usuario_id=usuario_id,
            tipo="verificacion",
            hash_token=hash_credencial(token_en_claro),
            expira_en=ahora + _VENCIMIENTO_TOKEN_VERIFICACION,
        )
        email = fila_usuario.email

    mensaje = mensaje_verificacion(destinatario=email, token_en_claro=token_en_claro)
    enviar_correo(mensaje)


def verificar_correo(*, token: str) -> None:
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
            or fila_token.tipo != "verificacion"
            or not _verificar_credencial(token, fila_token.hash_token)
            or not token_canjeable(
                consumido_en=fila_token.consumido_en, expira_en=fila_token.expira_en, ahora=ahora
            )
        ):
            raise TokenInvalido("token de verificacion inexistente, ya usado o vencido")

        consumir_token(conn, id=token_id, consumido_en=ahora)
        marcar_correo_verificado(conn, usuario_id=fila_token.usuario_id, momento=ahora)
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=fila_token.usuario_id,
            operacion="UPDATE",
            valores_nuevos={"email_verificado": True},
        )
