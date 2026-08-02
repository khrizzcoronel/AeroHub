"""CU-IA03/CU-IA06 -- Cambio de contrasena obligatorio (US3, FR-012/FR-013)
y recuperacion autoservicio (US6, FR-021/FR-022) (Sprint S1.10).

Como `iniciar_sesion`/`consultar_perfil`, corre bajo `alcance_global()`:
quien cambia su propia contrasena ya esta autenticado, pero las tablas
que hay que tocar (`sesion`, `token_acceso`) son alcance `'interno'` con
grants exclusivos de `role_platform_admin` (99_grants_identidad.sql) --
ningun otro rol de tenant tiene privilegio de motor sobre ellas. Mismo
patron ya establecido, no una excepcion nueva.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from aerohub_kernel import ahora_utc, generar_id, hash_credencial
from aerohub_kernel import verificar_credencial as _verificar_credencial

from ..domain import token_canjeable, validar_password
from ..infrastructure import (
    alcance_global,
    consumir_token,
    contexto_usuario_id,
    enviar_correo,
    insertar_token_acceso,
    invalidar_tokens,
    listar_tokens_previos_no_consumidos,
    marcar_password_cambiada,
    obtener_token_vigente_por_id,
    obtener_usuario_por_email,
    obtener_usuario_por_id_global,
    registrar_auditoria,
    revocar_sesiones_del_usuario,
    sesion,
)
from .plantillas_correo import mensaje_recuperacion

_MOTIVO_CAMBIAR_PASSWORD = "cambio_password_propio"
_MOTIVO_RECUPERACION = "recuperacion_password"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"
_VENCIMIENTO_TOKEN_RECUPERACION = timedelta(hours=1)


class PasswordActualIncorrecta(Exception):
    pass


class TokenInvalido(Exception):
    """Token de recuperacion inexistente, ya consumido o vencido -- 410,
    igual criterio en toda la familia de tokens de un solo uso."""


def cambiar_password(
    *, sesion_id_actual: int | None, password_actual: str, password_nueva: str
) -> None:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise PasswordActualIncorrecta("no hay usuario en el contexto de la peticion")
    validar_password(password_nueva)  # PasswordInvalida se propaga tal cual -- 422 en el router

    with (
        alcance_global(motivo=_MOTIVO_CAMBIAR_PASSWORD, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        fila_usuario = obtener_usuario_por_id_global(conn, usuario_id)
        if fila_usuario is None or not _verificar_credencial(
            password_actual, fila_usuario.hash_credencial
        ):
            raise PasswordActualIncorrecta("contrasena actual incorrecta")

        marcar_password_cambiada(
            conn, usuario_id=usuario_id, hash_credencial=hash_credencial(password_nueva)
        )
        revocar_sesiones_del_usuario(
            conn,
            usuario_id=usuario_id,
            motivo="cambio_password_propio",
            revocada_en=ahora_utc(),
            excepto_sesion_id=sesion_id_actual,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=usuario_id,
            operacion="UPDATE",
            valores_nuevos={"debe_cambiar_password": False},
            tenant_id=fila_usuario.tenant_id,
        )


def solicitar_recuperacion(*, email: str) -> None:
    """FR-021: SIEMPRE termina en 202 desde el router, exista o no la
    cuenta -- esta funcion simplemente no hace nada (sin lanzar) si el
    correo no corresponde a ningun usuario, en vez de reportarlo."""
    mensaje = None
    with (
        alcance_global(motivo=_MOTIVO_RECUPERACION, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        fila_usuario = obtener_usuario_por_email(conn, email)
        if fila_usuario is not None:
            anteriores = listar_tokens_previos_no_consumidos(
                conn, usuario_id=fila_usuario.id, tipo="recuperacion"
            )
            ahora = ahora_utc()
            if anteriores:
                invalidar_tokens(conn, ids=[fila.id for fila in anteriores], invalidado_en=ahora)

            token_id = generar_id()
            token_en_claro = f"{token_id}.{secrets.token_urlsafe(32)}"
            insertar_token_acceso(
                conn,
                id=token_id,
                usuario_id=fila_usuario.id,
                tipo="recuperacion",
                hash_token=hash_credencial(token_en_claro),
                expira_en=ahora + _VENCIMIENTO_TOKEN_RECUPERACION,
            )
            mensaje = mensaje_recuperacion(destinatario=email, token_en_claro=token_en_claro)

    # Enviar FUERA de la transaccion -- un correo que tarda no debe
    # mantener abierta una conexion de base de datos.
    if mensaje is not None:
        enviar_correo(mensaje)


def restablecer_password(*, token: str, password_nueva: str) -> None:
    validar_password(password_nueva)

    try:
        token_id_str, _secreto = token.split(".", 1)
        token_id = int(token_id_str)
    except (ValueError, AttributeError):
        raise TokenInvalido("token con formato invalido") from None

    ahora = ahora_utc()
    with (
        alcance_global(motivo=_MOTIVO_RECUPERACION, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        fila_token = obtener_token_vigente_por_id(conn, token_id)
        if (
            fila_token is None
            or fila_token.tipo != "recuperacion"
            or not _verificar_credencial(token, fila_token.hash_token)
            or not token_canjeable(
                consumido_en=fila_token.consumido_en, expira_en=fila_token.expira_en, ahora=ahora
            )
        ):
            raise TokenInvalido("token de recuperacion inexistente, ya usado o vencido")

        consumir_token(conn, id=token_id, consumido_en=ahora)
        marcar_password_cambiada(
            conn, usuario_id=fila_token.usuario_id, hash_credencial=hash_credencial(password_nueva)
        )
        revocar_sesiones_del_usuario(
            conn, usuario_id=fila_token.usuario_id, motivo="restablecer_password", revocada_en=ahora
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=fila_token.usuario_id,
            operacion="UPDATE",
            valores_nuevos={"motivo": "restablecer_password"},
        )
