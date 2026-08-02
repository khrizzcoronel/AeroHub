"""Compuertas de pruebas de S1.8 (Plan Sec8.8, US2): uptime y error budget
del mes en curso, contra Prometheus real -- Escenario 2 de quickstart.md.
"""

from __future__ import annotations

import functools
import os

import httpx
import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"


def _prometheus_url() -> str:
    return os.environ.get("AEROHUB_PROMETHEUS_URL", "http://localhost:9090")


@functools.lru_cache(maxsize=1)
def _hay_prometheus() -> bool:
    try:
        r = httpx.get(f"{_prometheus_url()}/-/healthy", timeout=2.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(autouse=True)
def _requiere_prometheus():
    if not _hay_prometheus():
        pytest.skip(f"Prometheus no disponible en {_prometheus_url()}")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario = None
        if mec is not None:
            usuario = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
    if mec is None or usuario is None:
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {"tenant_id": mec.id, "usuario_id": usuario.id}


def _token(datos_canario) -> str:
    return codificar_jwt(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer"],
    )


@pytest.mark.parametrize("servicio", ["aodb", "fids"])
def test_uptime_y_error_budget_del_mes_en_curso(client, datos_canario, servicio):
    r = client.get(
        "/support/observabilidad/uptime",
        params={"servicio": servicio},
        headers=_auth(_token(datos_canario)),
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["servicio"] == servicio
    assert 0.0 <= cuerpo["uptime_pct"] <= 100.0
    assert cuerpo["error_budget_consumido_pct"] >= 0.0


def test_servicio_invalido_rechazado(client, datos_canario):
    r = client.get(
        "/support/observabilidad/uptime",
        params={"servicio": "billing"},
        headers=_auth(_token(datos_canario)),
    )
    assert r.status_code == 422, r.text
