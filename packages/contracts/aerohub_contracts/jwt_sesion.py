"""Emision del JWT de sesion (Sprint S1.10). Vive en aerohub_contracts,
no en aerohub_tenancy ni en aerohub_gateway: quien EMITE el JWT de login
es `aerohub_tenancy` (dueno de `iniciar_sesion`), quien lo DECODIFICA es
`aerohub_gateway` (`aerohub_gateway.infrastructure.jwt_.decodificar_jwt`)
-- ninguno de los dos puede importar al otro (.importlinter), y ambos
necesitan el mismo secreto/algoritmo para que un token emitido aqui sea
valido alli. Mismos claims, mismo `AEROHUB_JWT_SECRET`, mismo algoritmo
HS256 que `aerohub_gateway.infrastructure.jwt_` ya usa desde S1.1/S1.2 --
deliberadamente NO se reimplementa un secreto ni un algoritmo distintos.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import jwt

_ALGORITMO = "HS256"
_SECRETO_POR_DEFECTO = "aerohub-dev-secret-nunca-usar-en-produccion"


def _secreto() -> str:
    return os.environ.get("AEROHUB_JWT_SECRET", _SECRETO_POR_DEFECTO)


def sesion_id_de_jwt(token: str) -> int | None:
    """Usado por `POST /auth/logout`: no valida `exp` (una sesion vencida
    igual se puede cerrar explicitamente) pero SI valida la firma -- un
    token con firma invalida no revoca ninguna sesion."""
    try:
        claims = jwt.decode(
            token, _secreto(), algorithms=[_ALGORITMO], options={"verify_exp": False}
        )
    except jwt.PyJWTError:
        return None
    sesion_id = claims.get("sesion_id")
    return int(sesion_id) if sesion_id is not None else None


def emitir_jwt_sesion(
    *,
    rol: str,
    tenant_id: int | None,
    usuario_id: int,
    scopes: frozenset[str],
    sesion_id: int,
    minutos_expiracion: int,
    aerolinea_id: int | None = None,
) -> str:
    claims = {
        "rol": rol,
        "tenant_id": tenant_id,
        "usuario_id": usuario_id,
        "scopes": sorted(scopes),
        "sesion_id": sesion_id,
        # Hallazgo 3 de la auditoria de la capa operativa (2026-08-08):
        # habilita el filtro "solo sus itinerarios"/"sus cargos" de
        # role_airline_coordinator. None para la gran mayoria de usuarios
        # (personal del aeropuerto, no de una aerolinea).
        "aerolinea_id": aerolinea_id,
        "exp": datetime.now(UTC) + timedelta(minutes=minutos_expiracion),
    }
    return jwt.encode(claims, _secreto(), algorithm=_ALGORITMO)
