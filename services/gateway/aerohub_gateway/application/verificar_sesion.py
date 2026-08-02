"""Verificacion de sesion vigente en cada peticion autenticada (Sprint
S1.10, spec.md US7, FR-022/FR-023; research.md Decision 5).

Sin esto, "cerrar sesion" o "restablecer contrasena" solo tendrian
efecto en la base -- el JWT ya emitido seguiria sirviendo hasta su
`exp`. Vive en aerohub_gateway por la misma razon que
verificar_licencia.py: es un control transversal de enrutamiento, no
una regla de negocio de aerohub_tenancy.

Devuelve tambien `debe_cambiar_password` (leido en la MISMA consulta,
sin round-trip extra) -- lo usa el middleware para bloquear toda ruta
autenticada salvo `/auth/cambiar-password` mientras la contrasena
temporal siga vigente (US3, FR-012).
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc

from ..infrastructure import alcance_global, obtener_estado_sesion, sesion

_MOTIVO_ALCANCE_GLOBAL = "verificacion_sesion_por_peticion"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"


class SesionRevocada(Exception):
    def __init__(self) -> None:
        super().__init__("sesion revocada o vencida")


def verificar_sesion(*, sesion_id: int | None) -> bool:
    """No hace nada (devuelve `False`, "no debe cambiar password") si la
    identidad no trae `sesion_id` (API Key, S1.2 -- su propia vigencia ya
    se verifico en `verificar_api_key`, y no tiene concepto de contrasena
    temporal)."""
    if sesion_id is None:
        return False
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        estado = obtener_estado_sesion(conn, sesion_id=sesion_id, ahora=ahora_utc())
    if not estado.vigente:
        raise SesionRevocada
    return estado.debe_cambiar_password
