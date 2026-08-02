"""Integracion (Sprint S1.10, US3, spec.md, quickstart.md Escenario 3):
mientras `debe_cambiar_password=true`, cualquier ruta autenticada
distinta de `/auth/cambiar-password` responde 403. Usa un tenant nuevo
recien aprovisionado -- `insertar_usuario_admin` deja
`debe_cambiar_password=TRUE` por defecto (16_identidad.sql).
"""

from __future__ import annotations

import uuid

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text


def _token_platform_admin() -> str:
    return codificar_jwt(rol="role_platform_admin", tenant_id=None, scopes=["tenants:crear"])


@pytest.fixture()
def tenant_nuevo_con_password_temporal(client, admin_engine):
    with admin_engine.connect() as conn:
        aeropuerto_id = conn.execute(
            text("SELECT id FROM catalogo.aeropuerto LIMIT 1")
        ).scalar_one()
        plan_id = conn.execute(text("SELECT id FROM tenants.plan LIMIT 1")).scalar_one()

    codigo = f"P3{uuid.uuid4().hex[:6].upper()}"
    email = f"{codigo.lower()}@aerohub.test"
    respuesta = client.post(
        "/tenants",
        json={
            "codigo": codigo,
            "razon_social": f"Tenant {codigo}",
            "aeropuerto_id": str(aeropuerto_id),
            "plan_id": str(plan_id),
            "email_admin": email,
            "nombre_admin": "Admin temporal",
        },
        headers={"Authorization": f"Bearer {_token_platform_admin()}"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return {"email": email, "password_temporal": respuesta.json()["password_temporal"]}


def _login(client, email: str, password: str) -> str:
    respuesta = client.post("/auth/login", json={"email": email, "password": password})
    assert respuesta.status_code == 200
    assert respuesta.json()["perfil"]["debe_cambiar_password"] is True
    return respuesta.json()["token"]


def test_endpoint_de_negocio_bloqueado_mientras_debe_cambiar_password(
    client, tenant_nuevo_con_password_temporal
):
    datos = tenant_nuevo_con_password_temporal
    token = _login(client, datos["email"], datos["password_temporal"])
    encabezados = {"Authorization": f"Bearer {token}"}

    respuesta = client.get("/auth/yo", headers=encabezados)
    assert respuesta.status_code == 403


def test_password_debil_rechazada_con_422_y_requisito_faltante(
    client, tenant_nuevo_con_password_temporal
):
    datos = tenant_nuevo_con_password_temporal
    token = _login(client, datos["email"], datos["password_temporal"])
    encabezados = {"Authorization": f"Bearer {token}"}

    respuesta = client.post(
        "/auth/cambiar-password",
        json={"password_actual": datos["password_temporal"], "password_nueva": "corta"},
        headers=encabezados,
    )
    assert respuesta.status_code == 422
    assert "al menos" in respuesta.json()["detail"]


def test_tras_cambiar_password_todo_queda_disponible(client, tenant_nuevo_con_password_temporal):
    datos = tenant_nuevo_con_password_temporal
    token = _login(client, datos["email"], datos["password_temporal"])
    encabezados = {"Authorization": f"Bearer {token}"}

    respuesta = client.post(
        "/auth/cambiar-password",
        json={
            "password_actual": datos["password_temporal"],
            "password_nueva": "nueva-password-123",
        },
        headers=encabezados,
    )
    assert respuesta.status_code == 200

    # El mismo token (misma sesion) ya no esta bloqueado por password
    # temporal -- solo se revocan las OTRAS sesiones, no la actual.
    respuesta_yo = client.get("/auth/yo", headers=encabezados)
    assert respuesta_yo.status_code == 200
    assert respuesta_yo.json()["debe_cambiar_password"] is False

    # Login con la password anterior ya no funciona.
    respuesta_login_vieja = client.post(
        "/auth/login", json={"email": datos["email"], "password": datos["password_temporal"]}
    )
    assert respuesta_login_vieja.status_code == 401

    # Login con la password nueva funciona.
    respuesta_login_nueva = client.post(
        "/auth/login", json={"email": datos["email"], "password": "nueva-password-123"}
    )
    assert respuesta_login_nueva.status_code == 200
