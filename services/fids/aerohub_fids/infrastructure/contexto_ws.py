"""Puente hacia aerohub_repository.contexto para el WebSocket de FIDS
(Sprint S1.3).

Analogo a aerohub_gateway.infrastructure.contexto_gateway (S1.1) --
REIMPLEMENTADO aqui, no importado de alli, porque aerohub_fids no puede
importar aerohub_gateway (contrato de independencia de modulos,
.importlinter). El WS de FIDS necesita poblar contexto (a diferencia del
WS de vuelos de S1.2, que solo lee `request.state.scopes` y nunca toca la
base) porque resuelve `codigo de pantalla -> fila real` ANTES de
suscribirse -- esa consulta es tenant-scoped (PN-01) y necesita un
tenant_id real en `aerohub_repository.contexto`, no solo saber que el
JWT tiene el scope correcto.
"""

from __future__ import annotations

from contextvars import Token

from aerohub_repository.contexto import (
    _establecer_rol_actor,
    _establecer_tenant_id,
    _establecer_usuario_id,
    _rol_actor,
    _tenant_id,
    _usuario_id,
)

TokensContexto = tuple[Token[int | None], Token[str | None], Token[int | None]]


def poblar_contexto_ws(*, tenant_id: int, rol: str) -> TokensContexto:
    token_t = _establecer_tenant_id(tenant_id)
    token_r = _establecer_rol_actor(rol)
    token_u = _establecer_usuario_id(None)
    return token_t, token_r, token_u


def limpiar_contexto_ws(tokens: TokensContexto) -> None:
    token_t, token_r, token_u = tokens
    _tenant_id.reset(token_t)
    _rol_actor.reset(token_r)
    _usuario_id.reset(token_u)
