"""Integracion HTTP de los informes operativos de M5 Billing (Sprint
S1.18) -- SC-002 (subtotales==total) y SC-003 (concilia con facturas
emitidas del periodo) contra MonetDB real. RF-I04: verifica que la
emision del informe compuesto queda en compliance.log_auditoria.
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


def _token_billing(datos_canario) -> str:
    return codificar_jwt(
        rol="role_billing_officer",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["billing:leer"],
    )


def test_informe_facturacion_compuesto_subtotales_igualan_total(client, datos_canario):
    token = _token_billing(datos_canario)
    r = client.get(
        "/billing/informes/compuesto",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    suma_subtotales = sum(float(g["subtotal"]) for g in cuerpo["grupos"])
    assert suma_subtotales == pytest.approx(float(cuerpo["total"]))


def test_informe_facturacion_concilia_con_facturas_emitidas(client, datos_canario):
    token = _token_billing(datos_canario)
    r_informe = client.get(
        "/billing/informes/compuesto",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    r_facturas = client.get(
        "/billing/facturas",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    assert r_informe.status_code == 200, r_informe.text
    assert r_facturas.status_code == 200, r_facturas.text
    total_informe = float(r_informe.json()["total"])
    total_facturas = sum(float(f["total"]) for f in r_facturas.json())
    assert total_informe == pytest.approx(total_facturas), (
        "SC-003: el informe de facturacion debe conciliar con las facturas emitidas del periodo"
    )


def test_informe_facturacion_registra_auditoria(client, datos_canario, admin_engine):
    token = _token_billing(datos_canario)
    with admin_engine.connect() as conn:
        antes = conn.execute(
            text(
                "SELECT count(*) AS n FROM compliance.log_auditoria "
                "WHERE tabla = 'informe_facturacion'"
            )
        ).fetchone()

    r = client.get(
        "/billing/informes/compuesto",
        params={"periodo_inicio": "2000-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    with admin_engine.connect() as conn:
        despues = conn.execute(
            text(
                "SELECT count(*) AS n FROM compliance.log_auditoria "
                "WHERE tabla = 'informe_facturacion'"
            )
        ).fetchone()
    assert despues.n > antes.n, "RF-I04: la emision del informe de facturacion debe auditarse"
