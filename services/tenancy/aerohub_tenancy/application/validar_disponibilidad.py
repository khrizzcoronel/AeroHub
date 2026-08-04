"""Validación de disponibilidad en tiempo real para el formulario de tenant (post S1.13).

Verifica si un código de tenant o un correo electrónico de usuario administrador
ya existen en la base de datos de MonetDB.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infrastructure import (
    alcance_global,
    existe_tenant_codigo,
    existe_usuario_email,
    sesion,
)

_MOTIVO_ALCANCE_GLOBAL = "verificar_disponibilidad_tenant"
_ROL_PLATAFORMA = "role_platform_admin"


@dataclass(frozen=True, slots=True)
class ResultadoValidacionDisponibilidad:
    codigo_disponible: bool
    codigo_mensaje: str | None
    email_disponible: bool
    email_mensaje: str | None


def validar_disponibilidad_tenant(
    *, codigo: str | None = None, email_admin: str | None = None
) -> ResultadoValidacionDisponibilidad:
    codigo_disp = True
    codigo_msg = None
    email_disp = True
    email_msg = None

    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PLATAFORMA),
        sesion() as conn,
    ):
        if codigo and codigo.strip():
            codigo_clean = codigo.strip().upper()
            if existe_tenant_codigo(conn, codigo_clean):
                codigo_disp = False
                codigo_msg = f"El código '{codigo_clean}' ya está registrado."

        if email_admin and email_admin.strip():
            email_clean = email_admin.strip().lower()
            if existe_usuario_email(conn, email_clean):
                email_disp = False
                email_msg = f"El correo '{email_clean}' ya se encuentra registrado."

    return ResultadoValidacionDisponibilidad(
        codigo_disponible=codigo_disp,
        codigo_mensaje=codigo_msg,
        email_disponible=email_disp,
        email_mensaje=email_msg,
    )
