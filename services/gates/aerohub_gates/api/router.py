"""Endpoints HTTP de aerohub_gates (Sprint S1.4, Plan §8.4, RF-O02, OP2a,
PN-05).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (esa es la promesa de "sin capa BFF", SRS §6.4).
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..application import (
    AsignacionNoEncontrada,
    InformeCompuesto,
    InformeSimple,
    PuertaDuplicada,
    PuertaNoEncontrada,
    TerminalDuplicada,
    TerminalNoEncontrada,
    UsuarioNoIdentificado,
    VueloNoEncontrado,
    actualizar_puerta,
    asignar_puerta,
    cancelar_asignacion,
    consultar_informe_asignaciones_compuesto,
    consultar_informe_asignaciones_simple,
    consultar_tablero_de_puertas,
    consultar_vuelos_sin_asignacion,
    crear_puerta,
    crear_terminal,
    ejecutar_asignacion_automatica,
    listar_terminales_del_tenant,
)
from ..domain import (
    AsignacionPuertaInvalida,
    PuertaIncompatible,
    PuertaInvalida,
    SolapamientoPuertaInvalido,
    TerminalInvalida,
)

router = APIRouter(prefix="/puertas", tags=["puertas"])


class AsignarPuertaRequest(BaseModel):
    vuelo_id: int
    puerta_id: int
    inicio_previsto: datetime
    fin_previsto: datetime


class AsignarPuertaResponse(BaseModel):
    asignacion_id: str


class PuertaTableroResponse(BaseModel):
    id: str
    terminal_id: str
    codigo: str
    tipo: str
    envergadura_max_m: float
    tiene_pasarela: bool


class AsignacionTableroResponse(BaseModel):
    id: str
    puerta_id: str
    puerta_codigo: str
    vuelo_id: str
    numero_vuelo: str
    inicio_previsto: datetime
    fin_previsto: datetime
    estado: str


class TableroResponse(BaseModel):
    puertas: list[PuertaTableroResponse]
    asignaciones: list[AsignacionTableroResponse]


class VueloSinAsignarResponse(BaseModel):
    id: str
    numero_vuelo: str
    sta_utc: datetime
    std_utc: datetime
    envergadura_m: float


class AsignacionAutomaticaResponse(BaseModel):
    asignados: list[str]
    sin_asignar: list[str] = Field(
        description="vuelo_id de los vuelos que no pudieron asignarse: sin "
        "puerta compatible en envergadura, o sin ventana libre sin solapar."
    )


class TerminalCrearRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=10)
    nombre: str = Field(min_length=1, max_length=100)


class TerminalCrearResponse(BaseModel):
    terminal_id: str


class TerminalListadoResponse(BaseModel):
    id: str
    codigo: str
    nombre: str


class PuertaCrearRequest(BaseModel):
    terminal_id: int
    codigo: str = Field(min_length=1, max_length=10)
    tipo: str
    envergadura_max_m: float
    tiene_pasarela: bool = False


class PuertaCrearResponse(BaseModel):
    puerta_id: str


class PuertaEditarRequest(BaseModel):
    terminal_id: int
    codigo: str = Field(min_length=1, max_length=10)
    tipo: str
    envergadura_max_m: float
    tiene_pasarela: bool = False


@router.post(
    "/asignaciones",
    response_model=AsignarPuertaResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("puertas:escribir"))],
)
def asignar_puerta_endpoint(cuerpo: AsignarPuertaRequest) -> AsignarPuertaResponse:
    """Asigna una puerta a un vuelo (RF-O02, PN-05)."""
    try:
        resultado = asignar_puerta(
            vuelo_id=cuerpo.vuelo_id,
            puerta_id=cuerpo.puerta_id,
            inicio_previsto=cuerpo.inicio_previsto,
            fin_previsto=cuerpo.fin_previsto,
        )
    except (PuertaNoEncontrada, VueloNoEncontrado) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (UsuarioNoIdentificado, AsignacionPuertaInvalida, PuertaIncompatible) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SolapamientoPuertaInvalido as exc:
        # RF-O02: "conflicto detectado se notifica" -- 409, con el detalle
        # del intervalo y la asignacion existente con la que choca.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AsignarPuertaResponse(asignacion_id=str(resultado.asignacion_id))


@router.post(
    "/asignaciones/{asignacion_id}/cancelar",
    status_code=204,
    dependencies=[Depends(requiere_scope("puertas:escribir"))],
)
def cancelar_asignacion_endpoint(asignacion_id: int) -> None:
    """Cancela una asignacion, liberando la puerta (baja logica, P5: nunca
    un DELETE de motor sobre la fila)."""
    try:
        cancelar_asignacion(asignacion_id=asignacion_id)
    except AsignacionNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/terminales",
    response_model=TerminalCrearResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("puertas:escribir"))],
)
def crear_terminal_endpoint(cuerpo: TerminalCrearRequest) -> TerminalCrearResponse:
    """Alta de terminal (Fase 3 de docs/diseno/PLAN_CORRECCION_MODULOS.md,
    causa raiz backend: M3 no tenia forma de crear terminales, solo se
    veian si un seed las insertaba a mano)."""
    try:
        resultado = crear_terminal(codigo=cuerpo.codigo, nombre=cuerpo.nombre)
    except TerminalInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TerminalDuplicada as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TerminalCrearResponse(terminal_id=str(resultado.terminal_id))


@router.get(
    "/terminales",
    response_model=list[TerminalListadoResponse],
    dependencies=[Depends(requiere_scope("puertas:leer"))],
)
def listar_terminales_endpoint() -> list[TerminalListadoResponse]:
    return [
        TerminalListadoResponse(id=str(t.id), codigo=t.codigo, nombre=t.nombre)
        for t in listar_terminales_del_tenant()
    ]


@router.post(
    "",
    response_model=PuertaCrearResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("puertas:escribir"))],
)
def crear_puerta_endpoint(cuerpo: PuertaCrearRequest) -> PuertaCrearResponse:
    """Alta de puerta (Fase 3 de docs/diseno/PLAN_CORRECCION_MODULOS.md,
    causa raiz backend: el tablero solo listaba puertas ya existentes,
    ninguna forma de crearlas desde la API)."""
    try:
        resultado = crear_puerta(
            terminal_id=cuerpo.terminal_id,
            codigo=cuerpo.codigo,
            tipo=cuerpo.tipo,
            envergadura_max_m=cuerpo.envergadura_max_m,
            tiene_pasarela=cuerpo.tiene_pasarela,
        )
    except PuertaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TerminalNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PuertaDuplicada as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PuertaCrearResponse(puerta_id=str(resultado.puerta_id))


@router.patch(
    "/{puerta_id}",
    status_code=204,
    dependencies=[Depends(requiere_scope("puertas:escribir"))],
)
def editar_puerta_endpoint(puerta_id: int, cuerpo: PuertaEditarRequest) -> None:
    """Edicion de puerta -- terminal, codigo, tipo, envergadura y pasarela
    (Fase 3, mismo hallazgo que el alta: no existia ninguna forma de
    editar una puerta ya creada)."""
    try:
        actualizar_puerta(
            puerta_id=puerta_id,
            terminal_id=cuerpo.terminal_id,
            codigo=cuerpo.codigo,
            tipo=cuerpo.tipo,
            envergadura_max_m=cuerpo.envergadura_max_m,
            tiene_pasarela=cuerpo.tiene_pasarela,
        )
    except PuertaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (TerminalNoEncontrada, PuertaNoEncontrada) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PuertaDuplicada as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/vuelos-sin-asignar",
    response_model=list[VueloSinAsignarResponse],
    dependencies=[Depends(requiere_scope("puertas:leer"))],
)
def listar_vuelos_sin_asignar_endpoint() -> list[VueloSinAsignarResponse]:
    """Catalogo para el <select> de vuelo del formulario "Asignar puerta
    manualmente" (2026-08-08, pedido directo del usuario) -- la consulta
    ya existia desde S1.4 para el asignador automatico, sin ningun
    listado expuesto por API hasta ahora."""
    return [
        VueloSinAsignarResponse(
            id=str(v.id),
            numero_vuelo=v.numero_vuelo,
            sta_utc=v.sta_utc,
            std_utc=v.std_utc,
            envergadura_m=v.envergadura_m,
        )
        for v in consultar_vuelos_sin_asignacion()
    ]


@router.get(
    "/tablero",
    response_model=TableroResponse,
    dependencies=[Depends(requiere_scope("puertas:leer"))],
)
def tablero_de_puertas_endpoint() -> TableroResponse:
    """Tablero de puertas: todas las puertas del tenant y sus asignaciones
    vigentes (Plan §8.4)."""
    puertas, asignaciones = consultar_tablero_de_puertas()
    return TableroResponse(
        puertas=[
            PuertaTableroResponse(
                id=str(p.id),
                terminal_id=str(p.terminal_id),
                codigo=p.codigo,
                tipo=p.tipo,
                envergadura_max_m=p.envergadura_max_m,
                tiene_pasarela=p.tiene_pasarela,
            )
            for p in puertas
        ],
        asignaciones=[
            AsignacionTableroResponse(
                id=str(a.id),
                puerta_id=str(a.puerta_id),
                puerta_codigo=a.puerta_codigo,
                vuelo_id=str(a.vuelo_id),
                numero_vuelo=a.numero_vuelo,
                inicio_previsto=a.inicio_previsto,
                fin_previsto=a.fin_previsto,
                estado=a.estado,
            )
            for a in asignaciones
        ],
    )


@router.post(
    "/asignaciones/automatica",
    response_model=AsignacionAutomaticaResponse,
    dependencies=[Depends(requiere_scope("puertas:escribir"))],
)
def asignacion_automatica_endpoint() -> AsignacionAutomaticaResponse:
    """Ejecuta la asignacion automatica por programacion lineal sobre los
    vuelos del tenant que todavia no tienen puerta (Plan §8.4)."""
    resultado = ejecutar_asignacion_automatica()
    return AsignacionAutomaticaResponse(
        asignados=[str(v) for v in resultado.asignados],
        sin_asignar=[str(v) for v in resultado.sin_asignar],
    )


# --------------------------------------------------------------------------
# Informes operativos (Sprint S1.18, RF-I01-RF-I04)
# --------------------------------------------------------------------------


class InformeSimpleResponse(BaseModel):
    parametros: dict[str, str]
    generado_en: str
    filas: list[dict[str, object]]


class GrupoInformeResponse(BaseModel):
    clave: str
    metricas: dict[str, object]
    subtotal: int


class InformeCompuestoResponse(BaseModel):
    parametros: dict[str, str]
    generado_en: str
    grupos: list[GrupoInformeResponse]
    total: int


def _csv_informe_simple(informe: InformeSimple) -> Response:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    for clave, valor in informe.parametros.items():
        escritor.writerow([clave, valor])
    escritor.writerow(["generado_en", informe.generado_en])
    escritor.writerow([])
    if informe.filas:
        columnas = list(informe.filas[0].keys())
        escritor.writerow(columnas)
        for fila in informe.filas:
            escritor.writerow([fila.get(c, "") for c in columnas])
    return Response(content=buffer.getvalue(), media_type="text/csv")


def _csv_informe_compuesto(informe: InformeCompuesto) -> Response:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    for clave, valor in informe.parametros.items():
        escritor.writerow([clave, valor])
    escritor.writerow(["generado_en", informe.generado_en])
    escritor.writerow([])
    if informe.grupos:
        columnas_metricas = list(informe.grupos[0].metricas.keys())
        escritor.writerow(["clave", *columnas_metricas, "subtotal"])
        for g in informe.grupos:
            valores_metricas = [g.metricas.get(c, "") for c in columnas_metricas]
            escritor.writerow([g.clave, *valores_metricas, g.subtotal])
    escritor.writerow(["TOTAL", informe.total])
    return Response(content=buffer.getvalue(), media_type="text/csv")


@router.get(
    "/informes/simple",
    response_model=None,
    dependencies=[Depends(requiere_scope("puertas:leer"))],
)
def informe_asignaciones_simple_endpoint(
    periodo_inicio: date, periodo_fin: date, puerta_id: str | None = None, formato: str = "json"
) -> InformeSimpleResponse | Response:
    informe = consultar_informe_asignaciones_simple(
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        puerta_id=int(puerta_id) if puerta_id is not None else None,
    )
    if formato == "csv":
        return _csv_informe_simple(informe)
    return InformeSimpleResponse(
        parametros=informe.parametros, generado_en=informe.generado_en, filas=informe.filas
    )


@router.get(
    "/informes/compuesto",
    response_model=None,
    dependencies=[Depends(requiere_scope("puertas:leer"))],
)
def informe_asignaciones_compuesto_endpoint(
    periodo_inicio: date, periodo_fin: date, formato: str = "json"
) -> InformeCompuestoResponse | Response:
    informe = consultar_informe_asignaciones_compuesto(
        periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
    )
    if formato == "csv":
        return _csv_informe_compuesto(informe)
    return InformeCompuestoResponse(
        parametros=informe.parametros,
        generado_en=informe.generado_en,
        grupos=[
            GrupoInformeResponse(clave=g.clave, metricas=g.metricas, subtotal=g.subtotal)
            for g in informe.grupos
        ],
        total=informe.total,
    )
