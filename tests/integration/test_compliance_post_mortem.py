"""Compuertas de pruebas de S1.7 (Plan Sec8.7): ciclo de vida completo de
post-mortem, exclusivo role_sre (ADR-009), y rechazo de publicacion con
remediacion incompleta (FR-005).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_SRE = "role_sre"
_ROL_SUPPORT = "role_support"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, rol: str, tenant_id: int, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


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


def _token_sre(datos_canario) -> str:
    return _token(
        rol=_ROL_SRE,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["compliance:leer", "compliance:escribir"],
    )


def test_ciclo_completo_post_mortem_con_role_sre(client, datos_canario):
    token = _token_sre(datos_canario)
    inicio = datetime.now(UTC)

    r = client.post(
        "/compliance/post-mortems",
        headers=_auth(token),
        json={
            "incidente_ref": "INC-TEST-001",
            "severidad": "alta",
            "iniciado_en": inicio.isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    post_mortem_id = r.json()["post_mortem_id"]

    r = client.patch(
        f"/compliance/post-mortems/{post_mortem_id}",
        headers=_auth(token),
        json={"causa_raiz": "Configuracion incorrecta de un timeout."},
    )
    assert r.status_code == 200, r.text

    r = client.post(
        f"/compliance/post-mortems/{post_mortem_id}/acciones",
        headers=_auth(token),
        json={
            "descripcion": "Ajustar el timeout en produccion",
            "responsable_usuario_id": str(datos_canario["usuario_id"]),
            "vence_en": (inicio + timedelta(days=1)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    accion_id = r.json()["accion_id"]

    # Con la accion sin completar, no se puede publicar (FR-005).
    r = client.post(f"/compliance/post-mortems/{post_mortem_id}/publicar", headers=_auth(token))
    assert r.status_code == 409, r.text

    r = client.post(
        f"/compliance/post-mortems/{post_mortem_id}/acciones/{accion_id}/completar",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    r = client.post(f"/compliance/post-mortems/{post_mortem_id}/publicar", headers=_auth(token))
    assert r.status_code == 200, r.text

    r = client.get(f"/compliance/post-mortems/{post_mortem_id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["post_mortem"]["estado"] == "publicado"
    assert cuerpo["post_mortem"]["causa_raiz"] == "Configuracion incorrecta de un timeout."
    assert cuerpo["post_mortem"]["publicado_en"] is not None


def test_role_support_no_puede_crear_post_mortem(client, datos_canario):
    token = _token(
        rol=_ROL_SUPPORT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["compliance:leer", "compliance:escribir"],
    )
    r = client.post(
        "/compliance/post-mortems",
        headers=_auth(token),
        json={
            "incidente_ref": "INC-TEST-002",
            "severidad": "baja",
            "iniciado_en": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 403, r.text


def test_edicion_de_causa_raiz_queda_auditada(client, datos_canario, admin_engine):
    token = _token_sre(datos_canario)
    r = client.post(
        "/compliance/post-mortems",
        headers=_auth(token),
        json={
            "incidente_ref": "INC-TEST-003",
            "severidad": "media",
            "iniciado_en": datetime.now(UTC).isoformat(),
        },
    )
    post_mortem_id = int(r.json()["post_mortem_id"])

    client.patch(
        f"/compliance/post-mortems/{post_mortem_id}",
        headers=_auth(token),
        json={"causa_raiz": "Primera hipotesis."},
    )

    with admin_engine.connect() as conn:
        n = conn.execute(
            text(
                "SELECT COUNT(*) FROM compliance.log_auditoria "
                "WHERE tabla = 'post_mortem' AND registro_id = :id AND operacion = 'UPDATE'"
            ),
            {"id": post_mortem_id},
        ).scalar_one()
    assert n >= 1, "la edicion de causa_raiz no quedo auditada (FR-007)"
