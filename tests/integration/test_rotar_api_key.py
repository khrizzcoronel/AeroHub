"""Compuerta de pruebas de S1.7 (RF-O12): rotar una API Key emite un
secreto nuevo sin perder acceso, marca la anterior revocada+rotada_en, y
audita el evento (SC-004).
"""

from __future__ import annotations

from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_PLATFORM_ADMIN = "role_platform_admin"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_rotar_api_key_emite_nueva_y_revoca_anterior(client, admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario = conn.execute(
            text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
        ).fetchone()

    token = codificar_jwt(
        rol=_ROL_PLATFORM_ADMIN,
        tenant_id=mec.id,
        usuario_id=usuario.id,
        scopes=["api-keys:administrar"],
    )

    r = client.post("/api-keys", headers=_auth(token))
    assert r.status_code == 201, r.text
    api_key_id_original = r.json()["api_key_id"]

    r = client.post(f"/api-keys/{api_key_id_original}/rotar", headers=_auth(token))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    api_key_id_nueva = cuerpo["api_key_id"]
    assert api_key_id_nueva != api_key_id_original
    assert "." in cuerpo["api_key_en_claro"]

    with admin_engine.connect() as conn:
        anterior = conn.execute(
            text("SELECT estado, rotada_en FROM tenants.api_key WHERE id = :id"),
            {"id": int(api_key_id_original)},
        ).fetchone()
        nueva = conn.execute(
            text("SELECT estado FROM tenants.api_key WHERE id = :id"), {"id": int(api_key_id_nueva)}
        ).fetchone()
        eventos_auditoria = conn.execute(
            text(
                "SELECT COUNT(*) FROM compliance.log_auditoria "
                "WHERE tabla = 'api_key' AND registro_id = :id AND operacion = 'UPDATE'"
            ),
            {"id": int(api_key_id_original)},
        ).scalar_one()

    assert anterior.estado == "revocada"
    assert anterior.rotada_en is not None
    assert nueva.estado == "activa"
    assert eventos_auditoria >= 1, "la rotacion no quedo auditada (SC-004)"
