"""Integracion HTTP real (FastAPI TestClient, sin servidor vivo) de S1.1
(Plan §8.1): middleware JWT del Gateway + endpoints de aerohub_tenancy y
aerohub_aodb. Verifica PN-01 (recurso de otro tenant -> 404, nunca 403) y
PN-02 (tenant_id del cuerpo de la peticion se ignora, siempre gana el del
JWT). Requiere MonetDB con DDL + seed aplicados (mismos datos canario que
el resto de tests/integration/ y tests/cross_tenant/).

`services/gateway/main.py` se carga por ruta de archivo, no por import
normal -- es deliberadamente un script fuera de cualquier paquete `aerohub_*`
(ver el docstring de ese archivo: el contrato de independencia de modulos
de import-linter prohibe que un paquete de negocio importe a otro, y la
composicion de rutas de varios modulos en un solo proceso HTTP tiene que
vivir fuera de esa malla).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

DSN_ADMIN = "monetdb://monetdb:aerohub@localhost:50000/aerohub"

_RUTA_MAIN = Path(__file__).resolve().parents[2] / "services" / "gateway" / "main.py"
_spec = importlib.util.spec_from_file_location("_aerohub_gateway_main_bajo_prueba", _RUTA_MAIN)
assert _spec is not None and _spec.loader is not None
_gateway_main = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _gateway_main
_spec.loader.exec_module(_gateway_main)


def _hay_monetdb() -> bool:
    try:
        engine = create_engine(DSN_ADMIN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _hay_monetdb(), reason="MonetDB no disponible en localhost:50000"
)


@pytest.fixture()
def admin_engine():
    return create_engine(DSN_ADMIN)


@pytest.fixture()
def client():
    return TestClient(_gateway_main.crear_app())


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(
            text("SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).fetchone()
        uio = conn.execute(
            text("SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).fetchone()
        vuelo_mec = conn.execute(
            text("SELECT id FROM ops.vuelo WHERE tenant_id = :t"), {"t": mec.id if mec else None}
        ).fetchone()
        vuelo_uio = conn.execute(
            text("SELECT id FROM ops.vuelo WHERE tenant_id = :t"), {"t": uio.id if uio else None}
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
        plan = conn.execute(
            text("SELECT id FROM tenants.plan WHERE codigo = 'PLAN-CANARIO'")
        ).fetchone()
    faltantes = [
        n
        for n, f in (
            ("tenant MEC", mec),
            ("tenant UIO", uio),
            ("vuelo canario MEC", vuelo_mec),
            ("vuelo canario UIO", vuelo_uio),
            ("aerolinea XX", aerolinea),
            ("aeronave HC-DEV1", aeronave),
            ("tipo_vuelo comercial", tipo_vuelo),
            ("plan PLAN-CANARIO", plan),
        )
        if f is None
    ]
    if faltantes:
        pytest.fail(
            f"Datos canario no encontrados ({', '.join(faltantes)}) -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "mec_tenant_id": mec.id,
        "mec_aeropuerto_id": mec.aeropuerto_id,
        "mec_vuelo_id": vuelo_mec.id,
        "uio_tenant_id": uio.id,
        "uio_aeropuerto_id": uio.aeropuerto_id,
        "uio_vuelo_id": vuelo_uio.id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "tipo_vuelo_id": tipo_vuelo.id,
        "plan_id": plan.id,
    }


def _token_operaciones(tenant_id: int) -> str:
    return codificar_jwt(rol="role_operations_controller", tenant_id=tenant_id)


def _token_platform_admin() -> str:
    return codificar_jwt(rol="role_platform_admin", tenant_id=None)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _cuerpo_vuelo(datos, *, tenant_id_en_cuerpo: int | None = None) -> dict:
    # numero_vuelo unico por llamada -- ops.vuelo tiene un UNIQUE
    # (tenant_id, aerolinea_id, numero_vuelo, fecha_operacion, sentido); un
    # literal fijo colisiona en la segunda ejecucion de la suite completa.
    numero_vuelo = f"HT{generar_id() % 100_000}"
    cuerpo = {
        "aerolinea_id": datos["aerolinea_id"],
        "aeronave_id": datos["aeronave_id"],
        "numero_vuelo": numero_vuelo,
        "tipo_vuelo_id": datos["tipo_vuelo_id"],
        "fecha_operacion": "2026-10-01",
        "sentido": "S",
        "aeropuerto_origen_id": datos["mec_aeropuerto_id"],
        "aeropuerto_destino_id": datos["uio_aeropuerto_id"],
        "sta_utc": datetime(2026, 10, 1, 10, 0, tzinfo=UTC).isoformat(),
        "std_utc": datetime(2026, 10, 1, 9, 0, tzinfo=UTC).isoformat(),
    }
    if tenant_id_en_cuerpo is not None:
        cuerpo["tenant_id"] = tenant_id_en_cuerpo
    return cuerpo


def test_sin_encabezado_authorization_devuelve_401(client):
    r = client.get("/vuelos/1")
    assert r.status_code == 401


def test_token_invalido_devuelve_401(client):
    r = client.get("/vuelos/1", headers=_auth("esto-no-es-un-jwt"))
    assert r.status_code == 401


def test_crear_tenant_como_platform_admin(client, datos_canario):
    codigo = f"HT{generar_id() % 1_000_000}"
    r = client.post(
        "/tenants",
        headers=_auth(_token_platform_admin()),
        json={
            "codigo": codigo,
            "razon_social": f"Tenant HTTP {codigo}",
            "aeropuerto_id": datos_canario["mec_aeropuerto_id"],
            "plan_id": datos_canario["plan_id"],
            "email_admin": f"admin@{codigo.lower()}.aerohub.test",
            "nombre_admin": "Admin HTTP",
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    # tenant_id viaja como string (hallazgo S1.1: numero JSON nativo pierde
    # precision en el navegador por encima de Number.MAX_SAFE_INTEGER).
    assert int(cuerpo["tenant_id"]) > 0
    assert cuerpo["password_temporal"]


def test_crear_vuelo_y_consultarlo_bajo_el_mismo_tenant(client, datos_canario, admin_engine):
    token = _token_operaciones(datos_canario["mec_tenant_id"])
    cuerpo = _cuerpo_vuelo(datos_canario)

    r_crear = client.post("/vuelos", headers=_auth(token), json=cuerpo)
    assert r_crear.status_code == 201, r_crear.text
    vuelo_id = r_crear.json()["vuelo_id"]

    r_get = client.get(f"/vuelos/{vuelo_id}", headers=_auth(token))
    assert r_get.status_code == 200
    assert r_get.json()["numero_vuelo"] == cuerpo["numero_vuelo"]


def test_pn01_vuelo_de_otro_tenant_es_404_no_403(client, datos_canario):
    token_mec = _token_operaciones(datos_canario["mec_tenant_id"])
    token_uio = _token_operaciones(datos_canario["uio_tenant_id"])

    # Control positivo: UIO SI ve su propio vuelo canario.
    r_propio = client.get(f"/vuelos/{datos_canario['uio_vuelo_id']}", headers=_auth(token_uio))
    assert r_propio.status_code == 200, (
        "control positivo fallido -- UIO no encontro su propio vuelo canario"
    )

    # PN-01: MEC pide el vuelo canario de UIO -- debe ser 404, nunca 403.
    r_ajeno = client.get(f"/vuelos/{datos_canario['uio_vuelo_id']}", headers=_auth(token_mec))
    assert r_ajeno.status_code == 404


def test_pn01_cambiar_estado_de_vuelo_ajeno_es_404(client, datos_canario):
    token_mec = _token_operaciones(datos_canario["mec_tenant_id"])
    r = client.post(
        f"/vuelos/{datos_canario['uio_vuelo_id']}/estados",
        headers=_auth(token_mec),
        json={"codigo_estado_nuevo": "embarcando", "origen_cambio": "manual"},
    )
    assert r.status_code == 404


def test_pn02_tenant_id_del_cuerpo_se_ignora(client, datos_canario, admin_engine):
    token_mec = _token_operaciones(datos_canario["mec_tenant_id"])
    cuerpo = _cuerpo_vuelo(datos_canario, tenant_id_en_cuerpo=datos_canario["uio_tenant_id"])

    r = client.post("/vuelos", headers=_auth(token_mec), json=cuerpo)
    assert r.status_code == 201, r.text
    vuelo_id = int(r.json()["vuelo_id"])

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT tenant_id FROM ops.vuelo WHERE id = :id"), {"id": vuelo_id}
        ).fetchone()
    assert fila is not None
    assert fila.tenant_id == datos_canario["mec_tenant_id"], (
        "el vuelo se creo bajo el tenant_id del cuerpo de la peticion, no el "
        "del JWT -- fuga de PN-02"
    )
    assert fila.tenant_id != datos_canario["uio_tenant_id"]
