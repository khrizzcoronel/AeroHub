"""Integracion HTTP de los informes operativos de Tenancy (Sprint
S1.18) -- SC-002 contra MonetDB real. Alcance 'interno' (sin filtro de
tenant, mismo criterio que GET /tenants).
"""

from __future__ import annotations

from aerohub_gateway.infrastructure import codificar_jwt


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_informe_tenants_compuesto_subtotales_igualan_total(client):
    token = codificar_jwt(
        rol="role_platform_admin", tenant_id=None, usuario_id=1, scopes=["tenants:administrar"]
    )
    r = client.get("/tenants/informes/compuesto", headers=_auth(token))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    suma_subtotales = sum(g["subtotal"] for g in cuerpo["grupos"])
    assert suma_subtotales == cuerpo["total"]


def test_informe_tenants_simple_json(client):
    token = codificar_jwt(
        rol="role_platform_admin", tenant_id=None, usuario_id=1, scopes=["tenants:administrar"]
    )
    r = client.get("/tenants/informes/simple", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert "filas" in r.json()
