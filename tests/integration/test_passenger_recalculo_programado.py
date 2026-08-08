"""Ciclo programado de recalculo de tiempos de espera (RF-O17, 2026-08-08).

Cubre lo que el ciclo tiene de distinto respecto del endpoint de CU-O19 ya
probado en S1.6: corre SIN tenant ambiente (bajo `alcance_global`, ADR-019
G3) y recorre todos los tenants, asi que lo que hay que verificar es que
(a) funciona sin contexto de peticion, (b) escribe cada fila con el tenant
de SU terminal y no con uno cualquiera, y (c) es idempotente -- corre cada
15 minutos sobre los mismos datos y no debe duplicar franjas.

`admin_engine` viene de tests/integration/conftest.py.
"""

from __future__ import annotations

import pytest
from aerohub_passenger.application import ejecutar_ciclo_recalculo
from aerohub_repository.contexto import ContextoTenantAusente, contexto_tenant_id
from sqlalchemy import text


@pytest.fixture()
def dia_con_datos(admin_engine):
    """Un dia que tenga asignaciones de puerta ya cerradas -- si no hay
    ninguna, el ciclo no tiene nada que agregar y el test no probaria nada."""
    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT CAST(MAX(inicio_previsto) AS DATE) AS dia "
                "FROM ops.asignacion_puerta WHERE fin_real IS NOT NULL"
            )
        ).fetchone()
    if fila is None or fila.dia is None:
        pytest.skip("sin asignaciones de puerta cerradas para agregar")
    return fila.dia


def test_el_ciclo_corre_sin_tenant_ambiente(dia_con_datos):
    """El ciclo es un proceso de plataforma: si dependiera de un tenant en
    el contexto, fallaria justo cuando corre de verdad (tarea de fondo del
    gateway, sin peticion HTTP detras)."""
    with pytest.raises(ContextoTenantAusente):
        contexto_tenant_id()

    resultado = ejecutar_ciclo_recalculo(fecha=dia_con_datos)

    assert resultado.terminales_evaluadas > 0
    assert resultado.terminales_con_error == 0


def test_cada_franja_queda_con_el_tenant_de_su_terminal(dia_con_datos, admin_engine):
    """El riesgo real de un proceso que cruza tenants es escribir la fila
    con el tenant equivocado -- eso seria una fuga entre tenants que ningun
    filtro de lectura podria reparar despues."""
    ejecutar_ciclo_recalculo(fecha=dia_con_datos)

    with admin_engine.connect() as conn:
        desalineadas = conn.execute(
            text(
                "SELECT COUNT(*) AS n "
                "FROM billing.tiempo_espera_agregado a "
                "JOIN ops.terminal t ON t.id = a.terminal_id "
                "WHERE a.tenant_id <> t.tenant_id"
            )
        ).fetchone()
    assert desalineadas.n == 0, "hay franjas escritas con un tenant distinto al de su terminal"


def test_el_ciclo_es_idempotente(dia_con_datos, admin_engine):
    """Corre cada 15 min sobre los mismos datos: la segunda pasada debe
    actualizar las mismas filas, nunca crear duplicados (la UNIQUE de
    12_billing.sql lo respalda, pero el caso de uso debe resolverlo antes
    de llegar al motor -- `obtener_franja_existente`)."""

    def contar() -> int:
        with admin_engine.connect() as conn:
            return conn.execute(
                text(
                    "SELECT COUNT(*) AS n FROM billing.tiempo_espera_agregado WHERE fecha = :d"
                ),
                {"d": dia_con_datos},
            ).fetchone().n

    ejecutar_ciclo_recalculo(fecha=dia_con_datos)
    despues_de_la_primera = contar()

    ejecutar_ciclo_recalculo(fecha=dia_con_datos)
    despues_de_la_segunda = contar()

    assert despues_de_la_segunda == despues_de_la_primera


def test_un_dia_sin_datos_no_publica_franjas_inventadas():
    """RF-O17: sin observaciones no se publica un estimado. Un dia sin
    ninguna asignacion cerrada debe dejar el resultado en cero, no en una
    fila con minutos 0."""
    from datetime import date

    resultado = ejecutar_ciclo_recalculo(fecha=date(1999, 1, 1))

    assert resultado.franjas_actualizadas == 0
