"""Integracion (Sprint S1.10, US1, spec.md, quickstart.md Escenario 1):
ciclo completo de login contra MonetDB real. Usa el usuario canario
`canario@mec.aerohub.test` (db/seeds/generate.py, password
"canario-dev-password", `role_tenant_admin`, `debe_cambiar_password=False`)
para los casos de solo-lectura; un usuario desechable propio para el caso
de bloqueo, que SI muta estado (no se puede usar el canario compartido:
bloquearlo romperia el resto de la suite que loguea con el).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from aerohub_kernel import generar_id, hash_credencial
from sqlalchemy import text

_EMAIL_CANARIO_MEC = "canario@mec.aerohub.test"
_PASSWORD_CANARIO = "canario-dev-password"

_SQL_USUARIO = (
    "INSERT INTO tenants.usuario (id, tenant_id, email, hash_credencial, nombre, estado, "
    "debe_cambiar_password) VALUES (:id, :t, :email, :hash, :nombre, 'activo', FALSE)"
)
_SQL_USUARIO_ROL = (
    "INSERT INTO tenants.usuario_rol (usuario_id, rol_id, otorgado_por, otorgado_en) "
    "VALUES (:u, :r, :u, NOW())"
)


@pytest.fixture()
def usuario_desechable_con_rol(admin_engine):
    """Usuario nuevo del tenant MEC con `role_tenant_admin` y password
    conocida -- desechable para no afectar al canario compartido con los
    intentos fallidos del test de bloqueo."""
    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).scalar_one()
        rol_id = conn.execute(
            text("SELECT id FROM tenants.rol WHERE codigo = 'role_tenant_admin'")
        ).scalar_one()
        usuario_id = generar_id()
        email = f"login-test-{usuario_id}@mec.aerohub.test"
        conn.execute(
            text(_SQL_USUARIO),
            {
                "id": usuario_id,
                "t": tenant_id,
                "email": email,
                "hash": hash_credencial("password-correcta-123"),
                "nombre": "Usuario desechable de login",
            },
        )
        conn.execute(text(_SQL_USUARIO_ROL), {"u": usuario_id, "r": rol_id})
    return {"usuario_id": usuario_id, "email": email}


def test_login_valido_emite_token_usable_contra_endpoint_autenticado(client):
    respuesta = client.post(
        "/auth/login", json={"email": _EMAIL_CANARIO_MEC, "password": _PASSWORD_CANARIO}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["perfil"]["email"] == _EMAIL_CANARIO_MEC
    assert cuerpo["perfil"]["debe_cambiar_password"] is False

    token = cuerpo["token"]
    perfil = client.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert perfil.status_code == 200
    assert perfil.json()["email"] == _EMAIL_CANARIO_MEC


def test_login_password_incorrecta_devuelve_401(client):
    respuesta = client.post(
        "/auth/login", json={"email": _EMAIL_CANARIO_MEC, "password": "esta-no-es-la-password"}
    )
    assert respuesta.status_code == 401


def test_login_correo_inexistente_devuelve_401(client):
    respuesta = client.post(
        "/auth/login",
        json={"email": "no-existe-en-ningun-tenant@aerohub.test", "password": "cualquier-cosa"},
    )
    assert respuesta.status_code == 401


def test_login_registra_intento_en_tenants_intento_acceso(client, admin_engine):
    marca_antes = datetime.now(UTC) - timedelta(seconds=5)
    client.post("/auth/login", json={"email": _EMAIL_CANARIO_MEC, "password": _PASSWORD_CANARIO})
    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT resultado FROM tenants.intento_acceso "
                "WHERE email_intentado = :email AND ocurrido_en >= :marca "
                "ORDER BY ocurrido_en DESC LIMIT 1"
            ),
            {"email": _EMAIL_CANARIO_MEC, "marca": marca_antes},
        ).fetchone()
    assert fila is not None
    assert fila.resultado == "exitoso"


def test_bloqueo_tras_intentos_fallidos_rechaza_incluso_con_password_correcta(
    client, usuario_desechable_con_rol
):
    email = usuario_desechable_con_rol["email"]
    for _ in range(5):
        resp = client.post("/auth/login", json={"email": email, "password": "password-incorrecta"})
        assert resp.status_code == 401

    # Bloqueado: ni siquiera la contrasena correcta funciona ahora.
    resp = client.post("/auth/login", json={"email": email, "password": "password-correcta-123"})
    assert resp.status_code == 401
