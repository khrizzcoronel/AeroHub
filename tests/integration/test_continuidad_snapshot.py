"""Compuertas de pruebas de S1.9 (Plan Sec8.9, US1): ciclo de snapshot
forzado contra MonetDB + MinIO reales, catalogo verificado -- Escenario 1
de quickstart.md.
"""

from __future__ import annotations

import functools
import os

import httpx
import pytest
from sqlalchemy import text


def _minio_endpoint() -> str:
    return os.environ.get("AEROHUB_MINIO_ENDPOINT", "http://localhost:9002")


@functools.lru_cache(maxsize=1)
def _hay_minio() -> bool:
    try:
        r = httpx.get(f"{_minio_endpoint()}/minio/health/live", timeout=2.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(autouse=True)
def _requiere_minio():
    if not _hay_minio():
        pytest.skip(f"MinIO no disponible en {_minio_endpoint()}")


def test_ciclo_de_snapshot_programado_queda_verificado_y_catalogado(admin_engine):
    from aerohub_continuidad.operaciones.snapshot import ejecutar_ciclo_snapshot

    resultado = ejecutar_ciclo_snapshot(tipo="programado")
    assert resultado.estado == "verificado", resultado

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT tipo, estado, hash_artefacto, lsn_corte, ruta_artefacto "
                "FROM continuidad.snapshot_base WHERE id = :id"
            ),
            {"id": resultado.snapshot_id},
        ).fetchone()
    assert fila is not None
    assert fila.tipo == "programado"
    assert fila.estado == "verificado"
    assert fila.hash_artefacto is not None and len(fila.hash_artefacto) == 64
    assert fila.lsn_corte is not None
    assert fila.ruta_artefacto is not None


def test_ultimo_snapshot_verificado_es_consultable(admin_engine):
    from aerohub_continuidad.operaciones.snapshot import (
        ejecutar_ciclo_snapshot,
        obtener_ultimo_snapshot_verificado,
    )

    resultado = ejecutar_ciclo_snapshot(tipo="programado")
    assert resultado.estado == "verificado"

    ultimo = obtener_ultimo_snapshot_verificado()
    assert ultimo is not None
    assert ultimo["id"] == resultado.snapshot_id
