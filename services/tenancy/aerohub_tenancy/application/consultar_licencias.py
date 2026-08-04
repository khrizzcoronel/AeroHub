"""Consulta de licencias activas y contratadas por el tenant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc

from ..infrastructure import (
    contexto_tenant_id,
    listar_licencias_del_tenant,
    sesion,
)


@dataclass(frozen=True, slots=True)
class LicenciaResumen:
    id: str
    modulo_codigo: str
    modulo_nombre: str
    activa_desde: datetime
    activa_hasta: datetime | None
    es_vigente: bool


def consultar_licencias_del_tenant() -> list[LicenciaResumen]:
    tenant_id = contexto_tenant_id()
    if tenant_id is None:
        return []

    ahora = ahora_utc()
    with sesion() as conn:
        filas = listar_licencias_del_tenant(conn, tenant_id)

    return [
        LicenciaResumen(
            id=str(f.id),
            modulo_codigo=f.modulo_codigo,
            modulo_nombre=f.modulo_nombre,
            activa_desde=f.activa_desde,
            activa_hasta=f.activa_hasta,
            es_vigente=(
                f.activa_desde <= ahora
                and (f.activa_hasta is None or f.activa_hasta > ahora)
            ),
        )
        for f in filas
    ]
