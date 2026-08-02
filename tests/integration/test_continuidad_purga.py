"""Compuertas de pruebas de S1.9 (Plan Sec8.9, US5): la purga del journal
respeta la ventana de retencion (48h) Y el avance confirmado del shipper --
nunca purga por delante de lo que el shipper ya aplico -- Escenario 5 de
quickstart.md.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text


@pytest.fixture(autouse=True)
def _restaurar_checkpoint_real_al_terminar(admin_engine):
    """Los tests manipulan `shipper_checkpoint` directamente para simular
    distintos escenarios de purga -- sin restaurarlo, el agente de
    continuidad REAL (corriendo en paralelo, US2) quedaria con un
    checkpoint adelantado artificialmente y saltaria entradas genuinas
    sin replicarlas de verdad. Al terminar cada test, se recalcula el
    `lsn` maximo real (excluyendo las entradas sinteticas de esquema
    'continuidad'/'prueba_purga' que este archivo crea) y se restaura ahi."""
    yield
    with admin_engine.begin() as conn:
        conn.execute(text("DELETE FROM continuidad.journal_mutacion WHERE tabla = 'prueba_purga'"))
        maximo_real = conn.execute(
            text("SELECT COALESCE(MAX(lsn), 0) FROM continuidad.journal_mutacion")
        ).scalar_one()
        conn.execute(
            text(
                "UPDATE continuidad.shipper_checkpoint SET ultimo_lsn_aplicado = :lsn "
                "WHERE standby_nombre = 'monetdb-standby'"
            ),
            {"lsn": maximo_real},
        )


def _insertar_entrada_journal(admin_engine, *, lsn: int, ocurrido_en) -> None:
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO continuidad.journal_mutacion "
                "(lsn, esquema, tabla, operacion, clave_primaria, payload, "
                "ocurrido_en, checksum_sha256) "
                "VALUES (:lsn, 'continuidad', 'prueba_purga', 'DDL', "
                ":pk, :payload, :ocurrido, :checksum)"
            ),
            {
                "lsn": lsn,
                "pk": '{"id": 1}',
                "payload": '{"id": 1}',
                "ocurrido": ocurrido_en,
                "checksum": "0" * 64,
            },
        )


def _fijar_checkpoint(admin_engine, *, ultimo_lsn: int) -> None:
    from aerohub_kernel import generar_id

    with admin_engine.begin() as conn:
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
                {"id": generar_id(), "lsn": ultimo_lsn},
            )
        else:
            conn.execute(
                text(
                    "UPDATE continuidad.shipper_checkpoint SET ultimo_lsn_aplicado = :lsn "
                    "WHERE standby_nombre = 'monetdb-standby'"
                ),
                {"lsn": ultimo_lsn},
            )


def _existe_lsn(admin_engine, lsn: int) -> bool:
    with admin_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT 1 FROM continuidad.journal_mutacion WHERE lsn = :lsn"), {"lsn": lsn}
        ).first()
    return fila is not None


def test_purga_elimina_entrada_antigua_y_confirmada(admin_engine):
    from aerohub_continuidad.operaciones.purga import purgar_journal_confirmado
    from aerohub_kernel import generar_id

    lsn_antiguo_confirmado = generar_id()
    hace_49_horas = datetime.now(UTC) - timedelta(hours=49)
    _insertar_entrada_journal(
        admin_engine, lsn=lsn_antiguo_confirmado, ocurrido_en=hace_49_horas
    )
    _fijar_checkpoint(admin_engine, ultimo_lsn=lsn_antiguo_confirmado)

    purgar_journal_confirmado()

    assert not _existe_lsn(admin_engine, lsn_antiguo_confirmado)


def test_purga_no_elimina_entrada_antigua_pero_no_confirmada(admin_engine):
    from aerohub_continuidad.operaciones.purga import purgar_journal_confirmado
    from aerohub_kernel import generar_id

    lsn_antiguo_sin_confirmar = generar_id()
    hace_49_horas = datetime.now(UTC) - timedelta(hours=49)
    _insertar_entrada_journal(
        admin_engine, lsn=lsn_antiguo_sin_confirmar, ocurrido_en=hace_49_horas
    )
    # Checkpoint por DEBAJO de esta entrada -- el shipper todavia no la aplico.
    _fijar_checkpoint(admin_engine, ultimo_lsn=lsn_antiguo_sin_confirmar - 1)

    purgar_journal_confirmado()

    assert _existe_lsn(admin_engine, lsn_antiguo_sin_confirmar)


def test_purga_no_elimina_entrada_reciente_aunque_este_confirmada(admin_engine):
    from aerohub_continuidad.operaciones.purga import purgar_journal_confirmado
    from aerohub_kernel import generar_id

    lsn_reciente_confirmado = generar_id()
    ahora = datetime.now(UTC)
    _insertar_entrada_journal(admin_engine, lsn=lsn_reciente_confirmado, ocurrido_en=ahora)
    _fijar_checkpoint(admin_engine, ultimo_lsn=lsn_reciente_confirmado)

    purgar_journal_confirmado()

    assert _existe_lsn(admin_engine, lsn_reciente_confirmado)
