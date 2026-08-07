"""Compuertas de Fase 1 de docs/diseno/PLAN_CORRECCION_MODULOS.md
(2026-08-06): ninguna escritura autorizada por scope de aplicacion pero
sin GRANT de motor debe llegar como 500 -- SIEMPRE 403 legible
(PN-07/`_manejador_acceso_denegado_motor`). Y el ajuste de D1(a)
(quitar vuelos:escribir/puertas:escribir/rampa:escribir/billing:escribir
de role_tenant_admin) no debe romper el camino de escritura de los
roles operativos reales.
"""

from __future__ import annotations

import secrets
from datetime import date

import pytest
from aerohub_contracts import scopes_del_rol
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_TENANT_ADMIN = "role_tenant_admin"
_ROL_SUPPORT = "role_support"
_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"
_ROL_BILLING_OFFICER = "role_billing_officer"


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
    faltantes = (mec, usuario, aerolinea, aeronave, tipo_vuelo, aeropuerto_mec, aeropuerto_uio)
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
    }


def _cuerpo_vuelo(datos_canario, *, numero_vuelo: str) -> dict:
    fecha = date.today().isoformat()
    return {
        "aerolinea_id": str(datos_canario["aerolinea_id"]),
        "aeronave_id": str(datos_canario["aeronave_id"]),
        "numero_vuelo": numero_vuelo,
        "tipo_vuelo_id": str(datos_canario["tipo_vuelo_id"]),
        "fecha_operacion": fecha,
        "sentido": "S",
        "aeropuerto_origen_id": str(datos_canario["aeropuerto_mec_id"]),
        "aeropuerto_destino_id": str(datos_canario["aeropuerto_uio_id"]),
        "sta_utc": f"{fecha}T10:00:00Z",
        "std_utc": f"{fecha}T09:00:00Z",
        "pax_estimado": 10,
    }


# ---------------------------------------------------------------------------
# El handler traduce TANTO "access denied" (SELECT) COMO "insufficient
# privileges" (INSERT/UPDATE/DELETE) a 403 -- antes de este hallazgo, solo
# reconocia la primera frase y una escritura sin GRANT llegaba como 500.
# ---------------------------------------------------------------------------


def test_escritura_sin_grant_de_motor_responde_403_no_500(client, datos_canario):
    # role_support no tiene NINGUN grant sobre billing (98_grants_billing.sql,
    # celda '-' de la matriz 4.3.1) -- billing:escribir aqui es un scope de
    # aplicacion fabricado a mano (codificar_jwt no deriva de roles_modulos.py),
    # exactamente el escenario "scope de app sin GRANT de motor" que
    # _manejador_acceso_denegado_motor debe traducir.
    token = _token(
        rol=_ROL_SUPPORT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["billing:escribir"],
    )
    r = client.post(
        "/billing/tarifarios",
        headers=_auth(token),
        json={"nombre": "Plan negativo", "moneda": "USD", "vigente_desde": "2026-01-01"},
    )
    assert r.status_code == 403, r.text
    assert r.json() == {"detail": "acceso denegado"}


# ---------------------------------------------------------------------------
# D1(a): role_tenant_admin ya NO tiene scopes de escritura de M1/M3/M4/M5 --
# se rechaza en la capa de aplicacion (403 "scope insuficiente"), ni siquiera
# llega al motor.
# ---------------------------------------------------------------------------


def test_role_tenant_admin_no_tiene_scopes_de_escritura_operativos(datos_canario):
    scopes = scopes_del_rol(_ROL_TENANT_ADMIN)
    for scope in ("vuelos:escribir", "puertas:escribir", "rampa:escribir", "billing:escribir"):
        assert scope not in scopes, f"role_tenant_admin no deberia tener {scope!r} (D1(a))"
    # Confirma que no se le fue de paso el scope de lectura correspondiente.
    for scope in ("vuelos:leer", "puertas:leer", "rampa:leer", "billing:leer"):
        assert scope in scopes


def test_role_tenant_admin_no_puede_crear_vuelo(client, datos_canario):
    token = _token(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=list(scopes_del_rol(_ROL_TENANT_ADMIN)),
    )
    numero = f"NEG{secrets.randbelow(1_000_000)}"
    cuerpo = _cuerpo_vuelo(datos_canario, numero_vuelo=numero)
    r = client.post("/vuelos", headers=_auth(token), json=cuerpo)
    assert r.status_code == 403, r.text


def test_role_tenant_admin_no_puede_crear_tarifario(client, datos_canario):
    token = _token(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=list(scopes_del_rol(_ROL_TENANT_ADMIN)),
    )
    r = client.post(
        "/billing/tarifarios",
        headers=_auth(token),
        json={"nombre": "Plan denegado", "moneda": "USD", "vigente_desde": "2026-01-01"},
    )
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# Regresion: los roles que la matriz SI autoriza siguen pudiendo escribir --
# D1(a) no les quito nada.
# ---------------------------------------------------------------------------


def test_role_operations_controller_si_puede_crear_vuelo(client, datos_canario):
    token = _token(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=list(scopes_del_rol(_ROL_OPERATIONS_CONTROLLER)),
    )
    numero = f"NEG{secrets.randbelow(1_000_000)}"
    cuerpo = _cuerpo_vuelo(datos_canario, numero_vuelo=numero)
    r = client.post("/vuelos", headers=_auth(token), json=cuerpo)
    assert r.status_code == 201, r.text


def test_role_billing_officer_si_puede_crear_tarifario(client, datos_canario):
    token = _token(
        rol=_ROL_BILLING_OFFICER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=list(scopes_del_rol(_ROL_BILLING_OFFICER)),
    )
    r = client.post(
        "/billing/tarifarios",
        headers=_auth(token),
        json={"nombre": "Plan valido", "moneda": "USD", "vigente_desde": "2026-01-01"},
    )
    assert r.status_code == 201, r.text
