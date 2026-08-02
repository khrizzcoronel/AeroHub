"""Escritura de billing.* (Sprint S1.6). Solo persiste -- domain/ ya
valido, application/ ya genero el id y decide journal/auditoria.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import (
    cargo_aeronautico,
    conciliacion_pax,
    factura,
    factura_linea,
    tarifario,
    tarifario_concepto,
)


def insertar_tarifario(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    nombre: str,
    moneda: str,
    vigente_desde: date,
    vigente_hasta: date | None,
    creado_por_usuario_id: int,
) -> None:
    conn.execute(
        insert(tarifario).values(
            id=id,
            tenant_id=tenant_id,
            nombre=nombre,
            moneda=moneda,
            vigente_desde=vigente_desde,
            vigente_hasta=vigente_hasta,
            estado="borrador",
            creado_por_usuario_id=creado_por_usuario_id,
        )
    )


def marcar_tarifario_vigente(conn: Connection, *, id: int, tenant_id: int) -> None:
    conn.execute(
        update(tarifario)
        .where(tarifario.c.id == id, tarifario.c.tenant_id == tenant_id)
        .values(estado="vigente")
    )


def insertar_o_actualizar_tarifario_concepto(
    conn: Connection,
    *,
    id: int,
    tarifario_id: int,
    concepto_cargo_id: int,
    tarifa_unitaria: Decimal,
    monto_minimo: Decimal | None,
    monto_maximo: Decimal | None,
    existente_id: int | None,
) -> None:
    """Upsert por (tarifario_id, concepto_cargo_id) -- `existente_id` lo
    decide application/ (ya consulto si la fila existe); aqui solo INSERT
    o UPDATE segun corresponda, sin volver a consultar."""
    if existente_id is not None:
        conn.execute(
            update(tarifario_concepto)
            .where(tarifario_concepto.c.id == existente_id)
            .values(
                tarifa_unitaria=tarifa_unitaria,
                monto_minimo=monto_minimo,
                monto_maximo=monto_maximo,
            )
        )
        return
    conn.execute(
        insert(tarifario_concepto).values(
            id=id,
            tarifario_id=tarifario_id,
            concepto_cargo_id=concepto_cargo_id,
            tarifa_unitaria=tarifa_unitaria,
            monto_minimo=monto_minimo,
            monto_maximo=monto_maximo,
        )
    )


def insertar_cargo_aeronautico(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    vuelo_id: int,
    concepto_cargo_id: int,
    tarifario_concepto_id: int,
    cantidad: Decimal,
    tarifa_aplicada: Decimal,
    monto_calculado: Decimal,
) -> None:
    conn.execute(
        insert(cargo_aeronautico).values(
            id=id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            concepto_cargo_id=concepto_cargo_id,
            tarifario_concepto_id=tarifario_concepto_id,
            cantidad=cantidad,
            tarifa_aplicada=tarifa_aplicada,
            monto_calculado=monto_calculado,
        )
    )


def insertar_factura(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    aerolinea_id: int,
    periodo_inicio: date,
    periodo_fin: date,
    moneda: str,
) -> None:
    conn.execute(
        insert(factura).values(
            id=id,
            tenant_id=tenant_id,
            aerolinea_id=aerolinea_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            moneda=moneda,
            estado="borrador",
        )
    )


def insertar_factura_linea(
    conn: Connection,
    *,
    id: int,
    factura_id: int,
    cargo_aeronautico_id: int,
    descripcion: str,
    cantidad: Decimal,
    precio_unitario: Decimal,
    monto: Decimal,
) -> None:
    conn.execute(
        insert(factura_linea).values(
            id=id,
            factura_id=factura_id,
            cargo_aeronautico_id=cargo_aeronautico_id,
            descripcion=descripcion,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            monto=monto,
        )
    )


def actualizar_estado_factura(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    estado_nuevo: str,
    emitida_en: datetime | None = None,
    vence_en: datetime | None = None,
) -> None:
    valores: dict[str, object] = {"estado": estado_nuevo}
    if emitida_en is not None:
        valores["emitida_en"] = emitida_en
    if vence_en is not None:
        valores["vence_en"] = vence_en
    conn.execute(
        update(factura)
        .where(factura.c.id == id, factura.c.tenant_id == tenant_id)
        .values(**valores)
    )


def insertar_conciliacion_pax(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    vuelo_id: int,
    periodo: str,
    pax_reportado_aerolinea: int,
    pax_registrado_sistema: int,
    fuente_reporte: str,
) -> None:
    conn.execute(
        insert(conciliacion_pax).values(
            id=id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            periodo=periodo,
            pax_reportado_aerolinea=pax_reportado_aerolinea,
            pax_registrado_sistema=pax_registrado_sistema,
            fuente_reporte=fuente_reporte,
        )
    )


def marcar_conciliacion_conciliada(
    conn: Connection, *, id: int, tenant_id: int, conciliado_en: datetime, usuario_id: int
) -> None:
    conn.execute(
        update(conciliacion_pax)
        .where(conciliacion_pax.c.id == id, conciliacion_pax.c.tenant_id == tenant_id)
        .values(conciliado_en=conciliado_en, conciliado_por_usuario_id=usuario_id)
    )
