"""Endpoints HTTP de aerohub_tenancy (Sprints S1.1 CU-O18, S1.2 RF-O12).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (esa es la promesa de "sin capa BFF", SRS §6.4).

Sin `prefix=` en el APIRouter: /tenants y /api-keys son dos familias de
recursos con distinto padre logico dentro del mismo modulo, no una
jerarquia (una api_key no es un sub-recurso de un tenant especifico en la
URL -- pertenece al tenant del JWT/API Key de quien la gestiona).
"""

from __future__ import annotations

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..application import (
    ApiKeyNoEncontrada,
    aprovisionar_tenant,
    crear_api_key,
    revocar_api_key,
    rotar_api_key,
)
from ..domain import TenantInvalido

router = APIRouter(tags=["tenants"])


class TenantCrearRequest(BaseModel):
    # aeropuerto_id/plan_id viajan como STRING, no numero JSON: son ids
    # Snowflake de 64 bits (aerohub_kernel.generar_id) que superan
    # Number.MAX_SAFE_INTEGER de JavaScript -- un numero JSON nativo pierde
    # precision de forma silenciosa al pasar por el motor JS del navegador
    # (hallazgo empirico de S1.1, verificado con el formulario real de
    # apps/web). Pydantic parsea el string decimal directo a int, sin ese
    # paso intermedio de punto flotante, sin importar la magnitud.
    codigo: str = Field(min_length=2, max_length=30)
    razon_social: str = Field(min_length=1)
    aeropuerto_id: int = Field(description="Id Snowflake como string decimal")
    plan_id: int = Field(description="Id Snowflake como string decimal")
    email_admin: str
    nombre_admin: str = Field(min_length=1)
    es_sandbox: bool = False


class TenantCrearResponse(BaseModel):
    # Mismo motivo que arriba, en sentido inverso: si se serializaran como
    # numero JSON, json.parse() del navegador ya los corrompe antes de que
    # el codigo de Angular los toque.
    tenant_id: str
    usuario_admin_id: str
    password_temporal: str


@router.post(
    "/tenants",
    response_model=TenantCrearResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("tenants:crear"))],
)
def crear_tenant(cuerpo: TenantCrearRequest) -> TenantCrearResponse:
    """Aprovisiona un tenant nuevo con su usuario administrador (CU-O18)."""
    try:
        resultado = aprovisionar_tenant(
            codigo=cuerpo.codigo,
            razon_social=cuerpo.razon_social,
            aeropuerto_id=cuerpo.aeropuerto_id,
            plan_id=cuerpo.plan_id,
            email_admin=cuerpo.email_admin,
            nombre_admin=cuerpo.nombre_admin,
            es_sandbox=cuerpo.es_sandbox,
        )
    except TenantInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TenantCrearResponse(
        tenant_id=str(resultado.tenant_id),
        usuario_admin_id=str(resultado.usuario_admin_id),
        password_temporal=resultado.password_temporal,
    )


class ApiKeyCrearResponse(BaseModel):
    api_key_id: str
    api_key_en_claro: str


@router.post(
    "/api-keys",
    response_model=ApiKeyCrearResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("api-keys:administrar"))],
)
def crear_api_key_endpoint() -> ApiKeyCrearResponse:
    """Genera una API Key nueva para el tenant del llamador (RF-O12).

    El secreto en claro se devuelve UNA sola vez -- no se puede recuperar
    despues, solo revocar y crear una nueva.
    """
    resultado = crear_api_key()
    return ApiKeyCrearResponse(
        api_key_id=str(resultado.api_key_id),
        api_key_en_claro=resultado.api_key_en_claro,
    )


@router.post(
    "/api-keys/{api_key_id}/revocar",
    status_code=204,
    dependencies=[Depends(requiere_scope("api-keys:administrar"))],
)
def revocar_api_key_endpoint(api_key_id: int) -> None:
    """Revoca una API Key del propio tenant (PN-06: deja de aceptarse de inmediato)."""
    try:
        revocar_api_key(api_key_id=api_key_id)
    except ApiKeyNoEncontrada as exc:
        # PN-01: 404, nunca 403 -- no confirmar la existencia de una
        # api_key ajena.
        raise HTTPException(status_code=404, detail="api_key no encontrada") from exc


@router.post(
    "/api-keys/{api_key_id}/rotar",
    response_model=ApiKeyCrearResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("api-keys:administrar"))],
)
def rotar_api_key_endpoint(api_key_id: int) -> ApiKeyCrearResponse:
    """RF-O12 -- emite un secreto nuevo sin interrumpir el servicio: la
    key anterior queda revocada (con `rotada_en`), la nueva es la
    credencial activa desde ahora. Evento auditado (SC-004)."""
    try:
        resultado = rotar_api_key(api_key_id=api_key_id)
    except ApiKeyNoEncontrada as exc:
        raise HTTPException(status_code=404, detail="api_key no encontrada") from exc
    return ApiKeyCrearResponse(
        api_key_id=str(resultado.api_key_id),
        api_key_en_claro=resultado.api_key_en_claro,
    )
