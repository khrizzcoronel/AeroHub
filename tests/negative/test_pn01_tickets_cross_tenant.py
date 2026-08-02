"""PN-01 -- un ticket de soporte de un tenant nunca es accesible por un
usuario de otro tenant: 404, nunca 403 (no se confirma que el recurso ajeno
existe). Sprint S1.8, Escenario 1 de quickstart.md, paso 4.
"""

from __future__ import annotations

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_TENANT_ADMIN = "role_tenant_admin"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, tenant_id: int, usuario_id: int) -> str:
    return codificar_jwt(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=["support:leer", "support:escribir"],
    )


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        uio = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'UIO'")).fetchone()
        usuario_mec = usuario_uio = categoria = None
        if mec is not None:
            usuario_mec = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
        if uio is not None:
            usuario_uio = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": uio.id}
            ).fetchone()
        categoria = conn.execute(
            text("SELECT id FROM support.categoria_ticket WHERE codigo = 'AODB'")
        ).fetchone()
    faltante = mec is None or uio is None or usuario_mec is None or usuario_uio is None
    if faltante or categoria is None:
        pytest.fail(
            "Datos canario o categoria AODB no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_mec_id": mec.id,
        "usuario_mec_id": usuario_mec.id,
        "tenant_uio_id": uio.id,
        "usuario_uio_id": usuario_uio.id,
        "categoria_id": categoria.id,
    }


def test_ticket_de_otro_tenant_devuelve_404_no_403(client, datos_canario):
    token_mec = _token(
        tenant_id=datos_canario["tenant_mec_id"], usuario_id=datos_canario["usuario_mec_id"]
    )
    r = client.post(
        "/support/tickets",
        headers=_auth(token_mec),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "media",
            "asunto": "Ticket privado de MEC",
            "cuerpo_inicial": "Detalle sensible de MEC.",
        },
    )
    assert r.status_code == 201, r.text
    ticket_id = r.json()["ticket_id"]

    token_uio = _token(
        tenant_id=datos_canario["tenant_uio_id"], usuario_id=datos_canario["usuario_uio_id"]
    )
    r = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_uio))
    assert r.status_code == 404, r.text
    assert r.status_code != 403


def test_listado_de_tickets_no_incluye_los_de_otro_tenant(client, datos_canario):
    token_mec = _token(
        tenant_id=datos_canario["tenant_mec_id"], usuario_id=datos_canario["usuario_mec_id"]
    )
    r = client.post(
        "/support/tickets",
        headers=_auth(token_mec),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "baja",
            "asunto": "Otro ticket privado de MEC",
            "cuerpo_inicial": "Detalle.",
        },
    )
    ticket_id = r.json()["ticket_id"]

    token_uio = _token(
        tenant_id=datos_canario["tenant_uio_id"], usuario_id=datos_canario["usuario_uio_id"]
    )
    r = client.get("/support/tickets", headers=_auth(token_uio))
    assert r.status_code == 200, r.text
    assert ticket_id not in {t["id"] for t in r.json()}
