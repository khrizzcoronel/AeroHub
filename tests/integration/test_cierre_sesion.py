"""Integracion (Sprint S1.10, US7, spec.md, quickstart.md Escenario 7):
`POST /auth/logout` revoca la sesion de inmediato -- el mismo JWT ya no
sirve contra un endpoint autenticado (verificado por T063,
verificar_sesion en el middleware del gateway), sin esperar a su `exp`.
"""

from __future__ import annotations

import pytest
from aerohub_kernel import generar_id, hash_credencial
from sqlalchemy import text


@pytest.fixture()
def usuario_para_logout(admin_engine):
    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).scalar_one()
        usuario_id = generar_id()
        email = f"logout-test-{usuario_id}@uio.aerohub.test"
        conn.execute(
            text(
                "INSERT INTO tenants.usuario (id, tenant_id, email, hash_credencial, "
                "nombre, estado, debe_cambiar_password) "
                "VALUES (:id, :t, :email, :hash, :n, 'activo', FALSE)"
            ),
            {
                "id": usuario_id,
                "t": tenant_id,
                "email": email,
                "hash": hash_credencial("password-logout-123"),
                "n": "Usuario logout",
            },
        )
        rol_id = conn.execute(
            text("SELECT id FROM tenants.rol WHERE codigo = 'role_tenant_admin'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO tenants.usuario_rol (usuario_id, rol_id, otorgado_por, otorgado_en) "
                "VALUES (:u, :r, :u, NOW())"
            ),
            {"u": usuario_id, "r": rol_id},
        )
    return email


def _login(client, email: str) -> str:
    respuesta = client.post("/auth/login", json={"email": email, "password": "password-logout-123"})
    assert respuesta.status_code == 200
    return respuesta.json()["token"]


def test_logout_revoca_sesion_y_el_token_deja_de_servir(client, usuario_para_logout):
    token = _login(client, usuario_para_logout)
    encabezados = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/yo", headers=encabezados).status_code == 200

    respuesta_logout = client.post("/auth/logout", headers=encabezados)
    assert respuesta_logout.status_code == 200

    respuesta_tras_logout = client.get("/auth/yo", headers=encabezados)
    assert respuesta_tras_logout.status_code == 401


def test_logout_es_idempotente(client, usuario_para_logout):
    token = _login(client, usuario_para_logout)
    encabezados = {"Authorization": f"Bearer {token}"}

    assert client.post("/auth/logout", headers=encabezados).status_code == 200
    # Cerrar una sesion ya cerrada no es un error -- el segundo logout usa
    # el mismo token (ya revocado): el middleware lo rechaza con 401 antes
    # de llegar al handler, no hay 500 ni excepcion sin manejar.
    segunda_vez = client.post("/auth/logout", headers=encabezados)
    assert segunda_vez.status_code == 401
