"""Escritura de ops.asignacion_puerta (Sprint S1.4). Solo persiste --
domain/ ya valido, application/ ya genero el id y decide journal/auditoria.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import asignacion_puerta, puerta, terminal


def bloquear_puerta_para_asignacion(conn: Connection, *, tenant_id: int, puerta_id: int) -> None:
    """"Bloqueo de fila" sobre `puerta_id` (SDD-DATA-001 §7.5): MonetDB no
    admite `SELECT ... FOR UPDATE` (verificado empiricamente -- error de
    sintaxis). Un UPDATE sin efecto sobre la fila de la puerta fuerza un
    conflicto de escritura real en el motor entre dos transacciones
    concurrentes que intentan asignar la MISMA puerta, siempre que ambas
    ejecuten esto ANTES de leer las asignaciones existentes (ver
    aerohub_gates.application.asignar_puerta). Combinado con
    `aerohub_repository.reintentar_en_conflicto`, la transaccion que pierde
    la carrera se reintenta -- y en su segunda pasada SI ve la asignacion
    que la otra ya confirmo, detectando el solapamiento (PN-05, variante
    concurrente).
    """
    conn.execute(
        update(puerta)
        .where(puerta.c.tenant_id == tenant_id, puerta.c.id == puerta_id)
        .values(codigo=puerta.c.codigo)
    )


def insertar_asignacion_puerta(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    vuelo_id: int,
    puerta_id: int,
    inicio_previsto: datetime,
    fin_previsto: datetime,
    asignado_por_usuario_id: int,
) -> None:
    conn.execute(
        insert(asignacion_puerta).values(
            id=id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            puerta_id=puerta_id,
            inicio_previsto=inicio_previsto,
            fin_previsto=fin_previsto,
            asignado_por_usuario_id=asignado_por_usuario_id,
            estado="planificada",
        )
    )


def cancelar_asignacion_puerta(conn: Connection, *, id: int, tenant_id: int) -> None:
    conn.execute(
        update(asignacion_puerta)
        .where(asignacion_puerta.c.id == id, asignacion_puerta.c.tenant_id == tenant_id)
        .values(estado="cancelada")
    )


def insertar_terminal(
    conn: Connection, *, id: int, tenant_id: int, codigo: str, nombre: str
) -> None:
    conn.execute(insert(terminal).values(id=id, tenant_id=tenant_id, codigo=codigo, nombre=nombre))


def insertar_puerta(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    terminal_id: int,
    codigo: str,
    tipo: str,
    envergadura_max_m: float,
    tiene_pasarela: bool,
) -> None:
    conn.execute(
        insert(puerta).values(
            id=id,
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            codigo=codigo,
            tipo=tipo,
            envergadura_max_m=envergadura_max_m,
            tiene_pasarela=tiene_pasarela,
        )
    )


def actualizar_puerta(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    terminal_id: int,
    codigo: str,
    tipo: str,
    envergadura_max_m: float,
    tiene_pasarela: bool,
) -> None:
    conn.execute(
        update(puerta)
        .where(puerta.c.id == id, puerta.c.tenant_id == tenant_id)
        .values(
            terminal_id=terminal_id,
            codigo=codigo,
            tipo=tipo,
            envergadura_max_m=envergadura_max_m,
            tiene_pasarela=tiene_pasarela,
        )
    )
