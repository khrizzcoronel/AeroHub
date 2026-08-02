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

Verificacion de licencia (S1.7, RF-O18/CU-O20): se aplica DENTRO de
`contexto_autenticado`, DESPUES del rate limiting -- necesita
`contexto_tenant_id()`/`contexto_rol_actor()` ya poblados porque
`verificar_licencia` abre su propia `sesion()` (SET ROLE) para consultar
`tenants.licencia` y, si deniega, auditar el intento en la MISMA
transaccion. Una peticion rechazada por licencia ya paso el rate limit --
aceptable: RF-O18 no exige que la verificacion de licencia sea mas barata
que la de tasa, y el orden inverso forzaria abrir una sesion() de DB
ANTES de saber si la peticion sostiene su propio costo de cupo.

`RUTAS_EXENTAS` (S1.3): `/metrics` no pasa por este middleware -- Prometheus
scrapea sin credenciales de aplicacion (en produccion, ese endpoint se
protege por red/mTLS, no por el mismo JWT que el resto de la API). Ninguna
otra ruta se agrega a esta lista sin una razon documentada igual de
explicita: es la excepcion, no el patron.

S1.10 agrega las rutas PUBLICAS de `/auth/*` (login, recuperacion,
verificacion, aceptacion de invitacion) -- por definicion, ninguna de
ellas puede exigir un JWT previo (FR-026): son las que EMITEN uno o
resuelven una accion de un solo uso antes de que exista sesion. El resto
de `/auth/*` (`/auth/yo`, `/auth/logout`, `/auth/cambiar-password`,
`/auth/solicitar-verificacion`) SI exige JWT y no esta en esta lista.

Verificacion de sesion (S1.10, FR-022/FR-023, research.md Decision 5):
se aplica INMEDIATAMENTE despues de autenticar, ANTES del rate limiting
-- una sesion revocada (logout, restablecimiento de password) no debe
consumir cupo de tasa ni llegar a `contexto_autenticado`. No hace nada
si la identidad no trae `sesion_id` (autenticacion por API Key, S1.2).

Contrasena temporal (S1.10, US3, FR-012): la misma consulta que verifica
la sesion devuelve `debe_cambiar_password` (sin round-trip extra). Si es
`True`, toda ruta autenticada distinta de `/auth/cambiar-password`
responde 403 -- contracts/auth-api.md es literal: "unico endpoint
permitido mientras dure la contrasena temporal", ni siquiera
`/auth/logout` es excepcion.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..application import (
    LicenciaNoVigente,
    SesionRevocada,
    autenticar_con_api_key,
    autenticar_peticion,
    contexto_autenticado,
    peticion_permitida,
    verificar_licencia,
    verificar_sesion,
)
from ..domain import Identidad, IdentidadInvalida, TokenInvalido

__all__ = ["AutenticacionJWTMiddleware"]

RUTAS_EXENTAS = frozenset(
    {
        "/metrics",
        "/auth/login",
        "/auth/recuperar",
        "/auth/restablecer",
        "/auth/verificar-correo",
        "/usuarios/aceptar-invitacion",
    }
)

_RUTA_CAMBIAR_PASSWORD = "/auth/cambiar-password"


class AutenticacionJWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in RUTAS_EXENTAS:
            return await call_next(request)
        try:
            identidad = self._autenticar(request)
        except (TokenInvalido, IdentidadInvalida) as exc:
            return JSONResponse({"detail": str(exc)}, status_code=401)

        try:
            debe_cambiar_password = verificar_sesion(sesion_id=identidad.sesion_id)
        except SesionRevocada as exc:
            return JSONResponse({"detail": str(exc)}, status_code=401)

        if debe_cambiar_password and request.url.path != _RUTA_CAMBIAR_PASSWORD:
            return JSONResponse(
                {"detail": "debes cambiar tu contrasena temporal antes de continuar"},
                status_code=403,
            )

        if not peticion_permitida(identidad):
            return JSONResponse({"detail": "limite de tasa excedido"}, status_code=429)

        request.state.scopes = identidad.scopes
        with contexto_autenticado(identidad):
            try:
                verificar_licencia(path=request.url.path, tenant_id=identidad.tenant_id)
            except LicenciaNoVigente as exc:
                return JSONResponse({"detail": str(exc)}, status_code=403)
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
