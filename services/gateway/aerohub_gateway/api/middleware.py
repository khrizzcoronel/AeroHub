"""Middleware de autenticacion JWT (Sprint S1.1, Plan §8.1; ADR-014 P2).

Unico punto de la aplicacion HTTP que puebla `aerohub_repository.contexto`
a partir de una peticion -- todo el resto del backend confia en que, si
`contexto_tenant_id()`/`contexto_rol_actor()` devuelven un valor, proviene
de un JWT ya validado aqui, nunca de un parametro que el cliente pueda
inventar (PN-02).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..application import contexto_autenticado
from ..domain import IdentidadInvalida, TokenInvalido

__all__ = ["AutenticacionJWTMiddleware"]


class AutenticacionJWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        encabezado = request.headers.get("authorization", "")
        if not encabezado.startswith("Bearer "):
            return JSONResponse(
                {"detail": "falta encabezado Authorization: Bearer <token>"}, status_code=401
            )
        token = encabezado.removeprefix("Bearer ").strip()
        try:
            with contexto_autenticado(token):
                return await call_next(request)
        except (TokenInvalido, IdentidadInvalida) as exc:
            return JSONResponse({"detail": str(exc)}, status_code=401)
