"""Endpoints HTTP de aerohub_tenancy (Sprint S1.1, Plan §8.1, CU-O18).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (esa es la promesa de "sin capa BFF", SRS §6.4).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..application import aprovisionar_tenant
from ..domain import TenantInvalido

router = APIRouter(prefix="/tenants", tags=["tenants"])


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


@router.post("", response_model=TenantCrearResponse, status_code=201)
def crear_tenant(cuerpo: TenantCrearRequest) -> TenantCrearResponse:
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
