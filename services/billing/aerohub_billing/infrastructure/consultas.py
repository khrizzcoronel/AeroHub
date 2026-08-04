"""Lecturas de billing.* y ops.vuelo (Sprint S1.6). Toda consulta sobre una
tabla alcance='tenant' filtra por `contexto_tenant_id()`, sin excepcion
(PN-01). `tarifario_concepto`/`factura_linea` (alcance='interno', sin
columna tenant_id propia) se aislan de forma transitiva: SIEMPRE se
consultan mediante JOIN a su fila padre (`tarifario`/`factura`), que si
lleva el filtro de tenant explicito.

`total` de factura y `diferencia` de conciliacion_pax se derivan aqui
(3NF, SDD-DATA-001 Sec9.5/9.7) -- nunca son columnas.

Nota de alcance: la matriz de privilegios anota "(facturas propias)" para
role_tenant_admin y "(sus cargos)" para role_airline_coordinator, pero
ningun CU fuente (SRS/analisis v6.0) define un filtro adicional por
aerolinea a nivel de usuario individual -- mismo tipo de vacio ya
documentado para role_ramp_agent en S1.5 (ver 97_grants_rampa.sql). El
aislamiento aplicado aqui es por tenant (ya cubre "propias" en el sentido
de "de este tenant, no de otro"); un filtro mas fino por aerolinea
asociada al usuario queda fuera de alcance de este sprint (ninguna tabla
del modelo asocia tenants.usuario a catalogo.aerolinea todavia).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Row

from .tablas import (
    cargo_aeronautico,
    concepto_cargo,
    conciliacion_pax,
    factura,
    factura_linea,
    tarifario,
    tarifario_concepto,
    vuelo,
)


def obtener_vuelo_por_id(conn: Connection, vuelo_id: int) -> Row | None:
    stmt = select(vuelo).where(vuelo.c.tenant_id == contexto_tenant_id(), vuelo.c.id == vuelo_id)
    return conn.execute(stmt).first()


def listar_vuelos_de_aerolinea_en_periodo(
    conn: Connection, *, aerolinea_id: int, periodo_inicio: date, periodo_fin: date
) -> list[Row]:
    stmt = select(vuelo).where(
        vuelo.c.tenant_id == contexto_tenant_id(),
        vuelo.c.aerolinea_id == aerolinea_id,
        vuelo.c.fecha_operacion >= periodo_inicio,
        vuelo.c.fecha_operacion <= periodo_fin,
    )
    return list(conn.execute(stmt))


def listar_conceptos_cargo(conn: Connection) -> list[Row]:
    return list(conn.execute(select(concepto_cargo)))


def obtener_concepto_cargo_por_id(conn: Connection, concepto_cargo_id: int) -> Row | None:
    stmt = select(concepto_cargo).where(concepto_cargo.c.id == concepto_cargo_id)
    return conn.execute(stmt).first()


def obtener_tarifario_por_id(conn: Connection, tarifario_id: int) -> Row | None:
    stmt = select(tarifario).where(
        tarifario.c.tenant_id == contexto_tenant_id(), tarifario.c.id == tarifario_id
    )
    return conn.execute(stmt).first()


def obtener_tarifario_vigente(conn: Connection, *, moneda: str) -> Row | None:
    """El UNICO tarifario con estado='vigente' para (tenant_id, moneda) --
    la regla de "a lo sumo uno" se hace cumplir en application/ antes del
    INSERT/UPDATE que activa un tarifario nuevo (domain no la conoce)."""
    stmt = select(tarifario).where(
        tarifario.c.tenant_id == contexto_tenant_id(),
        tarifario.c.moneda == moneda,
        tarifario.c.estado == "vigente",
    )
    return conn.execute(stmt).first()


def listar_tarifarios(conn: Connection) -> list[Row]:
    """Sprint S1.17 -- todos los tarifarios del tenant, cualquier estado
    (a diferencia de listar_tarifarios_vigentes): historial completo
    para la vista administrativa (research.md Decision 4)."""
    stmt = (
        select(tarifario)
        .where(tarifario.c.tenant_id == contexto_tenant_id())
        .order_by(tarifario.c.moneda, tarifario.c.vigente_desde.desc())
    )
    return list(conn.execute(stmt))


def listar_tarifarios_vigentes(conn: Connection) -> list[Row]:
    """Todos los tarifarios 'vigente' del tenant, sin filtrar por moneda --
    usado por el motor de facturacion (CU-O17) para elegir el tarifario
    aplicable. En la practica se espera uno solo (una operacion factura en
    una moneda principal); multi-moneda simultanea queda fuera de alcance
    de este sprint (no cubierto por ningun Acceptance Scenario de
    spec.md)."""
    stmt = select(tarifario).where(
        tarifario.c.tenant_id == contexto_tenant_id(), tarifario.c.estado == "vigente"
    )
    return list(conn.execute(stmt))


def listar_conceptos_de_tarifario(conn: Connection, *, tarifario_id: int) -> list[Row]:
    """tarifario_concepto es alcance='interno' -- el aislamiento de tenant
    se aplica por construccion: tarifario_id proviene siempre de una fila
    de `tarifario` ya validada contra contexto_tenant_id() por el llamador
    (obtener_tarifario_por_id)."""
    stmt = select(tarifario_concepto).where(tarifario_concepto.c.tarifario_id == tarifario_id)
    return list(conn.execute(stmt))


def obtener_concepto_de_tarifario(
    conn: Connection, *, tarifario_id: int, concepto_cargo_id: int
) -> Row | None:
    stmt = select(tarifario_concepto).where(
        tarifario_concepto.c.tarifario_id == tarifario_id,
        tarifario_concepto.c.concepto_cargo_id == concepto_cargo_id,
    )
    return conn.execute(stmt).first()


def obtener_cargo_existente(
    conn: Connection, *, vuelo_id: int, concepto_cargo_id: int
) -> Row | None:
    """Pre-chequeo de uq_cargo_aeronautico_vuelo_concepto -- evita
    recalcular (y por tanto violar la inmutabilidad) un cargo que ya
    existe para este (vuelo, concepto). Mismo motivo que
    aerohub_ramp.obtener_turnaround_por_vuelo_llegada: un skip legible en
    vez de dejar que la UNIQUE del motor aborte la transaccion completa."""
    stmt = select(cargo_aeronautico).where(
        cargo_aeronautico.c.tenant_id == contexto_tenant_id(),
        cargo_aeronautico.c.vuelo_id == vuelo_id,
        cargo_aeronautico.c.concepto_cargo_id == concepto_cargo_id,
    )
    return conn.execute(stmt).first()


def listar_cargos_no_facturados(conn: Connection, *, vuelo_ids: list[int]) -> list[Row]:
    """Cargos de estos vuelos que todavia no aparecen en ninguna
    factura_linea -- candidatos a agrupar en la factura del periodo."""
    if not vuelo_ids:
        return []
    subconsulta_facturados = select(factura_linea.c.cargo_aeronautico_id)
    stmt = select(cargo_aeronautico).where(
        cargo_aeronautico.c.tenant_id == contexto_tenant_id(),
        cargo_aeronautico.c.vuelo_id.in_(vuelo_ids),
        cargo_aeronautico.c.id.notin_(subconsulta_facturados),
    )
    return list(conn.execute(stmt))


def obtener_factura_por_tenant_aerolinea_periodo(
    conn: Connection, *, aerolinea_id: int, periodo_inicio: date, periodo_fin: date
) -> Row | None:
    stmt = select(factura).where(
        factura.c.tenant_id == contexto_tenant_id(),
        factura.c.aerolinea_id == aerolinea_id,
        factura.c.periodo_inicio == periodo_inicio,
        factura.c.periodo_fin == periodo_fin,
    )
    return conn.execute(stmt).first()


def obtener_factura_por_id(conn: Connection, factura_id: int) -> Row | None:
    stmt = select(factura).where(
        factura.c.tenant_id == contexto_tenant_id(), factura.c.id == factura_id
    )
    return conn.execute(stmt).first()


def listar_facturas(
    conn: Connection,
    *,
    aerolinea_id: int | None,
    estado: str | None,
    periodo_inicio: date | None,
    periodo_fin: date | None,
) -> list[Row]:
    condiciones = [factura.c.tenant_id == contexto_tenant_id()]
    if aerolinea_id is not None:
        condiciones.append(factura.c.aerolinea_id == aerolinea_id)
    if estado is not None:
        condiciones.append(factura.c.estado == estado)
    if periodo_inicio is not None:
        condiciones.append(factura.c.periodo_inicio >= periodo_inicio)
    if periodo_fin is not None:
        condiciones.append(factura.c.periodo_fin <= periodo_fin)
    return list(conn.execute(select(factura).where(*condiciones)))


def listar_lineas_de_factura(conn: Connection, *, factura_id: int) -> list[Row]:
    stmt = select(factura_linea).where(factura_linea.c.factura_id == factura_id)
    return list(conn.execute(stmt))


def calcular_total_factura(conn: Connection, *, factura_id: int) -> Decimal:
    """factura.total NO es columna (3NF, SDD-DATA-001 Sec9.5) -- se deriva
    aqui, en cada lectura."""
    stmt = select(func.coalesce(func.sum(factura_linea.c.monto), 0)).where(
        factura_linea.c.factura_id == factura_id
    )
    total = conn.execute(stmt).scalar_one()
    return Decimal(total)


def obtener_conciliacion_por_id(conn: Connection, conciliacion_id: int) -> Row | None:
    stmt = select(conciliacion_pax).where(
        conciliacion_pax.c.tenant_id == contexto_tenant_id(),
        conciliacion_pax.c.id == conciliacion_id,
    )
    return conn.execute(stmt).first()


def listar_conciliaciones(conn: Connection) -> list[Row]:
    """Sprint S1.17 -- todas las conciliaciones del tenant, sin filtro
    adicional (research.md Decision 5)."""
    stmt = (
        select(conciliacion_pax)
        .where(conciliacion_pax.c.tenant_id == contexto_tenant_id())
        .order_by(conciliacion_pax.c.periodo.desc())
    )
    return list(conn.execute(stmt))


def obtener_conciliacion_por_vuelo_periodo(
    conn: Connection, *, vuelo_id: int, periodo: str
) -> Row | None:
    stmt = select(conciliacion_pax).where(
        conciliacion_pax.c.tenant_id == contexto_tenant_id(),
        conciliacion_pax.c.vuelo_id == vuelo_id,
        conciliacion_pax.c.periodo == periodo,
    )
    return conn.execute(stmt).first()
