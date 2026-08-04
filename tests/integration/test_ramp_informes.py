"""Integracion HTTP de los informes operativos de M4 Ground Ops (Sprint
S1.18) -- SC-002 contra MonetDB real.
"""

from __future__ import annotations

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text


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
        pytest.fail("Datos canario no encontrados -- correr db.seeds.generate")
    return {"tenant_id": mec.id, "usuario_id": usuario.id}


def test_informe_turnarounds_compuesto_subtotales_igualan_total(client, datos_canario):
    token = codificar_jwt(
        rol="role_ramp_agent",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["rampa:leer"],
    )
    r = client.get(
        "/rampa/informes/compuesto",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    suma_subtotales = sum(g["subtotal"] for g in cuerpo["grupos"])
    assert suma_subtotales == cuerpo["total"]


def test_informe_turnarounds_simple_json(client, datos_canario):
    token = codificar_jwt(
        rol="role_ramp_agent",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["rampa:leer"],
    )
    r = client.get(
        "/rampa/informes/simple",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert "parametros" in r.json() and "generado_en" in r.json()
