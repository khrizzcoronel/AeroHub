"""Fixtures compartidas por la bateria de pruebas negativas (Plan §13).

Todas corren contra MonetDB real (docker-compose), nunca mockeado -- el
aislamiento que verifican vive en el motor, no en la capa de aplicacion
(salvo PN-15, que es analisis estatico de codigo fuente y no depende de
estas fixtures ni del fixture autouse de abajo).
"""

from __future__ import annotations

import functools
import os
import socket

import pytest
from sqlalchemy import create_engine, text

# Ver tests/integration/conftest.py -- mismo AEROHUB_TEST_DB_HOST, para
# poder correr esta suite dentro del contenedor del gateway.
_DB_HOST = os.environ.get("AEROHUB_TEST_DB_HOST", "localhost")
DSN_ADMIN = f"monetdb://monetdb:aerohub@{_DB_HOST}:50000/aerohub"
DSN_APP = f"monetdb://aerohub_app:aerohub_app_dev_password@{_DB_HOST}:50000/aerohub"


def _puerto_abierto(host: str, port: int, timeout: float = 1.0) -> bool:
    """Pre-chequeo TCP rapido: pymonetdb tarda demasiado en fallar contra un
    puerto cerrado (~4 min sobre toda la suite, medido en S0.2) -- sin esto,
    un entorno sin MonetDB hace que la compuerta de pruebas parezca
    colgada en vez de saltar limpiamente.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@functools.lru_cache(maxsize=1)
def _hay_monetdb() -> bool:
    """Cacheado a nivel de proceso: sin esto, el fixture autouse de abajo
    repite el chequeo de conexion en CADA uno de los ~66 tests de este
    directorio -- 132s solo para saltar todo cuando MonetDB esta apagado
    (medido en S0.2). Una corrida de pytest es un proceso nuevo cada vez,
    asi que este cache no esconde un MonetDB que se cae a mitad de la
    suite; solo evita repetir el mismo chequeo decenas de veces en la misma
    ejecucion.
    """
    if not _puerto_abierto(_DB_HOST, 50000):
        return False
    try:
        engine = create_engine(DSN_ADMIN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _requiere_monetdb(request):
    """autouse=True en conftest.py SI se aplica de forma fiable a todos los
    tests del directorio -- a diferencia de una variable `pytestmark` a
    nivel de conftest.py, que NO se propaga a los modulos hermanos (hallazgo
    real de S0.2: con MonetDB apagado, los tests fallaban con error de
    conexion en vez de saltarse, porque ese patron no funciona como parece).

    PN-15 (test_pn15_sql_fuera_del_repositorio.py) es analisis estatico
    puro y no necesita MonetDB -- se marca con `sin_bd` para eximirlo de
    este chequeo, en vez de quedar skippeado sin necesidad cuando el motor
    esta apagado.
    """
    if request.node.get_closest_marker("sin_bd") is not None:
        return
    if not _hay_monetdb():
        pytest.skip(f"MonetDB no disponible en {_DB_HOST}:50000")


@pytest.fixture()
def admin_engine():
    return create_engine(DSN_ADMIN)


@pytest.fixture()
def app_engine():
    """Motor conectado como aerohub_app, SIN el guardian de packages/repository
    registrado (estas pruebas verifican el MOTOR, no el guardian de S0.2 --
    ese ya tiene su propia suite en tests/unit/repository/test_guard.py).
    """
    return create_engine(DSN_APP)


@pytest.fixture()
def set_role():
    def _set_role(conn, rol: str) -> None:
        conn.exec_driver_sql(f'SET ROLE "{rol}"')

    return _set_role
