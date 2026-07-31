"""Puente hacia aerohub_repository.contexto (Sprint S1.1, Plan §8.1; ADR-014 P2).

Unico lugar del backend que llama a `_establecer_*` -- todo el resto del
codigo (application/, infrastructure/ de cada modulo de negocio) solo LEE
el contexto (`contexto_tenant_id()`, etc.), nunca lo escribe. Reservado a
infrastructure/ por ADR-017 regla 4 (import-linter lo verifica).
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

from ..domain import Identidad

TokensContexto = tuple[Token[int | None], Token[str | None], Token[int | None]]


def poblar_contexto(identidad: Identidad) -> TokensContexto:
    token_t = _establecer_tenant_id(identidad.tenant_id)
    token_r = _establecer_rol_actor(identidad.rol)
    token_u = _establecer_usuario_id(identidad.usuario_id)
    return token_t, token_r, token_u


def limpiar_contexto(tokens: TokensContexto) -> None:
    token_t, token_r, token_u = tokens
    _tenant_id.reset(token_t)
    _rol_actor.reset(token_r)
    _usuario_id.reset(token_u)
