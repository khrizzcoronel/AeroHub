"""Endpoints HTTP y WebSocket de aerohub_fids (Sprint S1.3, Plan §8.3,
RF-T03, RF-O07, RNF-P02, RNF-R04).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (esa es la promesa de "sin capa BFF", SRS §6.4).
"""

from __future__ import annotations

import asyncio

from aerohub_contracts import TokenWebSocketInvalido, autenticar_websocket, requiere_scope
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..application import (
    PantallaConsultada,
    PantallaNoEncontrada,
    PlantillaNoEncontrada,
    UsuarioNoIdentificado,
    asignar_plantilla,
    consultar_pantalla_por_codigo,
    contexto_de_pantalla_ws,
    desuscribir_de_plantilla_pantalla,
    publicar_plantilla,
    registrar_heartbeat_pantalla,
    registrar_pantalla,
    suscribir_a_plantilla_pantalla,
)
from ..domain import PlantillaInvalida
from ..metricas import contar_heartbeat, observar_latencia_propagacion

router = APIRouter(prefix="/fids", tags=["fids"])

_CODIGO_CIERRE_NO_AUTENTICADO = 4401
_CODIGO_CIERRE_SIN_SCOPE = 4403
_CODIGO_CIERRE_PANTALLA_DESCONOCIDA = 4404


class PlantillaPublicarRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    definicion_json: dict


class PlantillaPublicarResponse(BaseModel):
    plantilla_id: str
    version: int


@router.post(
    "/plantillas",
    response_model=PlantillaPublicarResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("fids:administrar"))],
)
def publicar_plantilla_endpoint(cuerpo: PlantillaPublicarRequest) -> PlantillaPublicarResponse:
    """Publica una version nueva de plantilla FIDS (RF-T03)."""
    try:
        resultado = publicar_plantilla(nombre=cuerpo.nombre, definicion_json=cuerpo.definicion_json)
    except PlantillaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PlantillaPublicarResponse(
        plantilla_id=str(resultado.plantilla_id), version=resultado.version
    )


class PantallaRegistrarRequest(BaseModel):
    terminal_id: int
    codigo: str = Field(min_length=1, max_length=20)
    plantilla_id: int
    ubicacion_descripcion: str | None = None
    version_firmware: str | None = None


class PantallaRegistrarResponse(BaseModel):
    pantalla_id: str


@router.post(
    "/pantallas",
    response_model=PantallaRegistrarResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("fids:administrar"))],
)
def registrar_pantalla_endpoint(cuerpo: PantallaRegistrarRequest) -> PantallaRegistrarResponse:
    """Registra una pantalla fisica nueva (RF-O07)."""
    resultado = registrar_pantalla(
        terminal_id=cuerpo.terminal_id,
        codigo=cuerpo.codigo,
        plantilla_id=cuerpo.plantilla_id,
        ubicacion_descripcion=cuerpo.ubicacion_descripcion,
        version_firmware=cuerpo.version_firmware,
    )
    return PantallaRegistrarResponse(pantalla_id=str(resultado.pantalla_id))


class AsignarPlantillaRequest(BaseModel):
    plantilla_id: int


@router.patch(
    "/pantallas/{pantalla_id}/plantilla",
    status_code=204,
    dependencies=[Depends(requiere_scope("fids:administrar"))],
)
def asignar_plantilla_endpoint(pantalla_id: int, cuerpo: AsignarPlantillaRequest) -> None:
    """Cambia la plantilla vigente de una pantalla (RF-T03, RNF-P02: <1s)."""
    try:
        asignar_plantilla(pantalla_id=pantalla_id, plantilla_id=cuerpo.plantilla_id)
    except (PantallaNoEncontrada, PlantillaNoEncontrada) as exc:
        # PN-01: 404, nunca 403.
        raise HTTPException(status_code=404, detail="pantalla o plantilla no encontrada") from exc


class HeartbeatRequest(BaseModel):
    version_firmware: str | None = None


@router.post(
    "/pantallas/{pantalla_id}/heartbeat",
    status_code=204,
    dependencies=[Depends(requiere_scope("fids:heartbeat"))],
)
def heartbeat_endpoint(pantalla_id: int, cuerpo: HeartbeatRequest) -> None:
    """Telemetria periodica de la pantalla fisica (RF-O07, RNF-R04)."""
    try:
        registrar_heartbeat_pantalla(
            pantalla_id=pantalla_id, version_firmware=cuerpo.version_firmware
        )
    except PantallaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail="pantalla no encontrada") from exc
    contar_heartbeat(pantalla=str(pantalla_id))


class PantallaConsultaResponse(BaseModel):
    id: str
    codigo: str
    plantilla_id: str
    definicion_json: dict
    estado: str


@router.get(
    "/pantallas/{codigo}",
    response_model=PantallaConsultaResponse,
    dependencies=[Depends(requiere_scope("fids:leer"))],
)
def obtener_pantalla_endpoint(codigo: str) -> PantallaConsultaResponse:
    """Consulta la pantalla y su plantilla vigente por codigo (arranque del reproductor)."""
    resultado = consultar_pantalla_por_codigo(codigo)
    if resultado is None:
        raise HTTPException(status_code=404, detail="pantalla no encontrada")
    return PantallaConsultaResponse(
        id=str(resultado.id),
        codigo=resultado.codigo,
        plantilla_id=str(resultado.plantilla_id),
        definicion_json=resultado.definicion_json,
        estado=resultado.estado,
    )


@router.websocket("/ws/pantalla/{codigo}")
async def ws_plantilla_pantalla(websocket: WebSocket, codigo: str) -> None:
    """Canal en tiempo real de cambios de plantilla para UNA pantalla
    (RF-T03, RNF-P02). Token por query string -- ver el docstring
    equivalente en aerohub_aodb.api.router.ws_estado_vuelo (S1.2) para el
    porque (la API WebSocket del navegador no admite cabeceras propias, y
    BaseHTTPMiddleware no se ejecuta para el scope "websocket").
    """
    token = websocket.query_params.get("token", "")
    try:
        identidad = autenticar_websocket(token)
    except TokenWebSocketInvalido:
        await websocket.close(code=_CODIGO_CIERRE_NO_AUTENTICADO)
        return
    if "fids:leer" not in identidad.scopes:
        await websocket.close(code=_CODIGO_CIERRE_SIN_SCOPE)
        return

    def _resolver_pantalla() -> PantallaConsultada | None:
        # aerohub_repository.contexto nunca se puebla para el scope
        # "websocket" (BaseHTTPMiddleware no se ejecuta ahi) -- se puebla
        # aqui, a mano, SOLO para esta consulta puntual (PN-01: la
        # resolucion codigo->fila debe quedar filtrada por el tenant_id
        # real del JWT, no ser un lookup global).
        with contexto_de_pantalla_ws(tenant_id=identidad.tenant_id, rol=identidad.rol):
            return consultar_pantalla_por_codigo(codigo)

    resultado = await asyncio.to_thread(_resolver_pantalla)
    if resultado is None:
        await websocket.close(code=_CODIGO_CIERRE_PANTALLA_DESCONOCIDA)
        return

    await websocket.accept()
    cola = suscribir_a_plantilla_pantalla(resultado.id)
    try:
        while True:
            evento = await asyncio.to_thread(cola.get)
            observar_latencia_propagacion(pantalla=codigo, evento=evento)
            await websocket.send_json(
                {
                    "pantalla_id": str(evento.pantalla_id),
                    "plantilla_id": str(evento.plantilla_id),
                    "definicion_json": evento.definicion_json,
                    "ocurrido_en": evento.ocurrido_en.isoformat(),
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        desuscribir_de_plantilla_pantalla(resultado.id, cola)
