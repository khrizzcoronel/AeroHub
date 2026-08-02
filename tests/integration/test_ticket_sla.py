"""Compuertas de pruebas de S1.8 (Plan Sec8.8, US1): ciclo completo de
ticket con SLA, primera_respuesta_en estable ante mensajes posteriores,
mensajes internos ocultos al tenant, transicion de estado invalida
rechazada -- Escenario 1 de quickstart.md.
"""

from __future__ import annotations

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_SUPPORT = "role_support"
_ROL_TENANT_ADMIN = "role_tenant_admin"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, rol: str, tenant_id: int | None, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


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


def _token_tenant_mec(datos_canario) -> str:
    return _token(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=datos_canario["tenant_mec_id"],
        usuario_id=datos_canario["usuario_mec_id"],
        scopes=["support:leer", "support:escribir"],
    )


def _token_support(datos_canario) -> str:
    return _token(
        rol=_ROL_SUPPORT,
        tenant_id=None,
        usuario_id=datos_canario["usuario_mec_id"],
        scopes=["support:leer", "support:escribir"],
    )


def test_ciclo_completo_ticket_con_sla(client, datos_canario):
    token_tenant = _token_tenant_mec(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token_tenant),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "alta",
            "asunto": "Vuelo retrasado por error de AODB",
            "cuerpo_inicial": "El vuelo XX100 muestra un estado incorrecto.",
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert int(cuerpo["sla_objetivo_min"]) < 120
    ticket_id = cuerpo["ticket_id"]

    token_support = _token_support(datos_canario)

    r = client.post(
        f"/support/tickets/{ticket_id}/mensajes",
        headers=_auth(token_support),
        json={"cuerpo": "Estamos investigando el incidente.", "es_interno": False},
    )
    assert r.status_code == 201, r.text

    r = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_support))
    assert r.status_code == 200, r.text
    primera_respuesta_1 = r.json()["ticket"]["primera_respuesta_en"]
    assert primera_respuesta_1 is not None

    r = client.post(
        f"/support/tickets/{ticket_id}/mensajes",
        headers=_auth(token_support),
        json={"cuerpo": "Nota interna de seguimiento.", "es_interno": True},
    )
    assert r.status_code == 201, r.text

    r = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_support))
    assert r.json()["ticket"]["primera_respuesta_en"] == primera_respuesta_1

    # El tenant no ve el mensaje interno (FR-004).
    r = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_tenant))
    assert r.status_code == 200, r.text
    mensajes = r.json()["mensajes"]
    assert all(not m["es_interno"] for m in mensajes)
    assert len(mensajes) == 2  # cuerpo_inicial + respuesta visible de soporte

    # PN-01: usuario de otro tenant recibe 404.
    token_uio = _token(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=datos_canario["tenant_uio_id"],
        usuario_id=datos_canario["usuario_uio_id"],
        scopes=["support:leer", "support:escribir"],
    )
    r = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_uio))
    assert r.status_code == 404, r.text


def test_tenant_no_puede_marcar_mensaje_interno(client, datos_canario):
    token_tenant = _token_tenant_mec(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token_tenant),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "media",
            "asunto": "Consulta general",
            "cuerpo_inicial": "Duda sobre el modulo.",
        },
    )
    ticket_id = r.json()["ticket_id"]

    r = client.post(
        f"/support/tickets/{ticket_id}/mensajes",
        headers=_auth(token_tenant),
        json={"cuerpo": "Intento marcar interno", "es_interno": True},
    )
    assert r.status_code == 403, r.text


def test_transicion_directa_de_abierto_a_resuelto_rechazada(client, datos_canario):
    token_tenant = _token_tenant_mec(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token_tenant),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "baja",
            "asunto": "Prueba de transicion de estado",
            "cuerpo_inicial": "Verificar que rechaza el salto de estado.",
        },
    )
    ticket_id = r.json()["ticket_id"]

    token_support = _token_support(datos_canario)
    r = client.patch(
        f"/support/tickets/{ticket_id}/estado",
        headers=_auth(token_support),
        json={"estado": "resuelto"},
    )
    assert r.status_code == 409, r.text


def test_tenant_no_puede_cambiar_estado(client, datos_canario):
    token_tenant = _token_tenant_mec(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token_tenant),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "baja",
            "asunto": "Otra prueba",
            "cuerpo_inicial": "x",
        },
    )
    ticket_id = r.json()["ticket_id"]

    r = client.patch(
        f"/support/tickets/{ticket_id}/estado",
        headers=_auth(token_tenant),
        json={"estado": "en_progreso"},
    )
    assert r.status_code == 403, r.text
