"""Borrado físico de tenant y sus registros dependientes.

Exclusivo para rol Administrador de Plataforma (`role_platform_admin`).
"""

from __future__ import annotations

from ..infrastructure import (
    alcance_global,
    eliminar_tenant_y_relaciones_db,
    obtener_tenant_por_id_global,
    sesion,
)
from .gestionar_tenant import TenantNoEncontrado

_MOTIVO_ALCANCE_GLOBAL = "eliminar_tenant_fisico"
_ROL_PLATAFORMA = "role_platform_admin"


def eliminar_tenant_fisico(*, tenant_id: int) -> None:
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PLATAFORMA),
        sesion() as conn,
    ):
        existente = obtener_tenant_por_id_global(conn, tenant_id)
        if existente is None:
            raise TenantNoEncontrado(f"tenant {tenant_id} no encontrado")

        eliminar_tenant_y_relaciones_db(conn, tenant_id)
