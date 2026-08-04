"""Integracion HTTP de los informes operativos de M1 AODB (Sprint S1.18,
PLAN v3.0 §8-bis.4) -- verifica SC-002 (suma de subtotales == total)
contra MonetDB real. Mismo patron que
tests/integration/test_billing_tarifarios_conciliacion.py.
"""

from __future__ import annotations

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"


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


def test_informe_vuelos_compuesto_subtotales_igualan_total(client, datos_canario):
    token = codificar_jwt(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:leer"],
    )
    r = client.get(
        "/vuelos/informes/compuesto",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    suma_subtotales = sum(g["subtotal"] for g in cuerpo["grupos"])
    assert suma_subtotales == cuerpo["total"], "SC-002: suma de subtotales debe igualar el total"


def test_informe_vuelos_simple_filtra_por_periodo(client, datos_canario):
    token = codificar_jwt(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:leer"],
    )
    r = client.get(
        "/vuelos/informes/simple",
        params={"periodo_inicio": "1990-01-01", "periodo_fin": "1990-01-02"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["filas"] == []


def test_informe_vuelos_csv_declara_parametros_y_fecha(client, datos_canario):
    token = codificar_jwt(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:leer"],
    )
    r = client.get(
        "/vuelos/informes/simple",
        params={
            "periodo_inicio": "2000-01-01",
            "periodo_fin": "2030-01-01",
            "formato": "csv",
        },
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "periodo_inicio,2000-01-01" in r.text
    assert "generado_en," in r.text
