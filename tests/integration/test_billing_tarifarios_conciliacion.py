"""Integracion HTTP de los listados de tarifarios/conciliacion y del
catalogo de conceptos de cargo (Sprint S1.17, PLAN v3.0 §8-bis.3) -- cierra
RF-T10/RF-O15 en el frontend. Mismo patron que
test_billing_facturacion.py: `client`/`admin_engine`/`_requiere_monetdb`
vienen de tests/integration/conftest.py.
"""

from __future__ import annotations

import secrets
import string
from datetime import date, timedelta

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_BILLING_OFFICER = "role_billing_officer"
_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, rol: str, tenant_id: int, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


def _fecha_unica() -> str:
    return (date(2000, 1, 1) + timedelta(days=secrets.randbelow(2_900_000))).isoformat()


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario = None
        if mec is not None:
            usuario = conn.execute(
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
        concepto_aterrizaje = conn.execute(
            text("SELECT id FROM billing.concepto_cargo WHERE codigo = 'tasa_aterrizaje'")
        ).fetchone()
    faltantes = (
        mec,
        usuario,
        aerolinea,
        aeronave,
        tipo_vuelo,
        aeropuerto_mec,
        aeropuerto_uio,
        concepto_aterrizaje,
    )
    if any(f is None for f in faltantes):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "usuario_id": usuario.id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "tipo_vuelo_id": tipo_vuelo.id,
        "aeropuerto_mec_id": aeropuerto_mec.aeropuerto_id,
        "aeropuerto_uio_id": aeropuerto_uio.aeropuerto_id,
        "concepto_aterrizaje_id": concepto_aterrizaje.id,
    }


def _token_billing(datos_canario) -> str:
    return _token(
        rol=_ROL_BILLING_OFFICER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["billing:leer", "billing:escribir"],
    )


def _crear_vuelo(client, datos_canario, *, numero_vuelo: str, fecha_operacion: str):
    token_vuelos = _token(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:escribir"],
    )
    r = client.post(
        "/vuelos",
        headers=_auth(token_vuelos),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "aeronave_id": str(datos_canario["aeronave_id"]),
            "numero_vuelo": numero_vuelo,
            "tipo_vuelo_id": str(datos_canario["tipo_vuelo_id"]),
            "fecha_operacion": fecha_operacion,
            "sentido": "S",
            "aeropuerto_origen_id": str(datos_canario["aeropuerto_mec_id"]),
            "aeropuerto_destino_id": str(datos_canario["aeropuerto_uio_id"]),
            "sta_utc": f"{fecha_operacion}T10:00:00Z",
            "std_utc": f"{fecha_operacion}T09:00:00Z",
            "pax_estimado": 10,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["vuelo_id"]


# ---------------------------------------------------------------------------
# US1/US2: catalogo de conceptos + listado de tarifarios con historial
# ---------------------------------------------------------------------------


def test_catalogo_conceptos_cargo_no_esta_vacio(client, datos_canario):
    token_billing = _token_billing(datos_canario)
    r = client.get("/billing/catalogo/conceptos-cargo", headers=_auth(token_billing))
    assert r.status_code == 200, r.text
    conceptos = r.json()
    assert any(c["codigo"] == "tasa_aterrizaje" for c in conceptos)


def test_listar_tarifarios_incluye_historial_no_solo_vigente(client, datos_canario):
    token_billing = _token_billing(datos_canario)
    # Moneda ISO 4217 de 3 LETRAS (domain/tarifario.py exige .isalpha()),
    # pero unica por corrida -- evita colision con el tarifario 'vigente'
    # de USD que crean otras suites (test_billing_facturacion.py::tarifario_activo).
    letras = "".join(secrets.choice(string.ascii_uppercase) for _ in range(2))
    moneda = f"Z{letras}"
    nombre_1 = f"T1-{secrets.randbelow(1_000_000)}"
    nombre_2 = f"T2-{secrets.randbelow(1_000_000)}"

    # `activar_tarifario` rechaza un segundo 'vigente' en la misma moneda
    # sin desactivar el primero (no existe endpoint de desactivacion) --
    # el "historial" que este listado debe exponer es, en la practica de
    # hoy, borrador + vigente coexistiendo, no vigente + expirado.
    r1 = client.post(
        "/billing/tarifarios",
        headers=_auth(token_billing),
        json={"nombre": nombre_1, "moneda": moneda, "vigente_desde": "2020-01-01"},
    )
    assert r1.status_code == 201, r1.text
    tarifario_1 = r1.json()["tarifario_id"]
    client.post(
        f"/billing/tarifarios/{tarifario_1}/conceptos",
        headers=_auth(token_billing),
        json={
            "concepto_cargo_id": str(datos_canario["concepto_aterrizaje_id"]),
            "tarifa_unitaria": "10.0000",
        },
    )

    r2 = client.post(
        "/billing/tarifarios",
        headers=_auth(token_billing),
        json={"nombre": nombre_2, "moneda": moneda, "vigente_desde": "2026-01-01"},
    )
    tarifario_2 = r2.json()["tarifario_id"]
    r_activar_2 = client.post(
        f"/billing/tarifarios/{tarifario_2}/activar", headers=_auth(token_billing)
    )
    assert r_activar_2.status_code == 204, r_activar_2.text

    r_listar = client.get("/billing/tarifarios", headers=_auth(token_billing))
    assert r_listar.status_code == 200, r_listar.text
    tarifarios = {t["id"]: t for t in r_listar.json()}

    # Los 2 aparecen -- listar_tarifarios() no filtra por estado (a
    # diferencia de listar_tarifarios_vigentes), historial observable
    # (spec.md US2).
    assert tarifario_1 in tarifarios
    assert tarifario_2 in tarifarios
    assert tarifarios[tarifario_2]["estado"] == "vigente"
    assert tarifarios[tarifario_1]["estado"] == "borrador"
    assert len(tarifarios[tarifario_1]["conceptos"]) == 1
    assert tarifarios[tarifario_1]["conceptos"][0]["tarifa_unitaria"] == "10.0000"


# ---------------------------------------------------------------------------
# US3: listado de conciliaciones con diferencia derivada
# ---------------------------------------------------------------------------


def test_listar_conciliaciones_muestra_diferencia_derivada(client, datos_canario):
    token_billing = _token_billing(datos_canario)
    fecha = _fecha_unica()
    numero = f"BL{secrets.randbelow(100_000_000)}"
    vuelo_id = _crear_vuelo(client, datos_canario, numero_vuelo=numero, fecha_operacion=fecha)
    periodo = fecha[:7]

    r = client.post(
        "/billing/conciliaciones",
        headers=_auth(token_billing),
        json={
            "vuelo_id": vuelo_id,
            "periodo": periodo,
            "pax_reportado_aerolinea": 130,
            "pax_registrado_sistema": 125,
            "fuente_reporte": "manifiesto_aerolinea",
        },
    )
    assert r.status_code == 201, r.text
    conciliacion_id = r.json()["conciliacion_id"]

    r_listar = client.get("/billing/conciliaciones", headers=_auth(token_billing))
    assert r_listar.status_code == 200, r_listar.text
    encontrada = next((c for c in r_listar.json() if c["id"] == conciliacion_id), None)
    assert encontrada is not None
    assert encontrada["diferencia"] == 5
    assert encontrada["conciliado_en"] is None
