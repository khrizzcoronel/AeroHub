"""Endpoints HTTP de aerohub_ramp (Sprint S1.5, Plan §8.5, RF-O16, OP2b,
CU-O16).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (esa es la promesa de "sin capa BFF", SRS §6.4).
"""

from __future__ import annotations

from datetime import datetime

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..application import (
    TareaNoEncontrada,
    TareaTurnaroundInvalida,
    TipoTareaNoEncontrado,
    TurnaroundNoEncontrado,
    TurnaroundYaExiste,
    UsuarioNoIdentificado,
    VueloNoEncontrado,
    VuelosIncompatibles,
    consultar_incidencias,
    consultar_tareas_de_turnaround,
    consultar_turnarounds,
    crear_turnaround,
    finalizar_tarea,
    iniciar_tarea,
)

router = APIRouter(prefix="/rampa", tags=["rampa"])


class CrearTurnaroundRequest(BaseModel):
    vuelo_llegada_id: int
    vuelo_salida_id: int
    inicio_previsto: datetime
    fin_previsto: datetime


class CrearTurnaroundResponse(BaseModel):
    turnaround_id: str


class TurnaroundResponse(BaseModel):
    id: str
    vuelo_llegada_id: str
    numero_vuelo_llegada: str
    vuelo_salida_id: str
    numero_vuelo_salida: str
    aeronave_id: str
    inicio_previsto: datetime
    fin_previsto: datetime
    estado: str


class IniciarTareaRequest(BaseModel):
    tipo_tarea_id: int


class IniciarTareaResponse(BaseModel):
    tarea_id: str


class TareaResponse(BaseModel):
    id: str
    turnaround_id: str
    tipo_tarea_id: str
    agente_usuario_id: str
    inicio_real: datetime | None
    fin_real: datetime | None
    estado: str


class FinalizarTareaRequest(BaseModel):
    fin_real: datetime


class FinalizarTareaResponse(BaseModel):
    tarea_id: str
    duracion_minutos: float
    incidencia_generada: bool


class IncidenciaResponse(BaseModel):
    id: str
    tarea_turnaround_id: str
    tipo_incidencia_codigo: str
    descripcion: str
    severidad: str
    detectada_en: datetime


@router.post(
    "/turnarounds",
    response_model=CrearTurnaroundResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("rampa:escribir"))],
)
def crear_turnaround_endpoint(cuerpo: CrearTurnaroundRequest) -> CrearTurnaroundResponse:
    """Empareja un vuelo de llegada y uno de salida de la misma aeronave
    en un turnaround (RF-O16, SDD-DATA-001 §8.3)."""
    try:
        resultado = crear_turnaround(
            vuelo_llegada_id=cuerpo.vuelo_llegada_id,
            vuelo_salida_id=cuerpo.vuelo_salida_id,
            inicio_previsto=cuerpo.inicio_previsto,
            fin_previsto=cuerpo.fin_previsto,
        )
    except VueloNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TurnaroundYaExiste as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except VuelosIncompatibles as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CrearTurnaroundResponse(turnaround_id=str(resultado.turnaround_id))


@router.get(
    "/turnarounds",
    response_model=list[TurnaroundResponse],
    dependencies=[Depends(requiere_scope("rampa:leer"))],
)
def listar_turnarounds_endpoint() -> list[TurnaroundResponse]:
    return [
        TurnaroundResponse(
            id=str(t.id),
            vuelo_llegada_id=str(t.vuelo_llegada_id),
            numero_vuelo_llegada=t.numero_vuelo_llegada,
            vuelo_salida_id=str(t.vuelo_salida_id),
            numero_vuelo_salida=t.numero_vuelo_salida,
            aeronave_id=str(t.aeronave_id),
            inicio_previsto=t.inicio_previsto,
            fin_previsto=t.fin_previsto,
            estado=t.estado,
        )
        for t in consultar_turnarounds()
    ]


@router.post(
    "/turnarounds/{turnaround_id}/tareas",
    response_model=IniciarTareaResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("rampa:escribir"))],
)
def iniciar_tarea_endpoint(
    turnaround_id: int, cuerpo: IniciarTareaRequest
) -> IniciarTareaResponse:
    """El agente de rampa marca el inicio de una tarea (CU-O16, paso 2)."""
    try:
        resultado = iniciar_tarea(turnaround_id=turnaround_id, tipo_tarea_id=cuerpo.tipo_tarea_id)
    except (TurnaroundNoEncontrado, TipoTareaNoEncontrado) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IniciarTareaResponse(tarea_id=str(resultado.tarea_id))


@router.get(
    "/turnarounds/{turnaround_id}/tareas",
    response_model=list[TareaResponse],
    dependencies=[Depends(requiere_scope("rampa:leer"))],
)
def listar_tareas_endpoint(turnaround_id: int) -> list[TareaResponse]:
    """Minimo privilegio (Plan §8.5): role_ramp_agent solo ve sus propias
    tareas -- filtrado en la capa de aplicacion/infraestructura."""
    return [
        TareaResponse(
            id=str(t.id),
            turnaround_id=str(t.turnaround_id),
            tipo_tarea_id=str(t.tipo_tarea_id),
            agente_usuario_id=str(t.agente_usuario_id),
            inicio_real=t.inicio_real,
            fin_real=t.fin_real,
            estado=t.estado,
        )
        for t in consultar_tareas_de_turnaround(turnaround_id=turnaround_id)
    ]


@router.post(
    "/tareas/{tarea_id}/finalizar",
    response_model=FinalizarTareaResponse,
    dependencies=[Depends(requiere_scope("rampa:escribir"))],
)
def finalizar_tarea_endpoint(
    tarea_id: int, cuerpo: FinalizarTareaRequest
) -> FinalizarTareaResponse:
    """El agente de rampa marca el fin de una tarea; genera una incidencia
    de rampa automaticamente si supera el estandar (CU-O16 pasos 3-4,
    RF-O16). Minimo privilegio: 404 (no 403) si la tarea es de otro agente
    y el rol activo es role_ramp_agent -- ver aerohub_ramp.application.
    finalizar_tarea (PN-01)."""
    try:
        resultado = finalizar_tarea(tarea_id=tarea_id, fin_real=cuerpo.fin_real)
    except TareaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TareaTurnaroundInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FinalizarTareaResponse(
        tarea_id=str(resultado.tarea_id),
        duracion_minutos=resultado.duracion_minutos,
        incidencia_generada=resultado.incidencia_generada,
    )


@router.get(
    "/incidencias",
    response_model=list[IncidenciaResponse],
    dependencies=[Depends(requiere_scope("rampa:leer"))],
)
def listar_incidencias_endpoint() -> list[IncidenciaResponse]:
    return [
        IncidenciaResponse(
            id=str(i.id),
            tarea_turnaround_id=str(i.tarea_turnaround_id),
            tipo_incidencia_codigo=i.tipo_incidencia_codigo,
            descripcion=i.descripcion,
            severidad=i.severidad,
            detectada_en=i.detectada_en,
        )
        for i in consultar_incidencias()
    ]
