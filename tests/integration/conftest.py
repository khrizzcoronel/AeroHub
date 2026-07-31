"""Fixtures compartidas de tests/integration/ para las suites HTTP (Sprint
S1.1/S1.2): la app compuesta de `services/gateway/main.py`, el motor admin
y el guard de "MonetDB no disponible".

`services/gateway/main.py` se carga por ruta de archivo, no por import
normal -- es deliberadamente un script fuera de cualquier paquete
`aerohub_*` (ver el docstring de ese archivo: el contrato de independencia
de modulos de import-linter prohibe que un paquete de negocio importe a
otro, y la composicion de rutas de varios modulos en un solo proceso HTTP
tiene que vivir fuera de esa malla).
"""

from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

DSN_ADMIN = "monetdb://monetdb:aerohub@localhost:50000/aerohub"

_RUTA_MAIN = Path(__file__).resolve().parents[2] / "services" / "gateway" / "main.py"
_spec = importlib.util.spec_from_file_location("_aerohub_gateway_main_bajo_prueba", _RUTA_MAIN)
assert _spec is not None and _spec.loader is not None
gateway_main = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gateway_main
_spec.loader.exec_module(gateway_main)


@functools.lru_cache(maxsize=1)
def _hay_monetdb() -> bool:
    try:
        engine = create_engine(DSN_ADMIN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _requiere_monetdb():
    # autouse, no `pytestmark` a nivel de modulo -- no se propaga de forma
    # fiable entre modulos hermanos (mismo hallazgo que
    # tests/negative/conftest.py y tests/cross_tenant/conftest.py).
    if not _hay_monetdb():
        pytest.skip("MonetDB no disponible en localhost:50000")


@pytest.fixture()
def admin_engine():
    return create_engine(DSN_ADMIN)


@pytest.fixture()
def client():
    return TestClient(gateway_main.crear_app())
