"""Lecturas de ops.asignacion_puerta/terminal/puerta, rampa.turnaround y
billing.tiempo_espera_agregado (Sprint S1.6). Toda consulta sobre una
tabla alcance='tenant' filtra por `contexto_tenant_id()`, sin excepcion
(PN-01).
"""

from __future__ import annotations

from datetime import date, time

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import select
from sqlalchemy.engine import Connection, Row

from .tablas import asignacion_puerta, puerta, terminal, tiempo_espera_agregado, turnaround


def obtener_terminal_por_id(
    conn: Connection, terminal_id: int, *, tenant_id: int | None = None
) -> Row | None:
    """`tenant_id` explicito para el ciclo programado (2026-08-08), que corre
    bajo `alcance_global()` recorriendo TODOS los tenants: ahi no hay tenant
    ambiente y `contexto_tenant_id()` lanzaria. El camino de peticion HTTP
    no pasa el parametro y sigue resolviendolo del contexto, que es lo que
    impide que un cliente elija el tenant."""
    stmt = select(terminal).where(
        terminal.c.tenant_id == (tenant_id if tenant_id is not None else contexto_tenant_id()),
        terminal.c.id == terminal_id,
    )
    return conn.execute(stmt).first()


def listar_terminales_de_todos_los_tenants(conn: Connection) -> list[Row]:
    """SIN filtro de tenant -- solo valido dentro de `alcance_global()`
    (ADR-019 G3). Lo usa el ciclo programado de recalculo (RF-O17), que por
    definicion es un proceso de plataforma sin tenant ambiente, igual que el
    monitor de senal de FIDS. Devuelve tenant_id junto al id de terminal
    porque el ciclo necesita ambos para escribir la fila agregada."""
    return list(conn.execute(select(terminal.c.id, terminal.c.tenant_id, terminal.c.codigo)))


def listar_terminales(conn: Connection) -> list[Row]:
    """Catalogo de terminales del tenant para el selector de la vista de
    M6 (2026-08-08).

    `ops.terminal` NO es un catalogo global: tiene `tenant_id` real, asi
    que filtra por tenant como cualquier otra lectura (PN-01) -- mismo
    tratamiento que ya le da aerohub_fids.

    Existe aca, y no se reusa `GET /puertas/terminales` de M3, porque ese
    endpoint exige `puertas:leer`: role_airline_coordinator tiene M6 y
    `passenger:leer` pero NO `puertas:leer`, asi que dependeria de un
    scope de otro modulo para poder usar el suyo. Verificado que los 3
    roles con `passenger:leer` tienen GRANT SELECT sobre ops.terminal
    (96_grants_ops.sql) salvo role_tenant_analyst, a quien la matriz le
    niega `ops` entero -- decision en pausa, ver hallazgo 3.
    """
    stmt = (
        select(terminal)
        .where(terminal.c.tenant_id == contexto_tenant_id())
        .order_by(terminal.c.codigo)
    )
    return list(conn.execute(stmt))


def listar_asignaciones_completadas_de_terminal(
    conn: Connection, *, terminal_id: int, fecha: date, tenant_id: int | None = None
) -> list[Row]:
    """Solo asignaciones con inicio_real/fin_real conocidos (ocupacion de
    puerta ya finalizada, no en curso) -- ver CU-O19."""
    tid = tenant_id if tenant_id is not None else contexto_tenant_id()
    stmt = (
        select(
            asignacion_puerta.c.vuelo_id,
            asignacion_puerta.c.inicio_previsto,
            asignacion_puerta.c.inicio_real,
            asignacion_puerta.c.fin_real,
        )
        .select_from(asignacion_puerta.join(puerta, puerta.c.id == asignacion_puerta.c.puerta_id))
        .where(
            asignacion_puerta.c.tenant_id == tid,
            puerta.c.tenant_id == tid,
            puerta.c.terminal_id == terminal_id,
            asignacion_puerta.c.inicio_real.is_not(None),
            asignacion_puerta.c.fin_real.is_not(None),
        )
    )
    return [
        fila
        for fila in conn.execute(stmt)
        if fila.inicio_previsto is not None and fila.inicio_previsto.date() == fecha
    ]


def listar_turnarounds_de_vuelos(
    conn: Connection, *, vuelo_ids: list[int], tenant_id: int | None = None
) -> list[Row]:
    if not vuelo_ids:
        return []
    tid = tenant_id if tenant_id is not None else contexto_tenant_id()
    en_llegada = turnaround.c.vuelo_llegada_id.in_(vuelo_ids)
    en_salida = turnaround.c.vuelo_salida_id.in_(vuelo_ids)
    stmt = select(turnaround).where(
        turnaround.c.tenant_id == tid,
        (en_llegada | en_salida),
        turnaround.c.inicio_real.is_not(None),
        turnaround.c.fin_real.is_not(None),
    )
    return list(conn.execute(stmt))


def obtener_franja_existente(
    conn: Connection, *, terminal_id: int, fecha: date, franja_inicio: time,
    tenant_id: int | None = None,
) -> Row | None:
    stmt = select(tiempo_espera_agregado).where(
        tiempo_espera_agregado.c.tenant_id
        == (tenant_id if tenant_id is not None else contexto_tenant_id()),
        tiempo_espera_agregado.c.terminal_id == terminal_id,
        tiempo_espera_agregado.c.fecha == fecha,
        tiempo_espera_agregado.c.franja_inicio == franja_inicio,
    )
    return conn.execute(stmt).first()


def listar_tiempos_espera(conn: Connection, *, terminal_id: int, fecha: date) -> list[Row]:
    stmt = select(tiempo_espera_agregado).where(
        tiempo_espera_agregado.c.tenant_id == contexto_tenant_id(),
        tiempo_espera_agregado.c.terminal_id == terminal_id,
        tiempo_espera_agregado.c.fecha == fecha,
    )
    return list(conn.execute(stmt))
