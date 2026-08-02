"""Integracion end-to-end (Sprint S1.10, US4, spec.md, quickstart.md
Escenario 4): invitar -> el correo llega de verdad a mailpit -> aceptar
crea el usuario con el rol correcto -> reusar el token da 410 -> invitar
un correo existente da 409 -> invitar sin ser admin da 403. Contra SMTP
real, no un mock de smtplib (contracts/correo-puerto.md, Principio III).
"""

from __future__ import annotations

import uuid

from aerohub_gateway.infrastructure import codificar_jwt
from mailpit_helper import extraer_token_del_enlace, ultimo_mensaje_para
from sqlalchemy import text


def _token_tenant_admin(tenant_id: int, usuario_id: int) -> str:
    return codificar_jwt(
        rol="role_tenant_admin",
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=["tenants:crear"],
    )


def _token_no_admin(tenant_id: int) -> str:
    return codificar_jwt(
        rol="role_ramp_agent", tenant_id=tenant_id, usuario_id=1, scopes=["rampa:leer"]
    )


def _auth_admin(admin: dict) -> dict[str, str]:
    token = _token_tenant_admin(admin["tenant_id"], admin["usuario_id"])
    return {"Authorization": f"Bearer {token}"}


def _admin_de_mec(admin_engine) -> dict:
    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT u.id AS usuario_id, u.tenant_id FROM tenants.usuario u "
                "JOIN tenants.usuario_rol ur ON ur.usuario_id = u.id "
                "JOIN tenants.rol r ON r.id = ur.rol_id "
                "WHERE u.email = 'canario@mec.aerohub.test' AND r.codigo = 'role_tenant_admin'"
            )
        ).fetchone()
    assert fila is not None
    return {"usuario_id": fila.usuario_id, "tenant_id": fila.tenant_id}


def test_ciclo_completo_invitar_y_aceptar(client, admin_engine):
    admin = _admin_de_mec(admin_engine)
    email_invitado = f"invitado-{uuid.uuid4().hex[:8]}@aerohub.test"

    respuesta = client.post(
        "/usuarios/invitaciones",
        json={"email": email_invitado, "rol_codigo": "role_ramp_agent"},
        headers=_auth_admin(admin),
    )
    assert respuesta.status_code == 201, respuesta.text

    mensaje = ultimo_mensaje_para(email_invitado, asunto_contiene="Invitacion")
    token_en_claro = extraer_token_del_enlace(mensaje)

    respuesta_aceptar = client.post(
        "/usuarios/aceptar-invitacion",
        json={
            "token": token_en_claro,
            "nombre": "Invitado de prueba",
            "password": "password-invitado-123",
        },
    )
    assert respuesta_aceptar.status_code == 201, respuesta_aceptar.text
    assert respuesta_aceptar.json()["tenant_id"] == str(admin["tenant_id"])

    # El usuario nuevo puede loguearse de inmediato con su propia password.
    respuesta_login = client.post(
        "/auth/login", json={"email": email_invitado, "password": "password-invitado-123"}
    )
    assert respuesta_login.status_code == 200
    assert respuesta_login.json()["perfil"]["rol_codigo"] == "role_ramp_agent"

    # Reusar el mismo token de invitacion ya consumido -> 410.
    respuesta_reuso = client.post(
        "/usuarios/aceptar-invitacion",
        json={"token": token_en_claro, "nombre": "Otro nombre", "password": "otra-password-123"},
    )
    assert respuesta_reuso.status_code == 410


def test_invitar_correo_ya_registrado_da_409(client, admin_engine):
    admin = _admin_de_mec(admin_engine)
    respuesta = client.post(
        "/usuarios/invitaciones",
        json={"email": "canario@mec.aerohub.test", "rol_codigo": "role_ramp_agent"},
        headers=_auth_admin(admin),
    )
    assert respuesta.status_code == 409


def test_invitar_sin_ser_admin_da_403(client, admin_engine):
    admin = _admin_de_mec(admin_engine)
    respuesta = client.post(
        "/usuarios/invitaciones",
        json={
            "email": f"otro-{uuid.uuid4().hex[:8]}@aerohub.test",
            "rol_codigo": "role_ramp_agent",
        },
        headers={"Authorization": f"Bearer {_token_no_admin(admin['tenant_id'])}"},
    )
    assert respuesta.status_code == 403
