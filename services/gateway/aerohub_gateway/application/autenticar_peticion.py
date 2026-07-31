"""Autenticacion de una peticion HTTP a partir de un JWT (Sprint S1.1, Plan
§8.1; ADR-014 P2, PN-02).

`contexto_autenticado` es el unico punto que el middleware de api/ invoca:
decodifica el token, construye la Identidad (fail-fast si los claims son
incoherentes) y puebla/limpia aerohub_repository.contexto alrededor de la
peticion -- ninguna otra capa del backend puebla ese contexto.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from ..domain import Identidad, TokenInvalido
from ..infrastructure import decodificar_jwt, limpiar_contexto, poblar_contexto

__all__ = ["autenticar_peticion", "contexto_autenticado"]


def autenticar_peticion(token: str) -> Identidad:
    claims = decodificar_jwt(token)
    rol = claims.get("rol")
    if not isinstance(rol, str) or not rol:
        raise TokenInvalido("claim 'rol' ausente o invalida en el token")
    return Identidad(
        tenant_id=claims.get("tenant_id"),
        rol=rol,
        usuario_id=claims.get("usuario_id"),
    )


@contextmanager
def contexto_autenticado(token: str) -> Iterator[Identidad]:
    identidad = autenticar_peticion(token)
    tokens = poblar_contexto(identidad)
    try:
        yield identidad
    finally:
        limpiar_contexto(tokens)
