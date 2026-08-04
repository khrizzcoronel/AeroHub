"""Informes operativos de M9 Compliance (Sprint S1.18, RF-I01/RF-I02):
eventos de auditoria del periodo, y emision de reporte_dgac agrupada por
tipo de reporte -- generaliza el caso especial ya existente en backend
(research.md Decision 5). Filtran por tenant_id explicito (aunque
`compliance.log_auditoria` esta registrada alcance 'interno', el dato
sigue siendo por-tenant y se filtra igual, PN-01). GROUP BY usa un alias
de tabla (hallazgo empirico de MonetDB, ver CLAUDE.md).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from aerohub_repository.audit import log_auditoria
from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Row

from .tablas import reporte_dgac


def _limites_periodo(periodo_inicio: date, periodo_fin: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(periodo_inicio, time.min, tzinfo=UTC),
        datetime.combine(periodo_fin, time.max, tzinfo=UTC),
    )


def listar_eventos_auditoria_informe(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    desde, hasta = _limites_periodo(periodo_inicio, periodo_fin)
    # Solo columnas escalares -- excluye valores_anteriores/valores_nuevos
    # (JSON): sqlalchemy-monetdb ya deserializa columnas JSON a dict/list
    # en la lectura, y volver a pasarlas por json.loads() en un SELECT *
    # sobre la tabla completa rompe con `TypeError: ... not dict`
    # (hallazgo empirico de S1.9, ver CLAUDE.md -- reproducido de nuevo
    # aqui al seleccionar la tabla completa en vez de columnas puntuales).
    stmt = (
        select(
            log_auditoria.c.id,
            log_auditoria.c.esquema,
            log_auditoria.c.tabla,
            log_auditoria.c.operacion,
            log_auditoria.c.usuario_id,
            log_auditoria.c.rol_codigo,
            log_auditoria.c.ocurrido_en,
        )
        .where(
            log_auditoria.c.tenant_id == contexto_tenant_id(),
            log_auditoria.c.ocurrido_en >= desde,
            log_auditoria.c.ocurrido_en <= hasta,
        )
        .order_by(log_auditoria.c.ocurrido_en.desc())
    )
    return list(conn.execute(stmt))


def agrupar_reportes_dgac_por_tipo(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    r = reporte_dgac.alias("r")
    stmt = (
        select(r.c.tipo_reporte_id, func.count().label("cantidad_reportes"))
        .where(
            r.c.tenant_id == contexto_tenant_id(),
            r.c.periodo_inicio >= periodo_inicio,
            r.c.periodo_fin <= periodo_fin,
        )
        .group_by(r.c.tipo_reporte_id)
        .order_by(r.c.tipo_reporte_id)
    )
    return list(conn.execute(stmt))
