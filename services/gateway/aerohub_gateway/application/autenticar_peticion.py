"""Autenticacion de una peticion HTTP a partir de un JWT o una API Key
(Sprint S1.1 Plan §8.1 JWT; S1.2 Plan §8.2 API Key + scopes; ADR-014 P2,
PN-02, PN-06, PN-07).

`contexto_autenticado` es el unico punto que el middleware de api/ invoca:
recibe una Identidad ya resuelta (por cualquiera de los dos metodos) y
puebla/limpia aerohub_repository.contexto alrededor de la peticion --
ninguna otra capa del backend puebla ese contexto.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from ..domain import Identidad, TokenInvalido
from ..infrastructure import decodificar_jwt, limpiar_contexto, poblar_contexto, verificar_api_key

__all__ = ["autenticar_peticion", "autenticar_con_api_key", "contexto_autenticado"]


def autenticar_peticion(token: str) -> Identidad:
    claims = decodificar_jwt(token)
    rol = claims.get("rol")
    if not isinstance(rol, str) or not rol:
        raise TokenInvalido("claim 'rol' ausente o invalida en el token")
    scopes = claims.get("scopes") or []
    if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
        raise TokenInvalido("claim 'scopes' con formato invalido en el token")
    return Identidad(
        tenant_id=claims.get("tenant_id"),
        rol=rol,
        usuario_id=claims.get("usuario_id"),
        scopes=frozenset(scopes),
    )


def autenticar_con_api_key(api_key_en_claro: str) -> Identidad:
    """`api_key_en_claro` tiene la forma "{prefijo}.{secreto}" (analogo a
    `sk_live_...` de Stripe). PN-06: clave revocada, expirada, inexistente o
    con formato invalido -> TokenInvalido, sin distinguir el motivo exacto
    en el mensaje (evitar dar pistas a un atacante sobre cual de los casos
    aplica).
    """
    partes = api_key_en_claro.split(".", 1)
    if len(partes) != 2 or not partes[0] or not partes[1]:
        raise TokenInvalido("formato de API Key invalido")
    prefijo, secreto = partes
    identidad = verificar_api_key(prefijo, secreto)
    if identidad is None:
        raise TokenInvalido("API Key invalida, revocada o expirada")
    return identidad


@contextmanager
def contexto_autenticado(identidad: Identidad) -> Iterator[Identidad]:
    tokens = poblar_contexto(identidad)
    try:
        yield identidad
    finally:
        limpiar_contexto(tokens)
