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
    TenantNoEncontrado,
    actualizar_tenant,
    aprovisionar_tenant,
    cambiar_estado_tenant,
    consultar_aeropuertos,
    consultar_planes,
    consultar_tenants,
    crear_api_key,
    obtener_tenant,
    revocar_api_key,
    rotar_api_key,
)
from ..domain import ESTADOS_VALIDOS, TenantInvalido, TransicionTenantInvalida

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


class AeropuertoResponse(BaseModel):
    id: str
    codigo_iata: str
    codigo_icao: str
    nombre: str
    ciudad: str


class PlanResponse(BaseModel):
    id: str
    codigo: str
    nombre: str
    tarifa_base_mensual: str
    moneda: str


@router.get(
    "/catalogo/aeropuertos",
    response_model=list[AeropuertoResponse],
    dependencies=[Depends(requiere_scope("tenants:crear"))],
)
def listar_aeropuertos_endpoint() -> list[AeropuertoResponse]:
    """Para el select de aeropuerto del formulario de tenant -- antes se
    pedia el id de memoria en un campo de texto libre."""
    return [
        AeropuertoResponse(
            id=str(a.id),
            codigo_iata=a.codigo_iata,
            codigo_icao=a.codigo_icao,
            nombre=a.nombre,
            ciudad=a.ciudad,
        )
        for a in consultar_aeropuertos()
    ]


@router.get(
    "/catalogo/planes",
    response_model=list[PlanResponse],
    dependencies=[Depends(requiere_scope("tenants:crear"))],
)
def listar_planes_endpoint() -> list[PlanResponse]:
    return [
        PlanResponse(
            id=str(p.id),
            codigo=p.codigo,
            nombre=p.nombre,
            tarifa_base_mensual=p.tarifa_base_mensual,
            moneda=p.moneda,
        )
        for p in consultar_planes()
    ]


class TenantResumenResponse(BaseModel):
    id: str
    codigo: str
    razon_social: str
    aeropuerto_id: str
    plan_id: str
    estado: str
    es_sandbox: bool


def _resumen_a_response(r) -> TenantResumenResponse:  # noqa: ANN001
    return TenantResumenResponse(
        id=str(r.id),
        codigo=r.codigo,
        razon_social=r.razon_social,
        aeropuerto_id=str(r.aeropuerto_id),
        plan_id=str(r.plan_id),
        estado=r.estado,
        es_sandbox=r.es_sandbox,
    )


@router.get(
    "/tenants",
    response_model=list[TenantResumenResponse],
    dependencies=[Depends(requiere_scope("tenants:administrar"))],
)
def listar_tenants_endpoint() -> list[TenantResumenResponse]:
    """Workpanel: lista de todos los tenants (alcance 'interno', no hay
    filtro de tenant que aplicar -- ver consultas_tenant.py)."""
    return [_resumen_a_response(r) for r in consultar_tenants()]


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResumenResponse,
    dependencies=[Depends(requiere_scope("tenants:administrar"))],
)
def obtener_tenant_endpoint(tenant_id: int) -> TenantResumenResponse:
    try:
        return _resumen_a_response(obtener_tenant(tenant_id))
    except TenantNoEncontrado as exc:
        raise HTTPException(status_code=404, detail="tenant no encontrado") from exc


class TenantActualizarRequest(BaseModel):
    razon_social: str = Field(min_length=1)
    plan_id: int
    es_sandbox: bool = False


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantResumenResponse,
    dependencies=[Depends(requiere_scope("tenants:administrar"))],
)
def actualizar_tenant_endpoint(
    tenant_id: int, cuerpo: TenantActualizarRequest
) -> TenantResumenResponse:
    try:
        resultado = actualizar_tenant(
            tenant_id=tenant_id,
            razon_social=cuerpo.razon_social,
            plan_id=cuerpo.plan_id,
            es_sandbox=cuerpo.es_sandbox,
        )
    except TenantNoEncontrado as exc:
        raise HTTPException(status_code=404, detail="tenant no encontrado") from exc
    except TenantInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _resumen_a_response(resultado)


class TenantCambiarEstadoRequest(BaseModel):
    estado_nuevo: str = Field(description=f"uno de: {', '.join(ESTADOS_VALIDOS)}")


@router.post(
    "/tenants/{tenant_id}/estado",
    response_model=TenantResumenResponse,
    dependencies=[Depends(requiere_scope("tenants:administrar"))],
)
def cambiar_estado_tenant_endpoint(
    tenant_id: int, cuerpo: TenantCambiarEstadoRequest
) -> TenantResumenResponse:
    """Transiciones validas por domain/tenant.py -- p. ej. dar de baja es
    terminal, no se puede reactivar un tenant 'dado_de_baja'."""
    try:
        resultado = cambiar_estado_tenant(tenant_id=tenant_id, estado_nuevo=cuerpo.estado_nuevo)
    except TenantNoEncontrado as exc:
        raise HTTPException(status_code=404, detail="tenant no encontrado") from exc
    except TransicionTenantInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _resumen_a_response(resultado)


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
