"""Informes operativos de M5 Billing (Sprint S1.18, RF-I01/RF-I02):
facturas del periodo, y facturacion agrupada por concepto de cargo --
esta ultima cierra RF-E02 en su parte operativa (spec.md US2 escenario
2, debe conciliar con las facturas emitidas del periodo sin
diferencias). Filtran por tenant_id (PN-01). GROUP BY usa un alias de
tabla (hallazgo empirico de MonetDB, ver CLAUDE.md).
"""

from __future__ import annotations

from datetime import date

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Row

from .tablas import cargo_aeronautico, factura, factura_linea


def listar_facturas_informe(
    conn: Connection,
    *,
    periodo_inicio: date,
    periodo_fin: date,
    aerolinea_id: int | None = None,
    estado: str | None = None,
) -> list[Row]:
    condiciones = [
        factura.c.tenant_id == contexto_tenant_id(),
        factura.c.periodo_inicio >= periodo_inicio,
        factura.c.periodo_fin <= periodo_fin,
    ]
    if aerolinea_id is not None:
        condiciones.append(factura.c.aerolinea_id == aerolinea_id)
    if estado is not None:
        condiciones.append(factura.c.estado == estado)
    stmt = select(factura).where(*condiciones).order_by(factura.c.periodo_inicio)
    return list(conn.execute(stmt))


def agrupar_facturacion_por_concepto(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    """Suma de `factura_linea.monto` agrupada por `concepto_cargo_id`
    (via `cargo_aeronautico`), solo lineas de facturas del periodo y
    tenant -- debe conciliar exactamente con el total de esas mismas
    facturas (SC-003)."""
    f = factura.alias("f")
    fl = factura_linea.alias("fl")
    ca = cargo_aeronautico.alias("ca")
    stmt = (
        select(
            ca.c.concepto_cargo_id,
            func.count().label("cantidad_lineas"),
            func.coalesce(func.sum(fl.c.monto), 0).label("monto_total"),
        )
        .select_from(
            fl.join(f, f.c.id == fl.c.factura_id).join(ca, ca.c.id == fl.c.cargo_aeronautico_id)
        )
        .where(
            f.c.tenant_id == contexto_tenant_id(),
            f.c.periodo_inicio >= periodo_inicio,
            f.c.periodo_fin <= periodo_fin,
        )
        .group_by(ca.c.concepto_cargo_id)
        .order_by(ca.c.concepto_cargo_id)
    )
    return list(conn.execute(stmt))
