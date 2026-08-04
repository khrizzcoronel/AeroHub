"""Informes operativos de M1 AODB (Sprint S1.18, RF-I01/RF-I02): vuelos
del periodo, y vuelos agrupados por aerolinea con conteo y % de
puntualidad -- ambos filtran por tenant_id (PN-01), igual que cualquier
otra consulta del modulo (spec.md, Edge Cases: un informe no es un
camino de acceso nuevo). Totales/porcentajes se calculan aqui con SQL
(func.count/func.sum), nunca en Python sobre filas ya traidas.
"""

from __future__ import annotations

from datetime import date

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import case, func, select
from sqlalchemy.engine import Connection, Row

from .tablas import vuelo


def listar_vuelos_informe(
    conn: Connection,
    *,
    periodo_inicio: date,
    periodo_fin: date,
    aerolinea_id: int | None = None,
) -> list[Row]:
    condiciones = [
        vuelo.c.tenant_id == contexto_tenant_id(),
        vuelo.c.fecha_operacion >= periodo_inicio,
        vuelo.c.fecha_operacion <= periodo_fin,
    ]
    if aerolinea_id is not None:
        condiciones.append(vuelo.c.aerolinea_id == aerolinea_id)
    stmt = select(vuelo).where(*condiciones).order_by(vuelo.c.fecha_operacion)
    return list(conn.execute(stmt))


def agrupar_vuelos_por_aerolinea(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    """Puntualidad = % de vuelos con ata_utc no nulo y ata_utc <=
    sta_utc, sobre el total de vuelos del grupo con ata_utc registrado
    -- calculado enteramente en SQL (research.md Decision 6).

    Hallazgo empirico de MonetDB (Sprint S1.18): un GROUP BY sobre la
    forma completa `esquema.tabla.columna` (lo que SQLAlchemy Core
    genera por defecto al agrupar sobre `tabla.c.columna`) es rechazado
    con `42000!SELECT: cannot use non GROUP BY column ... without an
    aggregate function`, incluso cuando esa columna exacta esta en el
    GROUP BY -- reproducido incluso sin ninguna funcion agregada de por
    medio. Se resuelve usando un alias de tabla (`vuelo.alias("v")`):
    SQLAlchemy compila entonces `v.columna` (2 partes) en vez de
    `esquema.tabla.columna` (3 partes), y MonetDB lo acepta. Documentado
    en CLAUDE.md.
    """
    v = vuelo.alias("v")
    a_tiempo = case((v.c.ata_utc <= v.c.sta_utc, 1), else_=0)
    stmt = (
        select(
            v.c.aerolinea_id,
            func.count().label("cantidad_vuelos"),
            func.sum(case((v.c.ata_utc.is_not(None), 1), else_=0)).label("con_llegada"),
            func.sum(case((v.c.ata_utc.is_not(None), a_tiempo), else_=0)).label("a_tiempo"),
        )
        .where(
            v.c.tenant_id == contexto_tenant_id(),
            v.c.fecha_operacion >= periodo_inicio,
            v.c.fecha_operacion <= periodo_fin,
        )
        .group_by(v.c.aerolinea_id)
        .order_by(v.c.aerolinea_id)
    )
    return list(conn.execute(stmt))
