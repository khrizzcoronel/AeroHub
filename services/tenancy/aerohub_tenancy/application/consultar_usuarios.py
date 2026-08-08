"""Consulta de usuarios pertenecientes al tenant del usuario autenticado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..infrastructure import (
    contexto_tenant_id,
    listar_usuarios_del_tenant,
    sesion,
)


@dataclass(frozen=True, slots=True)
class UsuarioResumen:
    id: str
    email: str
    nombre: str
    estado: str
    creado_en: datetime
    ultimo_acceso_en: datetime | None
    rol_codigo: str | None
    rol_nombre: str | None
    aerolinea_id: str | None = None


def consultar_usuarios_del_tenant() -> list[UsuarioResumen]:
    tenant_id = contexto_tenant_id()
    if tenant_id is None:
        return []

    with sesion() as conn:
        filas = listar_usuarios_del_tenant(conn, tenant_id)

    return [
        UsuarioResumen(
            id=str(f.id),
            email=f.email,
            nombre=f.nombre,
            estado=f.estado,
            creado_en=f.creado_en,
            ultimo_acceso_en=f.ultimo_acceso_en,
            rol_codigo=f.rol_codigo,
            rol_nombre=f.rol_nombre,
            aerolinea_id=str(f.aerolinea_id) if f.aerolinea_id is not None else None,
        )
        for f in filas
    ]
