"""Informes operativos de M3 Gates (Sprint S1.18, RF-I01/RF-I02):
asignaciones del periodo, y asignaciones agrupadas por puerta con
conteo y conflictos (solapamiento de intervalos) -- filtran por
tenant_id (PN-01). Todo GROUP BY usa un alias de tabla (hallazgo
empirico de MonetDB, ver CLAUDE.md y
specs/020-informes-operativos/research.md Decision 6).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import case, func, select
from sqlalchemy.engine import Connection, Row

from .tablas import asignacion_puerta


def _limites_periodo(periodo_inicio: date, periodo_fin: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(periodo_inicio, time.min, tzinfo=timezone.utc),
        datetime.combine(periodo_fin, time.max, tzinfo=timezone.utc),
    )


def listar_asignaciones_informe(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date, puerta_id: int | None = None
) -> list[Row]:
    desde, hasta = _limites_periodo(periodo_inicio, periodo_fin)
    condiciones = [
        asignacion_puerta.c.tenant_id == contexto_tenant_id(),
        asignacion_puerta.c.inicio_previsto >= desde,
        asignacion_puerta.c.inicio_previsto <= hasta,
    ]
    if puerta_id is not None:
        condiciones.append(asignacion_puerta.c.puerta_id == puerta_id)
    stmt = (
        select(asignacion_puerta)
        .where(*condiciones)
        .order_by(asignacion_puerta.c.inicio_previsto)
    )
    return list(conn.execute(stmt))


def agrupar_asignaciones_por_puerta(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    """Conflicto = asignacion de la misma puerta cuyo intervalo previsto
    se solapa con el de otra asignacion de la misma puerta (anti-join
    correlacionado contra un segundo alias, mismo criterio de
    "conflicto" ya usado en puertas/tablero-puertas del frontend desde
    S1.12, ahora calculado en el servidor)."""
    desde, hasta = _limites_periodo(periodo_inicio, periodo_fin)
    a = asignacion_puerta.alias("a")
    otra = asignacion_puerta.alias("otra")
    tiene_conflicto = (
        select(otra.c.id)
        .where(
            otra.c.tenant_id == a.c.tenant_id,
            otra.c.puerta_id == a.c.puerta_id,
            otra.c.id != a.c.id,
            otra.c.inicio_previsto < a.c.fin_previsto,
            otra.c.fin_previsto > a.c.inicio_previsto,
        )
        .exists()
    )
    stmt = (
        select(
            a.c.puerta_id,
            func.count().label("cantidad_asignaciones"),
            func.sum(case((tiene_conflicto, 1), else_=0)).label("con_conflicto"),
        )
        .where(
            a.c.tenant_id == contexto_tenant_id(),
            a.c.inicio_previsto >= desde,
            a.c.inicio_previsto <= hasta,
        )
        .group_by(a.c.puerta_id)
        .order_by(a.c.puerta_id)
    )
    return list(conn.execute(stmt))
