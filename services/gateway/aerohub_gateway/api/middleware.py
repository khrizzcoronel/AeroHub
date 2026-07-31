"""Middleware de autenticacion JWT / API Key (Sprint S1.1 Plan §8.1 JWT;
S1.2 Plan §8.2 API Key + scopes; ADR-014 P2).

Unico punto de la aplicacion HTTP que puebla `aerohub_repository.contexto`
a partir de una peticion -- todo el resto del backend confia en que, si
`contexto_tenant_id()`/`contexto_rol_actor()` devuelven un valor, proviene
de un JWT o una API Key ya validados aqui, nunca de un parametro que el
cliente pueda inventar (PN-02).

Tambien puebla `request.state.scopes` -- lo lee
`aerohub_contracts.scopes.requiere_scope`, la dependencia FastAPI que cada
api/ de cada modulo usa para gatear sus propios endpoints por scope (PN-07).
Se pasa por `request.state`, no por `aerohub_repository.contexto`, porque
scopes es un control de AUTORIZACION a nivel de HTTP/ruta -- ningun modulo
de negocio podria importar un `requiere_scope` de aerohub_gateway sin violar
el contrato de independencia de modulos.

Rate limiting: se aplica DESPUES de autenticar (necesita saber tenant_id/rol
para elegir el cupo correcto), ANTES de reenviar la peticion al router --
una peticion que agota su cupo nunca llega a application/ ni al motor.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..application import (
    autenticar_con_api_key,
    autenticar_peticion,
    contexto_autenticado,
    peticion_permitida,
)
from ..domain import Identidad, IdentidadInvalida, TokenInvalido

__all__ = ["AutenticacionJWTMiddleware"]


class AutenticacionJWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            identidad = self._autenticar(request)
        except (TokenInvalido, IdentidadInvalida) as exc:
            return JSONResponse({"detail": str(exc)}, status_code=401)

        if not peticion_permitida(identidad):
            return JSONResponse({"detail": "limite de tasa excedido"}, status_code=429)

        request.state.scopes = identidad.scopes
        with contexto_autenticado(identidad):
            return await call_next(request)

    def _autenticar(self, request: Request) -> Identidad:
        api_key_en_claro = request.headers.get("x-api-key", "").strip()
        if api_key_en_claro:
            return autenticar_con_api_key(api_key_en_claro)

        encabezado_auth = request.headers.get("authorization", "")
        if encabezado_auth.startswith("Bearer "):
            token = encabezado_auth.removeprefix("Bearer ").strip()
            return autenticar_peticion(token)

        raise TokenInvalido(
            "falta encabezado 'Authorization: Bearer <token>' o 'X-Api-Key: <clave>'"
        )
