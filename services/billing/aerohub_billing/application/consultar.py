"""Consultas de tablero: facturas con total derivado, lineas, conciliaciones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ..domain import diferencia as _diferencia
from ..infrastructure import (
    calcular_total_factura,
    listar_conceptos_de_tarifario,
    listar_conciliaciones,
    listar_facturas,
    listar_lineas_de_factura,
    listar_tarifarios,
    obtener_conciliacion_por_id,
    obtener_factura_por_id,
    sesion,
)


class FacturaNoEncontrada(Exception):
    pass


class ConciliacionNoEncontrada(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FacturaTablero:
    id: int
    aerolinea_id: int
    periodo_inicio: date
    periodo_fin: date
    moneda: str
    estado: str
    total: Decimal
    emitida_en: datetime | None
    vence_en: datetime | None


@dataclass(frozen=True, slots=True)
class FacturaLineaTablero:
    id: int
    cargo_aeronautico_id: int
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    monto: Decimal


@dataclass(frozen=True, slots=True)
class ConceptoTarifarioResumen:
    id: int
    concepto_cargo_id: int
    tarifa_unitaria: Decimal
    monto_minimo: Decimal | None
    monto_maximo: Decimal | None


@dataclass(frozen=True, slots=True)
class TarifarioResumen:
    id: int
    nombre: str
    moneda: str
    vigente_desde: date
    vigente_hasta: date | None
    estado: str
    conceptos: list[ConceptoTarifarioResumen]


@dataclass(frozen=True, slots=True)
class ConciliacionTablero:
    id: int
    vuelo_id: int
    periodo: str
    pax_reportado_aerolinea: int
    pax_registrado_sistema: int
    diferencia: int
    fuente_reporte: str
    conciliado_en: datetime | None


def consultar_facturas(
    *,
    aerolinea_id: int | None = None,
    estado: str | None = None,
    periodo_inicio: date | None = None,
    periodo_fin: date | None = None,
) -> list[FacturaTablero]:
    with sesion() as conn:
        filas = listar_facturas(
            conn,
            aerolinea_id=aerolinea_id,
            estado=estado,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        )
        return [
            FacturaTablero(
                id=f.id,
                aerolinea_id=f.aerolinea_id,
                periodo_inicio=f.periodo_inicio,
                periodo_fin=f.periodo_fin,
                moneda=f.moneda,
                estado=f.estado,
                total=calcular_total_factura(conn, factura_id=f.id),
                emitida_en=f.emitida_en,
                vence_en=f.vence_en,
            )
            for f in filas
        ]


def consultar_factura(*, factura_id: int) -> tuple[FacturaTablero, list[FacturaLineaTablero]]:
    with sesion() as conn:
        f = obtener_factura_por_id(conn, factura_id)
        if f is None:
            raise FacturaNoEncontrada(f"factura {factura_id} no encontrada")
        cabecera = FacturaTablero(
            id=f.id,
            aerolinea_id=f.aerolinea_id,
            periodo_inicio=f.periodo_inicio,
            periodo_fin=f.periodo_fin,
            moneda=f.moneda,
            estado=f.estado,
            total=calcular_total_factura(conn, factura_id=f.id),
            emitida_en=f.emitida_en,
            vence_en=f.vence_en,
        )
        lineas = [
            FacturaLineaTablero(
                id=linea.id,
                cargo_aeronautico_id=linea.cargo_aeronautico_id,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                monto=linea.monto,
            )
            for linea in listar_lineas_de_factura(conn, factura_id=factura_id)
        ]
    return cabecera, lineas


def consultar_tarifarios() -> list[TarifarioResumen]:
    """Sprint S1.17 -- historial completo (todos los estados), cada uno
    con sus conceptos, reutilizando listar_conceptos_de_tarifario ya
    existente desde S1.6 (research.md Decision 4)."""
    with sesion() as conn:
        tarifarios = listar_tarifarios(conn)
        return [
            TarifarioResumen(
                id=t.id,
                nombre=t.nombre,
                moneda=t.moneda,
                vigente_desde=t.vigente_desde,
                vigente_hasta=t.vigente_hasta,
                estado=t.estado,
                conceptos=[
                    ConceptoTarifarioResumen(
                        id=c.id,
                        concepto_cargo_id=c.concepto_cargo_id,
                        tarifa_unitaria=c.tarifa_unitaria,
                        monto_minimo=c.monto_minimo,
                        monto_maximo=c.monto_maximo,
                    )
                    for c in listar_conceptos_de_tarifario(conn, tarifario_id=t.id)
                ],
            )
            for t in tarifarios
        ]


def consultar_conciliaciones() -> list[ConciliacionTablero]:
    """Sprint S1.17 -- todas las conciliaciones del tenant, diferencia
    siempre derivada (research.md Decision 5)."""
    with sesion() as conn:
        filas = listar_conciliaciones(conn)
    return [
        ConciliacionTablero(
            id=c.id,
            vuelo_id=c.vuelo_id,
            periodo=c.periodo,
            pax_reportado_aerolinea=c.pax_reportado_aerolinea,
            pax_registrado_sistema=c.pax_registrado_sistema,
            diferencia=_diferencia(
                pax_reportado_aerolinea=c.pax_reportado_aerolinea,
                pax_registrado_sistema=c.pax_registrado_sistema,
            ),
            fuente_reporte=c.fuente_reporte,
            conciliado_en=c.conciliado_en,
        )
        for c in filas
    ]


def consultar_conciliacion(*, conciliacion_id: int) -> ConciliacionTablero:
    with sesion() as conn:
        c = obtener_conciliacion_por_id(conn, conciliacion_id)
    if c is None:
        raise ConciliacionNoEncontrada(f"conciliacion {conciliacion_id} no encontrada")
    return ConciliacionTablero(
        id=c.id,
        vuelo_id=c.vuelo_id,
        periodo=c.periodo,
        pax_reportado_aerolinea=c.pax_reportado_aerolinea,
        pax_registrado_sistema=c.pax_registrado_sistema,
        diferencia=_diferencia(
            pax_reportado_aerolinea=c.pax_reportado_aerolinea,
            pax_registrado_sistema=c.pax_registrado_sistema,
        ),
        fuente_reporte=c.fuente_reporte,
        conciliado_en=c.conciliado_en,
    )
