"""Integracion HTTP de los 4 hallazgos de la auditoria de la capa
operativa (2026-08-08).

Existen por la leccion de S1.20: aquel hallazgo (`support:*` inalcanzable
por cualquier rol) se le escapo a su propia suite porque los tests
fabricaban el JWT con `codificar_jwt(scopes=[...])` a mano en vez de
derivar los scopes de `roles_modulos.py`. Aca los scopes SIEMPRE salen de
`scopes_del_rol(...)`, para que un scope retirado del mapeo real rompa el
test en vez de quedar enmascarado.

Cubre:
- H1: M6 Passenger dejo de estar muerto (scope + GRANT alineados).
- H2: role_airline_coordinator puede escribir en M1 (GRANT ya existia).
- H3: recorte "solo sus itinerarios"/"sus cargos", incluido el
  comportamiento fail-closed sin aerolinea asignada.
- H4: informe "mis tareas" filtrado por el usuario de la sesion.

`client`/`admin_engine` vienen de tests/integration/conftest.py.
"""

from __future__ import annotations

import pytest
from aerohub_contracts.roles_modulos import scopes_del_rol
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(
    *, rol: str, tenant_id: int, usuario_id: int, aerolinea_id: int | None = None
) -> str:
    """Los scopes NUNCA se pasan a mano -- se derivan del mapeo real."""
    return codificar_jwt(
        rol=rol,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=sorted(scopes_del_rol(rol)),
        aerolinea_id=aerolinea_id,
    )


@pytest.fixture()
def canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        if mec is None:
            pytest.skip("tenant canario MEC no sembrado")
        aerolinea = conn.execute(text("SELECT id FROM catalogo.aerolinea LIMIT 1")).fetchone()
        terminal = conn.execute(
            text("SELECT id FROM ops.terminal WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
        ).fetchone()
        agente = conn.execute(
            text(
                "SELECT agente_usuario_id FROM rampa.tarea_turnaround "
                "WHERE tenant_id = :t AND agente_usuario_id IS NOT NULL LIMIT 1"
            ),
            {"t": mec.id},
        ).fetchone()
    if aerolinea is None:
        pytest.skip("catalogo.aerolinea vacio")
    return {
        "tenant_id": mec.id,
        "aerolinea_id": aerolinea.id,
        "terminal_id": terminal.id if terminal else None,
        "agente_usuario_id": agente.agente_usuario_id if agente else None,
    }


# --------------------------------------------------------------------
# H1 -- M6 Passenger
# --------------------------------------------------------------------


def test_h1_lectura_de_tiempos_espera_ya_no_muere_en_el_motor(client, canario):
    """Antes: 403 "acceso denegado" de motor -- los roles con el scope
    `passenger:leer` no tenian GRANT sobre billing.tiempo_espera_agregado."""
    if canario["terminal_id"] is None:
        pytest.skip("sin terminal sembrada")
    for rol in ("role_tenant_admin", "role_airline_coordinator"):
        tok = _token(rol=rol, tenant_id=canario["tenant_id"], usuario_id=1)
        r = client.get(
            "/passenger/tiempos-espera",
            params={"terminal_id": str(canario["terminal_id"]), "fecha": "2026-08-08"},
            headers=_auth(tok),
        )
        assert r.status_code == 200, f"{rol}: {r.status_code} {r.text[:120]}"


def test_h1_recalculo_alcanzable_por_role_operations_controller(client, canario):
    """CU-O19/RF-O17: `passenger:escribir` no lo tenia NINGUN rol, asi que
    este endpoint era inalcanzable por cualquier sesion humana desde S1.6."""
    if canario["terminal_id"] is None:
        pytest.skip("sin terminal sembrada")
    tok = _token(rol="role_operations_controller", tenant_id=canario["tenant_id"], usuario_id=1)
    r = client.post(
        "/passenger/tiempos-espera/recalcular",
        json={"terminal_id": str(canario["terminal_id"]), "fecha": "2026-08-08"},
        headers=_auth(tok),
    )
    assert r.status_code == 200, r.text[:160]
    assert "franjas_actualizadas" in r.json()


def test_h1_recalculo_sigue_negado_a_quien_solo_lee(client, canario):
    """El arreglo no debe volverse un permiso general: quien solo tiene
    `passenger:leer` sigue sin poder disparar el recalculo."""
    if canario["terminal_id"] is None:
        pytest.skip("sin terminal sembrada")
    tok = _token(rol="role_tenant_admin", tenant_id=canario["tenant_id"], usuario_id=1)
    r = client.post(
        "/passenger/tiempos-espera/recalcular",
        json={"terminal_id": str(canario["terminal_id"]), "fecha": "2026-08-08"},
        headers=_auth(tok),
    )
    assert r.status_code == 403


# --------------------------------------------------------------------
# H2 -- escritura de role_airline_coordinator en M1
# --------------------------------------------------------------------


def test_h2_coordinador_autorizado_a_escribir_en_m1(client, canario):
    """Antes 403: el motor le daba INSERT/UPDATE sobre ops.vuelo desde
    S1.4 pero la aplicacion no le daba `vuelos:escribir`. Se comprueba con
    cuerpo vacio: 422 (validacion) demuestra que paso la autorizacion; un
    403 volveria a ser el hallazgo."""
    tok = _token(
        rol="role_airline_coordinator",
        tenant_id=canario["tenant_id"],
        usuario_id=1,
        aerolinea_id=canario["aerolinea_id"],
    )
    r = client.post("/vuelos", json={}, headers=_auth(tok))
    assert r.status_code == 422, f"esperaba 422 (autorizado), vino {r.status_code}"


def test_h2_coordinador_no_gana_m3_de_paso(client, canario):
    """El motor tambien le otorga ops.asignacion_puerta, pero M3 no es su
    modulo -- no se le agregaron scopes `puertas:*`."""
    tok = _token(
        rol="role_airline_coordinator",
        tenant_id=canario["tenant_id"],
        usuario_id=1,
        aerolinea_id=canario["aerolinea_id"],
    )
    r = client.get("/puertas/tablero", headers=_auth(tok))
    assert r.status_code == 403


# --------------------------------------------------------------------
# H3 -- recorte por aerolinea
# --------------------------------------------------------------------


def test_h3_coordinador_solo_ve_vuelos_de_su_aerolinea(client, canario):
    tok = _token(
        rol="role_airline_coordinator",
        tenant_id=canario["tenant_id"],
        usuario_id=1,
        aerolinea_id=canario["aerolinea_id"],
    )
    r = client.get("/vuelos", headers=_auth(tok))
    assert r.status_code == 200
    ajenos = [v for v in r.json() if str(v["aerolinea_id"]) != str(canario["aerolinea_id"])]
    assert ajenos == [], f"se filtraron {len(ajenos)} vuelos de otra aerolinea"


def test_h3_coordinador_de_otra_aerolinea_no_ve_nada(client, canario):
    """Con una aerolinea que no opera en este tenant el listado queda
    vacio -- el recorte excluye de verdad, no solo ordena."""
    tok = _token(
        rol="role_airline_coordinator",
        tenant_id=canario["tenant_id"],
        usuario_id=1,
        aerolinea_id=99999999999999,
    )
    assert client.get("/vuelos", headers=_auth(tok)).json() == []


def test_h3_sin_aerolinea_asignada_es_fail_closed(client, canario):
    """Un coordinador cuyo usuario no tiene `aerolinea_id` NO ve todo: ve
    nada. Es la mitad del hallazgo que mas facil se implementa al reves."""
    tok = _token(rol="role_airline_coordinator", tenant_id=canario["tenant_id"], usuario_id=1)
    assert client.get("/vuelos", headers=_auth(tok)).json() == []


def test_h3_el_informe_respeta_el_mismo_recorte(client, canario):
    """Si el informe no filtrara, el dashboard seria una via alternativa
    para leer los vuelos de la competencia."""
    tok = _token(
        rol="role_airline_coordinator",
        tenant_id=canario["tenant_id"],
        usuario_id=1,
        aerolinea_id=99999999999999,
    )
    r = client.get(
        "/vuelos/informes/simple",
        params={"periodo_inicio": "2020-01-01", "periodo_fin": "2030-01-01"},
        headers=_auth(tok),
    )
    assert r.status_code == 200
    assert r.json()["filas"] == []


def test_h3_roles_no_restringidos_no_pierden_visibilidad(client, canario):
    """El filtro es exclusivo de role_airline_coordinator -- una regresion
    aca significaria haber recortado a quien no correspondia."""
    tok = _token(rol="role_operations_controller", tenant_id=canario["tenant_id"], usuario_id=1)
    r = client.get("/vuelos", headers=_auth(tok))
    assert r.status_code == 200
    assert len(r.json()) > 0


# --------------------------------------------------------------------
# H4 -- "mis tareas" de role_ramp_agent
# --------------------------------------------------------------------


def test_h4_mis_tareas_solo_devuelve_las_del_usuario_de_la_sesion(client, canario):
    if canario["agente_usuario_id"] is None:
        pytest.skip("sin tareas de rampa con agente asignado")
    params = {"periodo_inicio": "2020-01-01", "periodo_fin": "2030-01-01"}

    propio = _token(
        rol="role_ramp_agent",
        tenant_id=canario["tenant_id"],
        usuario_id=canario["agente_usuario_id"],
    )
    r = client.get("/rampa/informes/mis-tareas", params=params, headers=_auth(propio))
    assert r.status_code == 200
    assert len(r.json()["filas"]) > 0

    ajeno = _token(rol="role_ramp_agent", tenant_id=canario["tenant_id"], usuario_id=987654321)
    r2 = client.get("/rampa/informes/mis-tareas", params=params, headers=_auth(ajeno))
    assert r2.status_code == 200
    assert r2.json()["filas"] == [], "un agente no puede ver las tareas de otro"
