"""Aplicacion del limite de tasa a una identidad ya autenticada (Sprint
S1.2, Plan §8.2).
"""

from __future__ import annotations

from ..domain import Identidad
from ..infrastructure import limitador_global

__all__ = ["clave_de_limite", "peticion_permitida"]


def clave_de_limite(identidad: Identidad) -> str:
    """Cupo independiente por tenant+rol -- una identidad de API Key y una
    de JWT del mismo tenant comparten cupo si comparten rol (razonable:
    ambas terminan pegandole a las mismas tablas bajo el mismo SET ROLE).
    """
    return f"{identidad.tenant_id}:{identidad.rol}"


def peticion_permitida(identidad: Identidad) -> bool:
    return limitador_global.permitir(clave_de_limite(identidad))
