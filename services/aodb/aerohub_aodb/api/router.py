"""Endpoints HTTP de aerohub_aodb (Sprint S1.1, Plan §8.1, RF-O02 parcial;
scopes y WebSocket en tiempo real agregados en S1.2, Plan §8.2, PN-07,
RF-O04, RNF-P01).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (esa es la promesa de "sin capa BFF", SRS §6.4).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime

from aerohub_contracts import TokenWebSocketInvalido, autenticar_websocket, requiere_scope
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..application import (
    EstadoDesconocido,
    VueloNoEncontrado,
    alta_vuelo,
    consultar_vuelo,
    desuscribir_de_estado_vuelo,
    registrar_cambio_estado,
    suscribir_a_estado_vuelo,
)
from ..domain import TransicionEstadoInvalida, VueloInvalido

router = APIRouter(prefix="/vuelos", tags=["vuelos"])

_CODIGO_CIERRE_NO_AUTENTICADO = 4401  # rango 4000-4999: codigos de app (RFC 6455 §7.4.2)
_CODIGO_CIERRE_SIN_SCOPE = 4403


class VueloCrearRequest(BaseModel):
    # Los campos *_id aceptan int o string decimal -- Pydantic coerce un
    # string a int sin perder precision, a diferencia de un numero JSON
    # nativo (ver el comentario equivalente en aerohub_tenancy.api.router).
    # El cliente (Angular) DEBE enviarlos como string para ids que superen
    # Number.MAX_SAFE_INTEGER.
    aerolinea_id: int
    aeronave_id: int
    numero_vuelo: str = Field(min_length=1, max_length=10)
    tipo_vuelo_id: int
    fecha_operacion: date
    sentido: str
    aeropuerto_origen_id: int
    aeropuerto_destino_id: int
    sta_utc: datetime
    std_utc: datetime
    pax_estimado: int | None = None
    # `tenant_id` se acepta en el cuerpo (un cliente podria enviarlo) pero
    # SIEMPRE se ignora -- alta_vuelo() ni siquiera lo acepta como
    # parametro, el tenant real viene del JWT via contexto (PN-02).
    tenant_id: int | None = None


class VueloCrearResponse(BaseModel):
    # Los ids Snowflake de 64 bits viajan como string en toda respuesta:
    # como numero JSON, json.parse() del navegador los corrompe en
    # silencio por encima de Number.MAX_SAFE_INTEGER (hallazgo empirico de
    # S1.1, verificado con el formulario real de apps/web).
    vuelo_id: str


class VueloConsultaResponse(BaseModel):
    id: str
    aerolinea_id: str
    aeronave_id: str
    numero_vuelo: str
    tipo_vuelo_id: str
    fecha_operacion: date
    sentido: str
    aeropuerto_origen_id: str
    aeropuerto_destino_id: str
    sta_utc: datetime
    std_utc: datetime
    pax_estimado: int | None


class CambioEstadoRequest(BaseModel):
    codigo_estado_nuevo: str = Field(min_length=1)
    origen_cambio: str


class CambioEstadoResponse(BaseModel):
    vuelo_estado_id: str


@router.post(
    "",
    response_model=VueloCrearResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("vuelos:escribir"))],
)
def crear_vuelo(cuerpo: VueloCrearRequest) -> VueloCrearResponse:
    """Da de alta un vuelo para el tenant del llamador (RF-O02 parcial)."""
    try:
        resultado = alta_vuelo(
            aerolinea_id=cuerpo.aerolinea_id,
            aeronave_id=cuerpo.aeronave_id,
            numero_vuelo=cuerpo.numero_vuelo,
            tipo_vuelo_id=cuerpo.tipo_vuelo_id,
            fecha_operacion=cuerpo.fecha_operacion,
            sentido=cuerpo.sentido,
            aeropuerto_origen_id=cuerpo.aeropuerto_origen_id,
            aeropuerto_destino_id=cuerpo.aeropuerto_destino_id,
            sta_utc=cuerpo.sta_utc,
            std_utc=cuerpo.std_utc,
            pax_estimado=cuerpo.pax_estimado,
        )
    except VueloInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VueloCrearResponse(vuelo_id=str(resultado.vuelo_id))


@router.get(
    "/{vuelo_id}",
    response_model=VueloConsultaResponse,
    dependencies=[Depends(requiere_scope("vuelos:leer"))],
)
def obtener_vuelo(vuelo_id: int) -> VueloConsultaResponse:
    """Consulta un vuelo por id (PN-01: 404 si es de otro tenant)."""
    resultado = consultar_vuelo(vuelo_id)
    if resultado is None:
        # PN-01: un vuelo de otro tenant se ve identico a uno inexistente --
        # nunca 403 (eso confirmaria que el recurso ajeno existe).
        raise HTTPException(status_code=404, detail="vuelo no encontrado")
    return VueloConsultaResponse(
        id=str(resultado.id),
        aerolinea_id=str(resultado.aerolinea_id),
        aeronave_id=str(resultado.aeronave_id),
        numero_vuelo=resultado.numero_vuelo,
        tipo_vuelo_id=str(resultado.tipo_vuelo_id),
        fecha_operacion=resultado.fecha_operacion,
        sentido=resultado.sentido,
        aeropuerto_origen_id=str(resultado.aeropuerto_origen_id),
        aeropuerto_destino_id=str(resultado.aeropuerto_destino_id),
        sta_utc=resultado.sta_utc,
        std_utc=resultado.std_utc,
        pax_estimado=resultado.pax_estimado,
    )


@router.post(
    "/{vuelo_id}/estados",
    response_model=CambioEstadoResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("vuelos:escribir"))],
)
def cambiar_estado_vuelo(vuelo_id: int, cuerpo: CambioEstadoRequest) -> CambioEstadoResponse:
    """Registra un cambio de estado y lo publica en el canal en tiempo
    real /vuelos/ws/estado (RF-O04, RNF-P01).
    """
    try:
        resultado = registrar_cambio_estado(
            vuelo_id=vuelo_id,
            codigo_estado_nuevo=cuerpo.codigo_estado_nuevo,
            origen_cambio=cuerpo.origen_cambio,
        )
    except VueloNoEncontrado as exc:
        # Mismo principio que obtener_vuelo: 404, nunca 403 (PN-01).
        raise HTTPException(status_code=404, detail="vuelo no encontrado") from exc
    except EstadoDesconocido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TransicionEstadoInvalida as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CambioEstadoResponse(vuelo_estado_id=str(resultado.vuelo_estado_id))


@router.websocket("/ws/estado")
async def ws_estado_vuelo(websocket: WebSocket) -> None:
    """Canal en tiempo real de cambios de estado de vuelo (RF-O04, RNF-P01).

    El token viaja por query string (`?token=...`), no por cabecera: la API
    `WebSocket` del navegador no admite cabeceras personalizadas en el
    handshake. Ademas, `BaseHTTPMiddleware` (aerohub_gateway) NUNCA se
    ejecuta para el scope "websocket" de Starlette -- esta ruta se
    autentica a si misma via `aerohub_contracts.autenticar_websocket`
    (mismo JWT, verificado independientemente).

    Solo JWT (sin API Key) y solo scope "vuelos:leer" -- ver el docstring
    de aerohub_contracts.ws_auth para el porque del alcance reducido.
    """
    token = websocket.query_params.get("token", "")
    try:
        identidad = autenticar_websocket(token)
    except TokenWebSocketInvalido:
        await websocket.close(code=_CODIGO_CIERRE_NO_AUTENTICADO)
        return
    if "vuelos:leer" not in identidad.scopes:
        await websocket.close(code=_CODIGO_CIERRE_SIN_SCOPE)
        return

    await websocket.accept()
    cola = suscribir_a_estado_vuelo(identidad.tenant_id)
    try:
        while True:
            # get() bloqueante en un hilo aparte -- no bloquea el event
            # loop mientras espera el proximo evento (posiblemente nunca).
            evento = await asyncio.to_thread(cola.get)
            await websocket.send_json(
                {
                    "vuelo_id": str(evento.vuelo_id),
                    "vuelo_estado_id": str(evento.vuelo_estado_id),
                    "estado_id": str(evento.estado_id),
                    "codigo_estado": evento.codigo_estado,
                    "ocurrido_en": evento.ocurrido_en.isoformat(),
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        desuscribir_de_estado_vuelo(identidad.tenant_id, cola)
