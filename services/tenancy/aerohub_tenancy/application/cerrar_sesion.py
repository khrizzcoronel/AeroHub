"""CU-IA07 -- Cerrar sesion de verdad (Sprint S1.10, spec.md US7,
FR-023). Revoca la sesion del JWT presentado -- idempotente: cerrar una
sesion ya cerrada no es un error (contracts/auth-api.md).
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc

from ..infrastructure import alcance_global, revocar_sesion, sesion

_MOTIVO_ALCANCE_GLOBAL = "cierre_sesion"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"


def cerrar_sesion(*, sesion_id: int) -> None:
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        revocar_sesion(conn, id=sesion_id, motivo="cierre_sesion", revocada_en=ahora_utc())
