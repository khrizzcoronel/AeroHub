"""Autenticacion minima para conexiones WebSocket (Sprint S1.2, Plan §8.2,
RF-O04, RNF-P01).

Los WebSocket de FastAPI/Starlette NO pasan por `BaseHTTPMiddleware`
(Starlette excluye explicitamente el scope "websocket" de ese middleware)
-- por eso `AutenticacionJWTMiddleware` (aerohub_gateway) nunca ve una
conexion WS, y por el contrato de independencia de modulos ningun modulo
de negocio (aerohub_aodb, ...) puede importar aerohub_gateway para reusar
su logica de decodificacion. Se duplica aqui, en el UNICO paquete
transversal pensado para esto, el minimo necesario: decodificar el JWT y
extraer tenant_id/rol/scopes -- misma clave secreta
(`AEROHUB_JWT_SECRET`), mismo formato de claims que
`aerohub_gateway.infrastructure.jwt_` (S1.1/S1.2).

Alcance deliberadamente reducido: solo JWT, no API Key -- un canal de
notificaciones en vivo hacia un dashboard es, en la practica, un consumidor
de sesion humana (JWT tras login), no una integracion servidor-a-servidor
por API Key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt

_ALGORITMO = "HS256"
_SECRETO_POR_DEFECTO = "aerohub-dev-secret-nunca-usar-en-produccion"


def _secreto() -> str:
    return os.environ.get("AEROHUB_JWT_SECRET", _SECRETO_POR_DEFECTO)


class TokenWebSocketInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class IdentidadWebSocket:
    tenant_id: int
    rol: str
    scopes: frozenset[str]


def autenticar_websocket(token: str) -> IdentidadWebSocket:
    try:
        claims = jwt.decode(token, _secreto(), algorithms=[_ALGORITMO])
    except jwt.PyJWTError as exc:
        raise TokenWebSocketInvalido(f"token invalido: {exc}") from exc

    tenant_id = claims.get("tenant_id")
    rol = claims.get("rol")
    scopes = claims.get("scopes") or []
    if not isinstance(tenant_id, int) or tenant_id <= 0:
        raise TokenWebSocketInvalido("token sin tenant_id valido -- WS requiere sesion de tenant")
    if not isinstance(rol, str) or not rol:
        raise TokenWebSocketInvalido("token sin rol valido")
    if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
        raise TokenWebSocketInvalido("claim 'scopes' con formato invalido")
    return IdentidadWebSocket(tenant_id=tenant_id, rol=rol, scopes=frozenset(scopes))
