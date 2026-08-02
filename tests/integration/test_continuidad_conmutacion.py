"""Compuertas de pruebas de S1.9 (Plan Sec8.9, US3): los 3 casos del
preflight de conmutacion -- atraso 0 (codigo 0), atraso bajo el umbral
(codigo 0 con advertencia), atraso sobre el umbral (codigo 1) -- Escenario
3 de quickstart.md.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

_RUTA_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "continuidad_conmutar.py"
_spec = importlib.util.spec_from_file_location("_continuidad_conmutar_bajo_prueba", _RUTA_SCRIPT)
assert _spec is not None and _spec.loader is not None
continuidad_conmutar = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = continuidad_conmutar
_spec.loader.exec_module(continuidad_conmutar)


def _fijar_checkpoint_y_pendiente(admin_engine, *, segundos_atraso: float) -> None:
    """Deja el checkpoint del shipper una entrada por detras del maximo,
    con esa entrada fechada `segundos_atraso` en el pasado -- simula un
    atraso real sin depender de que el shipper este realmente detenido."""
    from aerohub_kernel import generar_id

    lsn_pendiente = generar_id()
    ocurrido_en = datetime.now(UTC) - timedelta(seconds=segundos_atraso)
    with admin_engine.begin() as conn:
        # operacion='DDL' -- el shipper la omite explicitamente (nunca
        # intenta re-consultarla ni aplicarla), asi que esta entrada
        # sintetica solo sirve para simular atraso sin arriesgar un error
        # real si algun ciclo del agente en curso la procesa.
        conn.execute(
            text(
                "INSERT INTO continuidad.journal_mutacion "
                "(lsn, esquema, tabla, operacion, clave_primaria, payload, "
                "ocurrido_en, checksum_sha256) "
                "VALUES (:lsn, 'continuidad', 'prueba_conmutacion', 'DDL', "
                ":pk, :payload, :ocurrido, :checksum)"
            ),
            {
                "lsn": lsn_pendiente,
                "pk": '{"id": 1}',
                "payload": '{"id": 1}',
                "ocurrido": ocurrido_en,
                "checksum": "0" * 64,
            },
        )
        existe = conn.execute(
            text(
                "SELECT 1 FROM continuidad.shipper_checkpoint "
                "WHERE standby_nombre = 'monetdb-standby'"
            )
        ).first()
        if existe is None:
            conn.execute(
                text(
                    "INSERT INTO continuidad.shipper_checkpoint "
                    "(id, standby_nombre, ultimo_lsn_aplicado) "
                    "VALUES (:id, 'monetdb-standby', :lsn)"
                ),
                {"id": generar_id(), "lsn": lsn_pendiente - 1},
            )
        else:
            conn.execute(
                text(
                    "UPDATE continuidad.shipper_checkpoint SET ultimo_lsn_aplicado = :lsn "
                    "WHERE standby_nombre = 'monetdb-standby'"
                ),
                {"lsn": lsn_pendiente - 1},
            )


def _marcar_al_dia(admin_engine) -> None:
    with admin_engine.begin() as conn:
        maximo = conn.execute(
            text("SELECT COALESCE(MAX(lsn), 0) FROM continuidad.journal_mutacion")
        ).scalar_one()
        conn.execute(
            text(
                "UPDATE continuidad.shipper_checkpoint SET ultimo_lsn_aplicado = :lsn "
                "WHERE standby_nombre = 'monetdb-standby'"
            ),
            {"lsn": maximo},
        )


def test_preflight_ok_sin_atraso(admin_engine, capsys):
    _marcar_al_dia(admin_engine)
    codigo = continuidad_conmutar.main(["--standby", "monetdb-standby"])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "DSN sugerido" in salida


def test_preflight_advertencia_bajo_el_umbral(admin_engine, capsys):
    _fijar_checkpoint_y_pendiente(admin_engine, segundos_atraso=30)
    codigo = continuidad_conmutar.main(["--standby", "monetdb-standby"])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "ADVERTENCIA" in salida
    assert "DSN sugerido" in salida


def test_preflight_rechaza_sobre_el_umbral(admin_engine, capsys):
    _fijar_checkpoint_y_pendiente(admin_engine, segundos_atraso=200)
    codigo = continuidad_conmutar.main(["--standby", "monetdb-standby"])
    assert codigo == 1
    capturado = capsys.readouterr()
    assert "DSN sugerido" not in (capturado.out + capturado.err)
