"""Endpoints HTTP de aerohub_passenger (Sprint S1.6, Plan Sec8.6, RF-O17,
CU-O19).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (SRS Sec6.4).
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..application import (
    TerminalNoEncontrado,
    consultar_terminales,
    consultar_tiempos_espera,
    recalcular_tiempos_espera,
)

router = APIRouter(prefix="/passenger", tags=["experiencia-pasajero"])


class RecalcularTiemposEsperaRequest(BaseModel):
    terminal_id: str
    fecha: date
    franja_minutos: int = 30


class RecalcularTiemposEsperaResponse(BaseModel):
    franjas_actualizadas: int
    franjas_descartadas_por_muestra_insuficiente: int


class FranjaTiempoEsperaResponse(BaseModel):
    franja_inicio: time
    franja_fin: time
    minutos_estimados: Decimal
    muestra_n: int
    calculado_en: datetime


class TiemposEsperaResponse(BaseModel):
    terminal_id: str
    fecha: date
    franjas: list[FranjaTiempoEsperaResponse]


class TerminalResponse(BaseModel):
    id: str
    codigo: str
    nombre: str


@router.get(
    "/catalogo/terminales",
    response_model=list[TerminalResponse],
    dependencies=[Depends(requiere_scope("passenger:leer"))],
)
def listar_terminales_endpoint() -> list[TerminalResponse]:
    """Catalogo para el selector de terminal de la vista de M6 (2026-08-08).

    Bajo `passenger:leer` y no reusando `GET /puertas/terminales`: ese
    exige `puertas:leer`, que role_airline_coordinator no tiene aunque M6
    SI sea su modulo."""
    return [
        TerminalResponse(id=str(t.id), codigo=t.codigo, nombre=t.nombre)
        for t in consultar_terminales()
    ]


@router.post(
    "/tiempos-espera/recalcular",
    response_model=RecalcularTiemposEsperaResponse,
    dependencies=[Depends(requiere_scope("passenger:escribir"))],
)
def recalcular_endpoint(cuerpo: RecalcularTiemposEsperaRequest) -> RecalcularTiemposEsperaResponse:
    """CU-O19 -- agrega ops.asignacion_puerta + rampa.turnaround en
    billing.tiempo_espera_agregado. Una franja se descarta (no se
    escribe fila) si muestra_n == 0 -- nunca se publica un estimado sin
    soporte estadistico."""
    try:
        resultado = recalcular_tiempos_espera(
            terminal_id=int(cuerpo.terminal_id),
            fecha=cuerpo.fecha,
            franja_minutos=cuerpo.franja_minutos,
        )
    except TerminalNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RecalcularTiemposEsperaResponse(
        franjas_actualizadas=resultado.franjas_actualizadas,
        franjas_descartadas_por_muestra_insuficiente=(
            resultado.franjas_descartadas_por_muestra_insuficiente
        ),
    )


@router.get(
    "/tiempos-espera",
    response_model=TiemposEsperaResponse,
    dependencies=[Depends(requiere_scope("passenger:leer"))],
)
def obtener_tiempos_espera_endpoint(terminal_id: str, fecha: date) -> TiemposEsperaResponse:
    """Lectura sin PII (PN-11) -- el modelo de respuesta solo expone las
    columnas de billing.tiempo_espera_agregado, nunca un dato de pasajero,
    vuelo o agente individual."""
    franjas = consultar_tiempos_espera(terminal_id=int(terminal_id), fecha=fecha)
    return TiemposEsperaResponse(
        terminal_id=terminal_id,
        fecha=fecha,
        franjas=[
            FranjaTiempoEsperaResponse(
                franja_inicio=f.franja_inicio,
                franja_fin=f.franja_fin,
                minutos_estimados=f.minutos_estimados,
                muestra_n=f.muestra_n,
                calculado_en=f.calculado_en,
            )
            for f in franjas
        ],
    )
