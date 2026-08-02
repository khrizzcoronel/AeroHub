"""Endpoints HTTP de aerohub_billing (Sprint S1.6, Plan Sec8.6, RF-O15,
RF-O17 parcial, RF-T10, CU-O17).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (SRS Sec6.4).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..application import (
    ConceptoCargoNoEncontrado,
    ConciliacionNoEncontrada,
    ConciliacionYaExiste,
    DiferenciaNoNula,
    FacturaNoEncontrada,
    PeriodoInvalido,
    TarifarioNoEncontrado,
    TarifarioVigenteNoEncontrado,
    TarifarioYaVigente,
    UsuarioNoIdentificado,
    activar_tarifario,
    agregar_concepto_a_tarifario,
    calcular_facturacion,
    conciliar,
    consultar_conciliacion,
    consultar_factura,
    consultar_facturas,
    crear_tarifario,
    disputar_factura,
    emitir_factura,
    registrar_conciliacion,
)

router = APIRouter(prefix="/billing", tags=["facturacion"])


class CrearTarifarioRequest(BaseModel):
    nombre: str
    moneda: str
    vigente_desde: date
    vigente_hasta: date | None = None


class CrearTarifarioResponse(BaseModel):
    tarifario_id: str


class AgregarConceptoRequest(BaseModel):
    concepto_cargo_id: str
    tarifa_unitaria: Decimal
    monto_minimo: Decimal | None = None
    monto_maximo: Decimal | None = None


class AgregarConceptoResponse(BaseModel):
    tarifario_concepto_id: str


class CalcularFacturacionRequest(BaseModel):
    aerolinea_id: str
    periodo_inicio: date
    periodo_fin: date


class CalcularFacturacionResponse(BaseModel):
    factura_id: str | None
    cargos_calculados: int
    cargos_ya_existentes: int


class FacturaResponse(BaseModel):
    id: str
    aerolinea_id: str
    periodo_inicio: date
    periodo_fin: date
    moneda: str
    estado: str
    total: Decimal
    emitida_en: datetime | None
    vence_en: datetime | None


class FacturaLineaResponse(BaseModel):
    id: str
    cargo_aeronautico_id: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    monto: Decimal


class FacturaDetalleResponse(BaseModel):
    factura: FacturaResponse
    lineas: list[FacturaLineaResponse]


class DisputarFacturaRequest(BaseModel):
    motivo: str


class RegistrarConciliacionRequest(BaseModel):
    vuelo_id: str
    periodo: str
    pax_reportado_aerolinea: int
    pax_registrado_sistema: int
    fuente_reporte: str


class RegistrarConciliacionResponse(BaseModel):
    conciliacion_id: str
    diferencia: int


class ConciliacionResponse(BaseModel):
    id: str
    vuelo_id: str
    periodo: str
    pax_reportado_aerolinea: int
    pax_registrado_sistema: int
    diferencia: int
    fuente_reporte: str
    conciliado_en: datetime | None


@router.post(
    "/tarifarios",
    response_model=CrearTarifarioResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def crear_tarifario_endpoint(cuerpo: CrearTarifarioRequest) -> CrearTarifarioResponse:
    try:
        resultado = crear_tarifario(
            nombre=cuerpo.nombre,
            moneda=cuerpo.moneda,
            vigente_desde=cuerpo.vigente_desde,
            vigente_hasta=cuerpo.vigente_hasta,
        )
    except UsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CrearTarifarioResponse(tarifario_id=str(resultado.tarifario_id))


@router.post(
    "/tarifarios/{tarifario_id}/conceptos",
    response_model=AgregarConceptoResponse,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def agregar_concepto_endpoint(
    tarifario_id: int, cuerpo: AgregarConceptoRequest
) -> AgregarConceptoResponse:
    try:
        resultado = agregar_concepto_a_tarifario(
            tarifario_id=tarifario_id,
            concepto_cargo_id=int(cuerpo.concepto_cargo_id),
            tarifa_unitaria=cuerpo.tarifa_unitaria,
            monto_minimo=cuerpo.monto_minimo,
            monto_maximo=cuerpo.monto_maximo,
        )
    except (TarifarioNoEncontrado, ConceptoCargoNoEncontrado) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AgregarConceptoResponse(tarifario_concepto_id=str(resultado.tarifario_concepto_id))


@router.post(
    "/tarifarios/{tarifario_id}/activar",
    status_code=204,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def activar_tarifario_endpoint(tarifario_id: int) -> None:
    try:
        activar_tarifario(tarifario_id=tarifario_id)
    except TarifarioNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TarifarioYaVigente as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/facturacion/calcular",
    response_model=CalcularFacturacionResponse,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def calcular_facturacion_endpoint(
    cuerpo: CalcularFacturacionRequest,
) -> CalcularFacturacionResponse:
    """Motor de facturacion (CU-O17) -- consolida los hechos facturables
    del periodo con el tarifario vigente. Todo o nada: 409 si algun vuelo
    del periodo no tiene tarifario que lo cubra."""
    try:
        resultado = calcular_facturacion(
            aerolinea_id=int(cuerpo.aerolinea_id),
            periodo_inicio=cuerpo.periodo_inicio,
            periodo_fin=cuerpo.periodo_fin,
        )
    except PeriodoInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TarifarioVigenteNoEncontrado as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CalcularFacturacionResponse(
        factura_id=str(resultado.factura_id) if resultado.factura_id is not None else None,
        cargos_calculados=resultado.cargos_calculados,
        cargos_ya_existentes=resultado.cargos_ya_existentes,
    )


@router.get(
    "/facturas",
    response_model=list[FacturaResponse],
    dependencies=[Depends(requiere_scope("billing:leer"))],
)
def listar_facturas_endpoint(
    aerolinea_id: str | None = None,
    estado: str | None = None,
    periodo_inicio: date | None = None,
    periodo_fin: date | None = None,
) -> list[FacturaResponse]:
    facturas = consultar_facturas(
        aerolinea_id=int(aerolinea_id) if aerolinea_id is not None else None,
        estado=estado,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
    )
    return [
        FacturaResponse(
            id=str(f.id),
            aerolinea_id=str(f.aerolinea_id),
            periodo_inicio=f.periodo_inicio,
            periodo_fin=f.periodo_fin,
            moneda=f.moneda,
            estado=f.estado,
            total=f.total,
            emitida_en=f.emitida_en,
            vence_en=f.vence_en,
        )
        for f in facturas
    ]


@router.get(
    "/facturas/{factura_id}",
    response_model=FacturaDetalleResponse,
    dependencies=[Depends(requiere_scope("billing:leer"))],
)
def obtener_factura_endpoint(factura_id: int) -> FacturaDetalleResponse:
    try:
        cabecera, lineas = consultar_factura(factura_id=factura_id)
    except FacturaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FacturaDetalleResponse(
        factura=FacturaResponse(
            id=str(cabecera.id),
            aerolinea_id=str(cabecera.aerolinea_id),
            periodo_inicio=cabecera.periodo_inicio,
            periodo_fin=cabecera.periodo_fin,
            moneda=cabecera.moneda,
            estado=cabecera.estado,
            total=cabecera.total,
            emitida_en=cabecera.emitida_en,
            vence_en=cabecera.vence_en,
        ),
        lineas=[
            FacturaLineaResponse(
                id=str(linea.id),
                cargo_aeronautico_id=str(linea.cargo_aeronautico_id),
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                monto=linea.monto,
            )
            for linea in lineas
        ],
    )


@router.post(
    "/facturas/{factura_id}/emitir",
    status_code=204,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def emitir_factura_endpoint(factura_id: int) -> None:
    try:
        emitir_factura(factura_id=factura_id)
    except FacturaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/facturas/{factura_id}/disputar",
    status_code=204,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def disputar_factura_endpoint(factura_id: int, cuerpo: DisputarFacturaRequest) -> None:
    """Unico metodo de mutacion disponible para role_billing_officer sobre
    una factura ya emitida (matriz: "Up (disputas)") -- nunca altera un
    monto_calculado (FR-007)."""
    try:
        disputar_factura(factura_id=factura_id, motivo=cuerpo.motivo)
    except FacturaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/conciliaciones",
    response_model=RegistrarConciliacionResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def registrar_conciliacion_endpoint(
    cuerpo: RegistrarConciliacionRequest,
) -> RegistrarConciliacionResponse:
    try:
        resultado = registrar_conciliacion(
            vuelo_id=int(cuerpo.vuelo_id),
            periodo=cuerpo.periodo,
            pax_reportado_aerolinea=cuerpo.pax_reportado_aerolinea,
            pax_registrado_sistema=cuerpo.pax_registrado_sistema,
            fuente_reporte=cuerpo.fuente_reporte,
        )
    except ConciliacionYaExiste as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RegistrarConciliacionResponse(
        conciliacion_id=str(resultado.conciliacion_id), diferencia=resultado.diferencia
    )


@router.get(
    "/conciliaciones/{conciliacion_id}",
    response_model=ConciliacionResponse,
    dependencies=[Depends(requiere_scope("billing:leer"))],
)
def obtener_conciliacion_endpoint(conciliacion_id: int) -> ConciliacionResponse:
    try:
        c = consultar_conciliacion(conciliacion_id=conciliacion_id)
    except ConciliacionNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConciliacionResponse(
        id=str(c.id),
        vuelo_id=str(c.vuelo_id),
        periodo=c.periodo,
        pax_reportado_aerolinea=c.pax_reportado_aerolinea,
        pax_registrado_sistema=c.pax_registrado_sistema,
        diferencia=c.diferencia,
        fuente_reporte=c.fuente_reporte,
        conciliado_en=c.conciliado_en,
    )


@router.post(
    "/conciliaciones/{conciliacion_id}/conciliar",
    status_code=204,
    dependencies=[Depends(requiere_scope("billing:escribir"))],
)
def conciliar_endpoint(conciliacion_id: int) -> None:
    """Solo permitido si diferencia == 0 -- compuerta de pruebas
    obligatoria del sprint (FR-006)."""
    try:
        conciliar(conciliacion_id=conciliacion_id)
    except ConciliacionNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DiferenciaNoNula as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
