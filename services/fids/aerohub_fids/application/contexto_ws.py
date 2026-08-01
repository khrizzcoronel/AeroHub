"""Contexto para la duracion de una conexion WebSocket de FIDS (Sprint
S1.3). Envoltorio delgado sobre infrastructure/ -- api/ no puede importar
infrastructure/ directamente (ADR-017 regla 3).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from ..infrastructure import limpiar_contexto_ws, poblar_contexto_ws

__all__ = ["contexto_de_pantalla_ws"]


@contextmanager
def contexto_de_pantalla_ws(*, tenant_id: int, rol: str) -> Iterator[None]:
    tokens = poblar_contexto_ws(tenant_id=tenant_id, rol=rol)
    try:
        yield
    finally:
        limpiar_contexto_ws(tokens)
