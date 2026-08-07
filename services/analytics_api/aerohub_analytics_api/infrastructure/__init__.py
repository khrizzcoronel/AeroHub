"""Único punto de conexión hacia ClickHouse (M7, ADR-012/013 -- ClickHouse
es la capa analítica dual, separada de MonetDB). Mismo patrón de
`aerohub_repository.base`: engine/cliente de proceso único, DSN por
variables de entorno con default de desarrollo.

**Alcance de este sprint** (pedido directo del usuario, 2026-08-05):
tabla mínima de demostración (`ah_tactico_demo.compuesto_informe`), NO
la ingesta medallion completa (bronce→plata→oro) que la Fase 2
(S2.1-S2.4, `docs/PLAN_IMPLEMENTACION_v3.0.md` §9) todavía no construyó.
Se documenta así para que nadie confunda esto con `ah_tactico` real --
cuando la Fase 2 exista, esta tabla y su sincronización manual
(`tools/sincronizar_analytics_demo.py`) se retiran.
"""

from __future__ import annotations

import os
from datetime import datetime

import clickhouse_connect
from clickhouse_connect.driver.client import Client

_client: Client | None = None

_ESQUEMA = "ah_tactico_demo"
_TABLA = "compuesto_informe"


def obtener_cliente() -> Client:
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=os.environ.get("AEROHUB_CLICKHOUSE_HOST", "localhost"),
            port=int(os.environ.get("AEROHUB_CLICKHOUSE_PORT", "8123")),
            username=os.environ.get("AEROHUB_CLICKHOUSE_USER", "aerohub"),
            password=os.environ.get("AEROHUB_CLICKHOUSE_PASSWORD", "aerohub"),
        )
    return _client


def asegurar_esquema() -> None:
    """Idempotente -- crea la base/tabla demo si todavía no existen (mismo
    criterio que los seeds de MonetDB: nunca falla si ya están creadas)."""
    cliente = obtener_cliente()
    cliente.command(f"CREATE DATABASE IF NOT EXISTS {_ESQUEMA}")
    cliente.command(
        f"""
        CREATE TABLE IF NOT EXISTS {_ESQUEMA}.{_TABLA} (
            modulo_codigo String,
            clave_grupo String,
            subtotal Int64,
            metrica_principal String,
            total_general Int64,
            calculado_en DateTime
        ) ENGINE = MergeTree()
        ORDER BY (modulo_codigo, clave_grupo)
        """
    )


def reemplazar_filas_modulo(
    modulo_codigo: str,
    *,
    filas: list[tuple[str, int, str, int]],
    calculado_en: datetime,
) -> None:
    """Sincronización manual (demo) -- borra las filas anteriores del
    módulo y escribe el snapshot nuevo. No es un INSERT incremental
    porque el "compuesto" siempre representa el estado agregado actual,
    no una serie histórica que haya que acumular."""
    cliente = obtener_cliente()
    cliente.command(
        f"ALTER TABLE {_ESQUEMA}.{_TABLA} DELETE WHERE modulo_codigo = %(m)s",
        parameters={"m": modulo_codigo},
    )
    if not filas:
        return
    datos = [
        [modulo_codigo, clave, subtotal, metrica, total_general, calculado_en]
        for clave, subtotal, metrica, total_general in filas
    ]
    cliente.insert(
        f"{_ESQUEMA}.{_TABLA}",
        datos,
        column_names=[
            "modulo_codigo",
            "clave_grupo",
            "subtotal",
            "metrica_principal",
            "total_general",
            "calculado_en",
        ],
    )


def leer_filas_modulo(modulo_codigo: str) -> list[tuple[str, int, str, datetime]]:
    cliente = obtener_cliente()
    # bandit B608 -- falso positivo: el f-string solo interpola las
    # constantes internas _ESQUEMA/_TABLA (nunca dato de entrada); el
    # valor de usuario (modulo_codigo) viaja parametrizado via %(m)s.
    resultado = cliente.query(
        f"SELECT clave_grupo, subtotal, metrica_principal, calculado_en "  # nosec B608
        f"FROM {_ESQUEMA}.{_TABLA} WHERE modulo_codigo = %(m)s ORDER BY subtotal DESC",
        parameters={"m": modulo_codigo},
    )
    return [(str(f[0]), int(f[1]), str(f[2]), f[3]) for f in resultado.result_rows]


def leer_total_modulo(modulo_codigo: str) -> int:
    cliente = obtener_cliente()
    # bandit B608 -- mismo falso positivo que leer_filas_modulo: solo
    # constantes internas en el f-string, modulo_codigo va parametrizado.
    resultado = cliente.query(
        f"SELECT total_general FROM {_ESQUEMA}.{_TABLA} "  # nosec B608
        f"WHERE modulo_codigo = %(m)s LIMIT 1",
        parameters={"m": modulo_codigo},
    )
    filas = resultado.result_rows
    return int(filas[0][0]) if filas else 0
