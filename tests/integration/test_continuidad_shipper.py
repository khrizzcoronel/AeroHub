"""Compuertas de pruebas de S1.9 (Plan Sec8.9, US2): el shipper replica una
mutacion real del primario al standby en orden, y reaplicar el mismo `lsn`
no produce efecto adicional -- Escenario 2 de quickstart.md.
"""

from __future__ import annotations

import json
import secrets

import pytest
from sqlalchemy import text


def _standby_engine():
    from sqlalchemy import create_engine

    return create_engine("monetdb://monetdb:aerohub@monetdb-standby:50000/aerohub")


@pytest.fixture()
def standby_engine():
    return _standby_engine()


@pytest.fixture(autouse=True)
def _checkpoint_al_dia(admin_engine):
    """El backlog historico de `journal_mutacion` (sprints S1.1-S1.8)
    referencia tenant_id/vuelo_id/etc. del PRIMARIO, que no coinciden con
    los ids generados al sembrar el standby por separado (Snowflake no es
    reproducible entre corridas) -- replicarlo generaria violaciones de
    FK ajenas al shipper. Se adelanta el checkpoint al `lsn` maximo actual
    ANTES de cada test, igual que corresponderia al conectar un standby
    recien restaurado desde un snapshot (ADR-018: el snapshot fija el
    punto de partida, el journal solo aporta el delta posterior) -- cada
    test solo ejercita el shipper contra las entradas NUEVAS que el
    propio test crea."""
    from aerohub_kernel import generar_id

    with admin_engine.begin() as conn:
        maximo = conn.execute(
            text("SELECT COALESCE(MAX(lsn), 0) FROM continuidad.journal_mutacion")
        ).scalar_one()
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
                {"id": generar_id(), "lsn": maximo},
            )
        else:
            conn.execute(
                text(
                    "UPDATE continuidad.shipper_checkpoint SET ultimo_lsn_aplicado = :lsn "
                    "WHERE standby_nombre = 'monetdb-standby'"
                ),
                {"lsn": maximo},
            )


def _insertar_categoria_y_journal(admin_engine, *, codigo: str, nombre: str) -> tuple[int, int]:
    from aerohub_kernel import generar_id

    categoria_id = generar_id()
    lsn = generar_id()
    with admin_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO support.categoria_ticket (id, codigo, nombre) VALUES (:id, :c, :n)"),
            {"id": categoria_id, "c": codigo, "n": nombre},
        )
        conn.execute(
            text(
                "INSERT INTO continuidad.journal_mutacion "
                "(lsn, esquema, tabla, operacion, clave_primaria, payload, checksum_sha256) "
                "VALUES (:lsn, 'support', 'categoria_ticket', 'INSERT', :pk, :payload, :checksum)"
            ),
            {
                "lsn": lsn,
                "pk": json.dumps({"id": categoria_id}),
                "payload": json.dumps({"id": categoria_id, "codigo": codigo}),
                "checksum": "0" * 64,
            },
        )
    return categoria_id, lsn


def test_shipper_replica_insercion_real_al_standby(admin_engine, standby_engine):
    from aerohub_continuidad.operaciones.shipper import ejecutar_ciclo_shipper

    codigo = f"TEST-{secrets.token_hex(4)}"
    categoria_id, _lsn = _insertar_categoria_y_journal(
        admin_engine, codigo=codigo, nombre="Categoria de prueba"
    )

    resultado = ejecutar_ciclo_shipper()
    assert resultado.aplicadas >= 1

    with standby_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT codigo, nombre FROM support.categoria_ticket WHERE id = :id"),
            {"id": categoria_id},
        ).fetchone()
    assert fila is not None
    assert fila.codigo == codigo
    assert fila.nombre == "Categoria de prueba"


def test_reaplicar_el_mismo_lsn_no_duplica_ni_falla(admin_engine, standby_engine):
    from aerohub_continuidad.operaciones.shipper import ejecutar_ciclo_shipper

    codigo = f"TEST-{secrets.token_hex(4)}"
    categoria_id, lsn = _insertar_categoria_y_journal(
        admin_engine, codigo=codigo, nombre="Version 1"
    )

    resultado_1 = ejecutar_ciclo_shipper()
    assert resultado_1.aplicadas >= 1

    with standby_engine.connect() as conn:
        version_1 = conn.execute(
            text("SELECT nombre FROM support.categoria_ticket WHERE id = :id"),
            {"id": categoria_id},
        ).fetchone()
    assert version_1.nombre == "Version 1"

    # Simula un reproceso: retrocede el checkpoint por debajo de este lsn y
    # vuelve a correr el ciclo -- debe re-aplicar sin duplicar la fila ni
    # fallar (idempotencia, FR-007).
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE continuidad.shipper_checkpoint SET ultimo_lsn_aplicado = :lsn_previo "
                "WHERE standby_nombre = 'monetdb-standby'"
            ),
            {"lsn_previo": lsn - 1},
        )

    resultado_2 = ejecutar_ciclo_shipper()
    assert resultado_2.aplicadas >= 1

    with standby_engine.connect() as conn:
        filas = conn.execute(
            text("SELECT nombre FROM support.categoria_ticket WHERE id = :id"), {"id": categoria_id}
        ).fetchall()
    assert len(filas) == 1
    assert filas[0].nombre == "Version 1"


def test_shipper_replica_actualizacion(admin_engine, standby_engine):
    from aerohub_continuidad.operaciones.shipper import ejecutar_ciclo_shipper
    from aerohub_kernel import generar_id

    codigo = f"TEST-{secrets.token_hex(4)}"
    categoria_id, _lsn = _insertar_categoria_y_journal(admin_engine, codigo=codigo, nombre="Antes")
    ejecutar_ciclo_shipper()

    lsn_update = generar_id()
    with admin_engine.begin() as conn:
        conn.execute(
            text("UPDATE support.categoria_ticket SET nombre = 'Despues' WHERE id = :id"),
            {"id": categoria_id},
        )
        conn.execute(
            text(
                "INSERT INTO continuidad.journal_mutacion "
                "(lsn, esquema, tabla, operacion, clave_primaria, payload, checksum_sha256) "
                "VALUES (:lsn, 'support', 'categoria_ticket', 'UPDATE', :pk, :payload, :checksum)"
            ),
            {
                "lsn": lsn_update,
                "pk": json.dumps({"id": categoria_id}),
                "payload": json.dumps({"id": categoria_id, "nombre": "Despues"}),
                "checksum": "0" * 64,
            },
        )

    resultado = ejecutar_ciclo_shipper()
    assert resultado.aplicadas >= 1

    with standby_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT nombre FROM support.categoria_ticket WHERE id = :id"), {"id": categoria_id}
        ).fetchone()
    assert fila.nombre == "Despues"
