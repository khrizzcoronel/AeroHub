"""Casos de uso de informes operativos de M5 Billing (Sprint S1.18,
RF-I01/RF-I02/RF-I04). El informe compuesto (facturacion por concepto)
tiene validez externa -- su emision se registra en
compliance.log_auditoria (research.md Decision 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aerohub_kernel import ahora_utc

from ..infrastructure import (
    agrupar_facturacion_por_concepto,
    contexto_tenant_id,
    contexto_usuario_id,
    listar_facturas_informe,
    registrar_auditoria,
    sesion,
)


@dataclass(frozen=True, slots=True)
class InformeSimple:
    parametros: dict[str, str]
    generado_en: str
    filas: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class GrupoInforme:
    clave: str
    metricas: dict[str, object]
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class InformeCompuesto:
    parametros: dict[str, str]
    generado_en: str
    grupos: list[GrupoInforme]
    total: Decimal


def consultar_informe_facturas_simple(
    *, periodo_inicio: date, periodo_fin: date, aerolinea_id: int | None, estado: str | None
) -> InformeSimple:
    with sesion() as conn:
        filas = listar_facturas_informe(
            conn,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            aerolinea_id=aerolinea_id,
            estado=estado,
        )
    parametros = {
        "periodo_inicio": periodo_inicio.isoformat(),
        "periodo_fin": periodo_fin.isoformat(),
    }
    if aerolinea_id is not None:
        parametros["aerolinea_id"] = str(aerolinea_id)
    if estado is not None:
        parametros["estado"] = estado
    return InformeSimple(
        parametros=parametros,
        generado_en=ahora_utc().isoformat(),
        filas=[
            {
                "factura_id": str(f.id),
                "aerolinea_id": str(f.aerolinea_id),
                "periodo_inicio": f.periodo_inicio.isoformat(),
                "periodo_fin": f.periodo_fin.isoformat(),
                "moneda": f.moneda,
                "estado": f.estado,
            }
            for f in filas
        ],
    )


def consultar_informe_facturacion_compuesto(
    *, periodo_inicio: date, periodo_fin: date
) -> InformeCompuesto:
    with sesion() as conn:
        grupos = agrupar_facturacion_por_concepto(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
    grupos_informe = [
        GrupoInforme(
            clave=str(g.concepto_cargo_id),
            metricas={"cantidad_lineas": int(g.cantidad_lineas)},
            subtotal=Decimal(g.monto_total),
        )
        for g in grupos
    ]
    # Total = suma de subtotales YA agregados por SQL (RF-I02) -- debe
    # conciliar con el total de las facturas del periodo (SC-003).
    total = sum((g.subtotal for g in grupos_informe), start=Decimal("0"))

    # RF-I04: el informe de facturacion tiene validez externa -- su
    # emision se registra en compliance.log_auditoria (research.md
    # Decision 4), igual que cualquier otra mutacion/emision auditable
    # del sistema.
    usuario_id = contexto_usuario_id()
    if usuario_id is not None:
        with sesion() as conn:
            registrar_auditoria(
                conn,
                esquema="billing",
                tabla="informe_facturacion",
                registro_id=0,
                operacion="INSERT",
                valores_nuevos={
                    "periodo_inicio": periodo_inicio.isoformat(),
                    "periodo_fin": periodo_fin.isoformat(),
                    "total": str(total),
                },
            )

    return InformeCompuesto(
        parametros={
            "periodo_inicio": periodo_inicio.isoformat(),
            "periodo_fin": periodo_fin.isoformat(),
            "tenant_id": str(contexto_tenant_id()),
        },
        generado_en=ahora_utc().isoformat(),
        grupos=grupos_informe,
        total=total,
    )
