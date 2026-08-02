"""Compuertas de pruebas de S1.9 (Plan Sec8.9, US4): prueba de
restauracion forzada contra `monetdb-restore-test` real -- fila resultante
en `prueba_restauracion` con RTO/RPO observados; un snapshot 'corrupto'
nunca se elige como origen -- Escenario 4 de quickstart.md.
"""

from __future__ import annotations

import functools
import os

import httpx
import pytest
from sqlalchemy import create_engine, text


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


@pytest.fixture()
def restore_test_engine():
    return create_engine("monetdb://monetdb:aerohub@monetdb-restore-test:50000/aerohub")


def test_prueba_de_restauracion_forzada_queda_registrada_con_metricas(admin_engine):
    from aerohub_continuidad.operaciones.restauracion import ejecutar_prueba_restauracion
    from aerohub_continuidad.operaciones.snapshot import ejecutar_ciclo_snapshot

    snapshot = ejecutar_ciclo_snapshot(tipo="volcado_diario")
    assert snapshot.estado == "verificado"

    resultado = ejecutar_prueba_restauracion()
    assert resultado.resultado == "exitosa"
    assert resultado.rto_observado_segundos is not None and resultado.rto_observado_segundos >= 0
    assert resultado.rpo_observado_segundos is not None and resultado.rpo_observado_segundos >= 0

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT resultado, rto_observado_segundos, rpo_observado_segundos "
                "FROM continuidad.prueba_restauracion ORDER BY ejecutado_en DESC LIMIT 1"
            )
        ).fetchone()
    assert fila is not None
    assert fila.resultado == "exitosa"


def test_datos_restaurados_aparecen_en_el_contenedor_de_prueba(admin_engine, restore_test_engine):
    from aerohub_continuidad.operaciones.restauracion import ejecutar_prueba_restauracion
    from aerohub_continuidad.operaciones.snapshot import ejecutar_ciclo_snapshot

    ejecutar_ciclo_snapshot(tipo="volcado_diario")
    ejecutar_prueba_restauracion()

    consulta = text("SELECT COUNT(*) FROM support.categoria_ticket")
    with admin_engine.connect() as conn:
        total_primario = conn.execute(consulta).scalar_one()
    with restore_test_engine.connect() as conn:
        total_restaurado = conn.execute(consulta).scalar_one()
    assert total_restaurado == total_primario
    assert total_restaurado > 0


def test_snapshot_corrupto_nunca_se_elige_como_origen(admin_engine):
    from aerohub_continuidad.operaciones.snapshot import obtener_ultimo_snapshot_verificado_de_tipo
    from aerohub_kernel import ahora_utc, generar_id

    snapshot_corrupto_id = generar_id()
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO continuidad.snapshot_base "
                "(id, tipo, lsn_corte, generado_en, ruta_artefacto, hash_artefacto, estado) "
                "VALUES (:id, 'volcado_diario', 0, :ahora, "
                "'volcado_diario/no-existe.tar', :hash, 'corrupto')"
            ),
            {"id": snapshot_corrupto_id, "ahora": ahora_utc(), "hash": "0" * 64},
        )

    ultimo = obtener_ultimo_snapshot_verificado_de_tipo("volcado_diario")
    assert ultimo is None or ultimo["id"] != snapshot_corrupto_id
