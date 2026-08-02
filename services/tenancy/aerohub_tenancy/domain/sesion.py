"""Vigencia de sesion y resolucion de rol vigente (Sprint S1.10,
ADR-020, data-model.md). Puro -- sin I/O; recibe filas ya leidas por
infrastructure/ y decide.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class RolVigenteInconsistente(Exception):
    """Mas de un rol vigente para el mismo usuario -- error de datos, se
    reporta, nunca se elige uno en silencio (decision del usuario previa a
    este sprint: un rol activo por usuario)."""


@dataclass(frozen=True, slots=True)
class RolAsignado:
    rol_id: int
    codigo: str
    nombre: str
    expira_en: datetime | None


def sesion_vigente(*, revocada_en: datetime | None, expira_en: datetime, ahora: datetime) -> bool:
    return revocada_en is None and ahora < expira_en


def resolver_rol_vigente(roles: list[RolAsignado], *, ahora: datetime) -> RolAsignado | None:
    """`roles` ya viene filtrado por `usuario_id`; esta funcion aplica
    `expira_en` y decide. None si ninguno esta vigente (FR-014 -- sin rol
    vigente, el login falla como cualquier otra credencial invalida).
    """
    vigentes = [r for r in roles if r.expira_en is None or ahora < r.expira_en]
    if len(vigentes) > 1:
        raise RolVigenteInconsistente(
            f"el usuario tiene {len(vigentes)} roles vigentes simultaneos, se esperaba a lo sumo 1"
        )
    return vigentes[0] if vigentes else None
