"""Codificacion/decodificacion de JWT (Sprint S1.1, Plan §8.1).

`codificar_jwt` NO es un endpoint de login -- CU-O?? (emision de credenciales
de sesion) queda fuera de alcance de S1.1 (Plan §8.1 solo pide el
middleware que VALIDA un JWT ya emitido). Existe aqui como utilidad de
arranque/pruebas para construir tokens validos contra los que ejercitar el
middleware con HTTP real (PN-01/PN-02), documentado explicitamente como tal
para que nadie lo confunda con un flujo de autenticacion de produccion.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from ..domain import TokenInvalido

_ALGORITMO = "HS256"
_SECRETO_POR_DEFECTO = "aerohub-dev-secret-nunca-usar-en-produccion"


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
    minutos_expiracion: int = 60,
) -> str:
    claims = {
        "rol": rol,
        "tenant_id": tenant_id,
        "usuario_id": usuario_id,
        "exp": datetime.now(UTC) + timedelta(minutes=minutos_expiracion),
    }
    return jwt.encode(claims, _secreto(), algorithm=_ALGORITMO)
