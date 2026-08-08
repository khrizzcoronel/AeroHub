"""Informes operativos de M4 Ground Ops (Sprint S1.18, RF-I01/RF-I02):
turnarounds del periodo, y tareas de turnaround agrupadas por tipo de
tarea con conteo de completadas e incidencias asociadas -- filtran por
tenant_id (PN-01). Todo GROUP BY usa un alias de tabla (hallazgo
empirico de MonetDB, ver CLAUDE.md).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import case, func, select
from sqlalchemy.engine import Connection, Row

from .tablas import incidencia_rampa, tarea_turnaround, turnaround


def _limites_periodo(periodo_inicio: date, periodo_fin: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(periodo_inicio, time.min, tzinfo=UTC),
        datetime.combine(periodo_fin, time.max, tzinfo=UTC),
    )


def listar_turnarounds_informe(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date, estado: str | None = None
) -> list[Row]:
    desde, hasta = _limites_periodo(periodo_inicio, periodo_fin)
    condiciones = [
        turnaround.c.tenant_id == contexto_tenant_id(),
        turnaround.c.inicio_previsto >= desde,
        turnaround.c.inicio_previsto <= hasta,
    ]
    if estado is not None:
        condiciones.append(turnaround.c.estado == estado)
    stmt = select(turnaround).where(*condiciones).order_by(turnaround.c.inicio_previsto)
    return list(conn.execute(stmt))


def listar_mis_tareas_informe(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date, usuario_id: int
) -> list[Row]:
    """Tareas del periodo asignadas al agente que consulta (hallazgo 4 de
    la auditoria de la capa operativa, 2026-08-08).

    El dashboard de role_ramp_agent pregunta "¿Que tengo que hacer ahora?"
    pero su unica seccion era el informe de turnarounds de TODO el tenant
    -- un conteo que no responde esa pregunta. No existia ningun endpoint
    de "mis tareas del periodo": el filtro por `agente_usuario_id` solo
    vivia en `listar_tareas_de_turnaround`, que exige un turnaround
    puntual y por lo tanto no sirve para un panel de jornada.

    A diferencia de `listar_tareas_de_turnaround`, aqui el filtro por
    agente NO es condicional al rol: este informe es, por definicion, "las
    tareas de quien pregunta". Un rol supervisor que quiera ver todo tiene
    `listar_turnarounds_informe`.
    """
    desde, hasta = _limites_periodo(periodo_inicio, periodo_fin)
    t = tarea_turnaround.alias("t")
    tu = turnaround.alias("tu")
    stmt = (
        select(
            t.c.id,
            t.c.turnaround_id,
            t.c.tipo_tarea_id,
            t.c.estado,
            t.c.inicio_real,
            t.c.fin_real,
            tu.c.inicio_previsto,
            tu.c.fin_previsto,
            tu.c.estado.label("estado_turnaround"),
        )
        .select_from(t.join(tu, tu.c.id == t.c.turnaround_id))
        .where(
            t.c.tenant_id == contexto_tenant_id(),
            # El guardian G2 solo inspecciona el WHERE, no el ON del JOIN
            # (hallazgo ya documentado en CLAUDE.md) -- por eso el filtro
            # de tenant se repite para la tabla unida.
            tu.c.tenant_id == contexto_tenant_id(),
            t.c.agente_usuario_id == usuario_id,
            tu.c.inicio_previsto >= desde,
            tu.c.inicio_previsto <= hasta,
        )
        .order_by(tu.c.inicio_previsto)
    )
    return list(conn.execute(stmt))


def agrupar_turnarounds_por_tipo_tarea(
    conn: Connection, *, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    """Agrupa tareas de turnaround (no turnarounds) por tipo_tarea_id --
    conteo total, completadas, e incidencias asociadas a esas tareas del
    periodo (via el turnaround al que pertenecen)."""
    desde, hasta = _limites_periodo(periodo_inicio, periodo_fin)
    t = tarea_turnaround.alias("t")
    tu = turnaround.alias("tu")
    inc = incidencia_rampa.alias("inc")

    tiene_incidencia = (
        select(inc.c.id).where(inc.c.tarea_turnaround_id == t.c.id).exists()
    )
    stmt = (
        select(
            t.c.tipo_tarea_id,
            func.count().label("cantidad_tareas"),
            func.sum(case((t.c.estado == "completada", 1), else_=0)).label("completadas"),
            func.sum(case((tiene_incidencia, 1), else_=0)).label("con_incidencia"),
        )
        .select_from(t.join(tu, tu.c.id == t.c.turnaround_id))
        .where(
            t.c.tenant_id == contexto_tenant_id(),
            tu.c.inicio_previsto >= desde,
            tu.c.inicio_previsto <= hasta,
        )
        .group_by(t.c.tipo_tarea_id)
        .order_by(t.c.tipo_tarea_id)
    )
    return list(conn.execute(stmt))
