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


def _puerto_abierto(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@functools.lru_cache(maxsize=1)
def _hay_monetdb() -> bool:
    """Cacheado a nivel de proceso -- ver la nota en tests/negative/conftest.py."""
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
def _requiere_monetdb():
    """autouse=True, no `pytestmark` a nivel de conftest.py -- ver la nota
    en tests/negative/conftest.py, donde se detecto que ese patron no se
    propaga de forma fiable a los modulos hermanos.
    """
    if not _hay_monetdb():
        pytest.skip(f"MonetDB no disponible en {_DB_HOST}:50000")


@pytest.fixture()
def admin_engine():
    return create_engine(DSN_ADMIN)


@pytest.fixture()
def canarios(admin_engine):
    """(tenant_id, usuario_id, vuelo_id, api_key_id) de los canarios
    sembrados por db/seeds/generate.py (Plan §7.2, ampliado en S1.1 con un
    vuelo por tenant y en S1.2 con una api_key por tenant). Falla con un
    mensaje claro si el seed no corrio -- estas filas son un requisito de
    entorno, no algo que este test deba crear.
    """
    with admin_engine.connect() as conn:
        filas = {}
        for codigo in ("MEC", "UIO"):
            fila = conn.execute(
                text(
                    "SELECT t.id, u.id FROM tenants.tenant t "
                    "JOIN tenants.usuario u ON u.tenant_id = t.id "
                    "WHERE t.codigo = :c AND u.email = :e"
                ),
                {"c": codigo, "e": f"canario@{codigo.lower()}.aerohub.test"},
            ).fetchone()
            if fila is None:
                pytest.fail(
                    f"Canario de {codigo} no encontrado -- ejecutar "
                    "'uv run python -m db.seeds.generate' antes de esta suite."
                )
            tenant_id, usuario_id = fila
            fila_vuelo = conn.execute(
                text("SELECT id FROM ops.vuelo WHERE tenant_id = :t"), {"t": tenant_id}
            ).fetchone()
            if fila_vuelo is None:
                pytest.fail(
                    f"Vuelo canario de {codigo} no encontrado -- ejecutar "
                    "'uv run python -m db.seeds.generate' antes de esta suite."
                )
            fila_api_key = conn.execute(
                text("SELECT id FROM tenants.api_key WHERE tenant_id = :t"), {"t": tenant_id}
            ).fetchone()
            if fila_api_key is None:
                pytest.fail(
                    f"Api key canaria de {codigo} no encontrada -- ejecutar "
                    "'uv run python -m db.seeds.generate' antes de esta suite."
                )
            filas[codigo] = {
                "tenant_id": tenant_id,
                "usuario_id": usuario_id,
                "vuelo_id": fila_vuelo[0],
                "api_key_id": fila_api_key[0],
            }
    return filas
