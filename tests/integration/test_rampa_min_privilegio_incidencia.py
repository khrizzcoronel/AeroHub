"""Compuerta de pruebas de S1.5 (Plan §8.5): minimo privilegio de
role_ramp_agent (no lee ni escribe turnarounds/tareas ajenas) y generacion
de incidencia dentro de la ventana (RF-O16: "< 60s tras superar el
estandar").

Todas las pruebas usan el `client` (TestClient in-process) de conftest.py
-- a diferencia de RNF-P02/PN-05 concurrente, aqui no hay WebSocket
involucrado, asi que no aplica el motivo de deadlock documentado en esos
otros archivos.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id, hash_credencial
from sqlalchemy import text

_ROL_RAMP_AGENT = "role_ramp_agent"
_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario_a = None
        if mec is not None:
            usuario_a = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
        aerolinea = conn.execute(
            text("SELECT id FROM catalogo.aerolinea WHERE codigo_iata = 'XX'")
        ).fetchone()
        aeronave = conn.execute(
            text("SELECT id FROM catalogo.aeronave WHERE matricula = 'HC-DEV1'")
        ).fetchone()
        tipo_vuelo = conn.execute(
            text("SELECT id FROM catalogo.tipo_vuelo WHERE codigo = 'comercial'")
        ).fetchone()
        aeropuerto_mec = conn.execute(
            text("SELECT aeropuerto_id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).fetchone()
        aeropuerto_uio = conn.execute(
            text("SELECT aeropuerto_id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).fetchone()
        tipo_combustible = conn.execute(
            text(
                "SELECT id, duracion_estandar_min, es_ruta_critica FROM rampa.tipo_tarea "
                "WHERE codigo = 'combustible'"
            )
        ).fetchone()
    faltantes = (
        mec,
        usuario_a,
        aerolinea,
        aeronave,
        tipo_vuelo,
        aeropuerto_mec,
        aeropuerto_uio,
        tipo_combustible,
    )
    if any(f is None for f in faltantes):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "usuario_a_id": usuario_a.id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "tipo_vuelo_id": tipo_vuelo.id,
        "aeropuerto_mec_id": aeropuerto_mec.aeropuerto_id,
        "aeropuerto_uio_id": aeropuerto_uio.aeropuerto_id,
        "tipo_combustible_id": tipo_combustible.id,
        "duracion_estandar_combustible_min": tipo_combustible.duracion_estandar_min,
    }


@pytest.fixture()
def usuario_b_canario(admin_engine, datos_canario):
    """Un segundo agente de rampa del MISMO tenant -- no hay endpoint de
    alta de usuario adicional en un tenant existente todavia (fuera de
    alcance de S1.5), se inserta directo por SQL admin, igual que
    test_pn06_pn07_rnf_p01.py inserta API Keys que el endpoint tampoco
    permite crear."""
    tenant_id = datos_canario["tenant_id"]
    usuario_id = generar_id()
    email = f"ramp-b-{usuario_id}@mec.aerohub.test"
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenants.usuario "
                "(id, tenant_id, email, hash_credencial, nombre, estado) "
                "VALUES (:id, :t, :email, :hash, 'Agente B (prueba)', 'activo')"
            ),
            {
                "id": usuario_id,
                "t": tenant_id,
                "email": email,
                "hash": hash_credencial("password-de-prueba"),
            },
        )
    return usuario_id


def _token(*, rol: str, tenant_id: int, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


def _crear_vuelo(client, token: str, datos_canario, *, sentido: str) -> str:
    if sentido == "L":
        origen, destino = datos_canario["aeropuerto_uio_id"], datos_canario["aeropuerto_mec_id"]
    else:
        origen, destino = datos_canario["aeropuerto_mec_id"], datos_canario["aeropuerto_uio_id"]
    r = client.post(
        "/vuelos",
        headers=_auth(token),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "aeronave_id": str(datos_canario["aeronave_id"]),
            "numero_vuelo": f"RA{generar_id() % 100_000_000}",
            "tipo_vuelo_id": str(datos_canario["tipo_vuelo_id"]),
            "fecha_operacion": "2026-11-01",
            "sentido": sentido,
            "aeropuerto_origen_id": str(origen),
            "aeropuerto_destino_id": str(destino),
            "sta_utc": "2026-11-01T10:00:00Z",
            "std_utc": "2026-11-01T09:00:00Z",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["vuelo_id"]


def _crear_turnaround(client, token_rampa: str, datos_canario) -> str:
    # ops.vuelo solo admite INSERT de role_operations_controller (y otros
    # roles "duenos" de ops, ver 96_grants_ops.sql) -- role_ramp_agent solo
    # tiene SELECT ahi. El JWT del agente de rampa lleva el scope
    # "vuelos:escribir" igual (para que requiere_scope() no lo bloquee),
    # pero el motor rechazaria el INSERT por rol; se usa un token de
    # operations_controller SOLO para poner en pie los vuelos de prueba.
    token_vuelos = _token(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_a_id"],
        scopes=["vuelos:escribir"],
    )
    vuelo_llegada = _crear_vuelo(client, token_vuelos, datos_canario, sentido="L")
    vuelo_salida = _crear_vuelo(client, token_vuelos, datos_canario, sentido="S")
    r = client.post(
        "/rampa/turnarounds",
        headers=_auth(token_rampa),
        json={
            "vuelo_llegada_id": vuelo_llegada,
            "vuelo_salida_id": vuelo_salida,
            "inicio_previsto": "2026-11-01T09:00:00Z",
            "fin_previsto": "2026-11-01T11:00:00Z",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["turnaround_id"]


def _token_agente_a(datos_canario) -> str:
    return _token(
        rol=_ROL_RAMP_AGENT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_a_id"],
        scopes=["rampa:leer", "rampa:escribir"],
    )


# ---------------------------------------------------------------------------
# Minimo privilegio de role_ramp_agent (Plan §8.5)
# ---------------------------------------------------------------------------


def test_ramp_agent_no_ve_tareas_de_otro_agente(client, datos_canario, usuario_b_canario):
    token_a = _token_agente_a(datos_canario)
    turnaround_id = _crear_turnaround(client, token_a, datos_canario)

    r = client.post(
        f"/rampa/turnarounds/{turnaround_id}/tareas",
        headers=_auth(token_a),
        json={"tipo_tarea_id": str(datos_canario["tipo_combustible_id"])},
    )
    assert r.status_code == 201, r.text

    token_b = _token(
        rol=_ROL_RAMP_AGENT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=usuario_b_canario,
        scopes=["rampa:leer", "rampa:escribir"],
    )
    r = client.get(f"/rampa/turnarounds/{turnaround_id}/tareas", headers=_auth(token_b))
    assert r.status_code == 200
    assert r.json() == []


def test_ramp_agent_no_puede_finalizar_tarea_de_otro_agente(
    client, datos_canario, usuario_b_canario
):
    token_a = _token_agente_a(datos_canario)
    turnaround_id = _crear_turnaround(client, token_a, datos_canario)
    r = client.post(
        f"/rampa/turnarounds/{turnaround_id}/tareas",
        headers=_auth(token_a),
        json={"tipo_tarea_id": str(datos_canario["tipo_combustible_id"])},
    )
    tarea_id = r.json()["tarea_id"]

    token_b = _token(
        rol=_ROL_RAMP_AGENT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=usuario_b_canario,
        scopes=["rampa:leer", "rampa:escribir"],
    )
    r = client.post(
        f"/rampa/tareas/{tarea_id}/finalizar",
        headers=_auth(token_b),
        json={"fin_real": "2026-11-01T09:15:00Z"},
    )
    # PN-01 mismo principio: 404, nunca 403 -- no confirma que la tarea de
    # otro agente existe.
    assert r.status_code == 404, r.text


def test_ramp_agent_si_ve_y_finaliza_su_propia_tarea(client, datos_canario):
    token_a = _token_agente_a(datos_canario)
    turnaround_id = _crear_turnaround(client, token_a, datos_canario)
    r = client.post(
        f"/rampa/turnarounds/{turnaround_id}/tareas",
        headers=_auth(token_a),
        json={"tipo_tarea_id": str(datos_canario["tipo_combustible_id"])},
    )
    tarea_id = r.json()["tarea_id"]

    r = client.get(f"/rampa/turnarounds/{turnaround_id}/tareas", headers=_auth(token_a))
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.post(
        f"/rampa/tareas/{tarea_id}/finalizar",
        headers=_auth(token_a),
        json={"fin_real": "2026-11-01T09:15:00Z"},
    )
    assert r.status_code == 200, r.text


def test_role_operations_controller_ve_todas_las_tareas(client, datos_canario):
    """Control positivo: un rol sin restriccion de minimo privilegio SI ve
    la tarea del agente -- si esta prueba fallara, las anteriores
    pasarian por una razon equivocada (p. ej. un bug que oculte TODA
    tarea, no solo las ajenas)."""
    token_a = _token_agente_a(datos_canario)
    turnaround_id = _crear_turnaround(client, token_a, datos_canario)
    client.post(
        f"/rampa/turnarounds/{turnaround_id}/tareas",
        headers=_auth(token_a),
        json={"tipo_tarea_id": str(datos_canario["tipo_combustible_id"])},
    )

    token_controller = _token(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_a_id"],
        scopes=["rampa:leer"],
    )
    r = client.get(f"/rampa/turnarounds/{turnaround_id}/tareas", headers=_auth(token_controller))
    assert r.status_code == 200
    assert len(r.json()) == 1


# ---------------------------------------------------------------------------
# RF-O16: incidencia generada < 60s tras superar el estandar
# ---------------------------------------------------------------------------


def test_incidencia_generada_dentro_de_60s_al_superar_estandar(client, datos_canario):
    token_a = _token_agente_a(datos_canario)
    turnaround_id = _crear_turnaround(client, token_a, datos_canario)
    r = client.post(
        f"/rampa/turnarounds/{turnaround_id}/tareas",
        headers=_auth(token_a),
        json={"tipo_tarea_id": str(datos_canario["tipo_combustible_id"])},
    )
    tarea_id = r.json()["tarea_id"]

    # fin_real bien por encima del estandar (30 min) -- la deteccion es
    # SINCRONICA (aerohub_ramp.application.finalizar_tarea), no un ciclo
    # de fondo: se mide el tiempo de la propia peticion HTTP.
    fin_real = (datetime.now(UTC) + timedelta(minutes=45)).isoformat()

    t0 = time.monotonic()
    r = client.post(
        f"/rampa/tareas/{tarea_id}/finalizar", headers=_auth(token_a), json={"fin_real": fin_real}
    )
    dt = time.monotonic() - t0

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["incidencia_generada"] is True
    assert dt < 60.0, f"finalizar_tarea tardo {dt:.3f}s -- RF-O16 exige < 60s"

    r_incidencias = client.get("/rampa/incidencias", headers=_auth(token_a))
    assert r_incidencias.status_code == 200
    incidencias = [i for i in r_incidencias.json() if i["tarea_turnaround_id"] == tarea_id]
    assert len(incidencias) == 1
    assert incidencias[0]["severidad"] == "alta"  # combustible es ruta critica


def test_incidencia_no_generada_si_no_supera_el_estandar(client, datos_canario):
    token_a = _token_agente_a(datos_canario)
    turnaround_id = _crear_turnaround(client, token_a, datos_canario)
    r = client.post(
        f"/rampa/turnarounds/{turnaround_id}/tareas",
        headers=_auth(token_a),
        json={"tipo_tarea_id": str(datos_canario["tipo_combustible_id"])},
    )
    tarea_id = r.json()["tarea_id"]

    # 5 minutos, muy por debajo del estandar de 30 min.
    fin_real = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    r = client.post(
        f"/rampa/tareas/{tarea_id}/finalizar", headers=_auth(token_a), json={"fin_real": fin_real}
    )
    assert r.status_code == 200, r.text
    assert r.json()["incidencia_generada"] is False
