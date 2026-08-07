"""Codificacion/decodificacion de JWT (Sprint S1.1, Plan §8.1; scopes y
expiracion corta agregados en S1.2, Plan §8.2, SRS §"JWT de corta vida").

`codificar_jwt` NO es un endpoint de login -- CU-O?? (emision de credenciales
de sesion) queda fuera de alcance de S1.1/S1.2 (el Plan solo pide el
middleware que VALIDA un JWT ya emitido). Existe aqui como utilidad de
arranque/pruebas para construir tokens validos contra los que ejercitar el
middleware con HTTP real (PN-01/PN-02/PN-06/PN-07), documentado
explicitamente como tal para que nadie lo confunda con un flujo de
autenticacion de produccion.

Expiracion por defecto: 30 minutos ("de corta vida", SRS §4 Seguridad --
sin un numero explicito en el documento fuente, ajustado a 30 min el
2026-08-05 por pedido directo del usuario, era 15 min desde S1.2;
configurable via `minutos_expiracion` por el llamador que emita el
token). Debe coincidir con `_MINUTOS_EXPIRACION_SESION` de
`aerohub_tenancy.application.iniciar_sesion` -- esa es la fuente real
usada por el login, esta constante solo alimenta la utilidad de
arranque/pruebas de este archivo.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from ..domain import TokenInvalido

_ALGORITMO = "HS256"
_SECRETO_POR_DEFECTO = "aerohub-dev-secret-nunca-usar-en-produccion"
_MINUTOS_EXPIRACION_POR_DEFECTO = 30


def _secreto() -> str:
    return os.environ.get("AEROHUB_JWT_SECRET", _SECRETO_POR_DEFECTO)


def decodificar_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secreto(), algorithms=[_ALGORITMO])
    except jwt.PyJWTError as exc:
        raise TokenInvalido(f"token JWT invalido: {exc}") from exc


def codificar_jwt(
    *,
    rol: str,
    tenant_id: int | None = None,
    usuario_id: int | None = None,
    scopes: list[str] | None = None,
    minutos_expiracion: int = _MINUTOS_EXPIRACION_POR_DEFECTO,
) -> str:
    claims = {
        "rol": rol,
        "tenant_id": tenant_id,
        "usuario_id": usuario_id,
        "scopes": scopes or [],
        "exp": datetime.now(UTC) + timedelta(minutes=minutos_expiracion),
    }
    return jwt.encode(claims, _secreto(), algorithm=_ALGORITMO)
