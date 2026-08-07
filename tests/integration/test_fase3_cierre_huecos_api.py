"""Integracion HTTP de la Fase 3 de docs/diseno/PLAN_CORRECCION_MODULOS.md
(2026-08-07): cierre de 3 huecos reales de API -- `GET /vuelos` (causa
raiz D: la vista nucleo de M1 no podia listar nada al entrar), CRUD de
terminal/puerta en M3 (nunca existio alta/edicion, solo el tablero de
solo lectura), y la linea de tiempo de transiciones de estado de un
ticket D6 (el dato ya se auditaba desde S1.8, no estaba expuesto).
`client`/`admin_engine` vienen de tests/integration/conftest.py, mismo
patron que test_soporte_hub.py/test_compliance_hub.py.
"""

from __future__ import annotations

import secrets

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, rol: str, tenant_id: int | None, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario_mec = None
        terminal = None
        ticket = None
        if mec is not None:
            usuario_mec = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
            terminal = conn.execute(
                text("SELECT id FROM ops.terminal WHERE tenant_id = :t AND codigo = 'T1'"),
                {"t": mec.id},
            ).fetchone()
            ticket = conn.execute(
                text("SELECT id FROM support.ticket WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
    faltantes = (mec, usuario_mec, terminal, ticket)
    if any(f is None for f in faltantes):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "usuario_id": usuario_mec.id,
        "terminal_id": terminal.id,
        "ticket_id": ticket.id,
    }


# ---------------------------------------------------------------------------
# Item 6: GET /vuelos
# ---------------------------------------------------------------------------


def test_listar_vuelos_devuelve_al_menos_el_vuelo_canario(client, datos_canario):
    token = _token(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:leer"],
    )
    r = client.get("/vuelos", headers=_auth(token))
    assert r.status_code == 200
    numeros = {v["numero_vuelo"] for v in r.json()}
    assert "XX100" in numeros


def test_listar_vuelos_filtra_por_codigo_estado(client, datos_canario):
    token = _token(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:leer"],
    )
    r = client.get("/vuelos", params={"codigo_estado": "programado"}, headers=_auth(token))
    assert r.status_code == 200
    assert all(v["codigo_estado"] == "programado" for v in r.json())


def test_listar_vuelos_sin_scope_es_403(client, datos_canario):
    token = _token(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=[],
    )
    r = client.get("/vuelos", headers=_auth(token))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Item 7: CRUD de terminal y puerta
# ---------------------------------------------------------------------------


def test_ciclo_terminal_y_puerta_crear_listar_editar(client, datos_canario):
    token = _token(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["puertas:leer", "puertas:escribir"],
    )
    sufijo = secrets.token_hex(3).upper()

    r = client.post(
        "/puertas/terminales",
        json={"codigo": f"F3{sufijo}", "nombre": "Terminal Fase 3"},
        headers=_auth(token),
    )
    assert r.status_code == 201
    terminal_id = int(r.json()["terminal_id"])

    r = client.get("/puertas/terminales", headers=_auth(token))
    assert r.status_code == 200
    assert any(int(t["id"]) == terminal_id for t in r.json())

    r = client.post(
        "/puertas",
        json={
            "terminal_id": terminal_id,
            "codigo": f"G{sufijo}",
            "tipo": "contacto",
            "envergadura_max_m": 36.0,
            "tiene_pasarela": True,
        },
        headers=_auth(token),
    )
    assert r.status_code == 201
    puerta_id = int(r.json()["puerta_id"])

    r = client.patch(
        f"/puertas/{puerta_id}",
        json={
            "terminal_id": terminal_id,
            "codigo": f"G{sufijo}",
            "tipo": "remota",
            "envergadura_max_m": 20.0,
            "tiene_pasarela": False,
        },
        headers=_auth(token),
    )
    assert r.status_code == 204


def test_crear_puerta_con_codigo_duplicado_es_409(client, datos_canario):
    token = _token(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["puertas:leer", "puertas:escribir"],
    )
    sufijo = secrets.token_hex(3).upper()
    cuerpo = {
        "terminal_id": datos_canario["terminal_id"],
        "codigo": f"D{sufijo}",
        "tipo": "contacto",
        "envergadura_max_m": 36.0,
        "tiene_pasarela": False,
    }
    r1 = client.post("/puertas", json=cuerpo, headers=_auth(token))
    assert r1.status_code == 201
    r2 = client.post("/puertas", json=cuerpo, headers=_auth(token))
    assert r2.status_code == 409


def test_crear_puerta_con_tipo_invalido_es_422(client, datos_canario):
    token = _token(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["puertas:leer", "puertas:escribir"],
    )
    r = client.post(
        "/puertas",
        json={
            "terminal_id": datos_canario["terminal_id"],
            "codigo": f"X{secrets.token_hex(3).upper()}",
            "tipo": "no_existe",
            "envergadura_max_m": 36.0,
            "tiene_pasarela": False,
        },
        headers=_auth(token),
    )
    assert r.status_code == 422


def test_crear_puerta_sin_scope_escritura_es_403(client, datos_canario):
    # role_tenant_admin perdio puertas:escribir en la Fase 1 de este mismo
    # plan (D1(a)) -- confirma que el hueco cerrado en Fase 3 respeta esa
    # decision, no la revierte.
    token = _token(
        rol="role_tenant_admin",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["puertas:leer"],
    )
    r = client.post(
        "/puertas/terminales",
        json={"codigo": f"NO{secrets.token_hex(2).upper()}", "nombre": "No deberia crearse"},
        headers=_auth(token),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Item 8: trazabilidad de transiciones de ticket
# ---------------------------------------------------------------------------


def test_transiciones_de_ticket_reflejan_cambio_de_estado(client, datos_canario):
    token_support = _token(
        rol="role_support",
        tenant_id=None,
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer", "support:escribir"],
    )
    ticket_id = datos_canario["ticket_id"]

    r_antes = client.get(f"/support/tickets/{ticket_id}/transiciones", headers=_auth(token_support))
    assert r_antes.status_code == 200
    cantidad_antes = len(r_antes.json())

    r_cambio = client.patch(
        f"/support/tickets/{ticket_id}/estado",
        json={"estado": "en_progreso"},
        headers=_auth(token_support),
    )
    assert r_cambio.status_code in (200, 409)  # 409 si otra suite ya lo movio de estado

    r_despues = client.get(
        f"/support/tickets/{ticket_id}/transiciones", headers=_auth(token_support)
    )
    assert r_despues.status_code == 200
    if r_cambio.status_code == 200:
        assert len(r_despues.json()) == cantidad_antes + 1
        ultima = r_despues.json()[-1]
        assert ultima["estado_nuevo"] == "en_progreso"
        assert ultima["rol_codigo"] == "role_support"


def test_transiciones_de_ticket_visibles_para_tenant_admin_de_su_propio_tenant(
    client, datos_canario
):
    # Decision explicita del usuario (Fase 3): role_tenant_admin tiene
    # GRANT nuevo sobre compliance.log_auditoria para poder ver esto,
    # ademas de role_support.
    token_admin = _token(
        rol="role_tenant_admin",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer"],
    )
    r = client.get(
        f"/support/tickets/{datos_canario['ticket_id']}/transiciones", headers=_auth(token_admin)
    )
    assert r.status_code == 200


def test_transiciones_de_ticket_inexistente_es_404(client, datos_canario):
    token_support = _token(
        rol="role_support",
        tenant_id=None,
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer"],
    )
    r = client.get("/support/tickets/1/transiciones", headers=_auth(token_support))
    assert r.status_code == 404
