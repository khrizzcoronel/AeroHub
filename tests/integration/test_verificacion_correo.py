"""Integracion (Sprint S1.10, US5, spec.md, quickstart.md Escenario 5):
solicitar verificacion -> el correo llega a mailpit -> verificar marca
`email_verificado_en` -> reusar el enlace da 410.
"""

from __future__ import annotations

import uuid

from aerohub_kernel import generar_id, hash_credencial
from mailpit_helper import extraer_token_del_enlace, ultimo_mensaje_para
from sqlalchemy import text


def _crear_usuario_no_verificado(admin_engine) -> dict:
    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).scalar_one()
        rol_id = conn.execute(
            text("SELECT id FROM tenants.rol WHERE codigo = 'role_tenant_admin'")
        ).scalar_one()
        usuario_id = generar_id()
        email = f"verificar-{uuid.uuid4().hex[:8]}@mec.aerohub.test"
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
                "hash": hash_credencial("password-verificar-123"),
                "n": "Usuario a verificar",
            },
        )
        conn.execute(
            text(
                "INSERT INTO tenants.usuario_rol (usuario_id, rol_id, otorgado_por, otorgado_en) "
                "VALUES (:u, :r, :u, NOW())"
            ),
            {"u": usuario_id, "r": rol_id},
        )
    return {"usuario_id": usuario_id, "email": email}


def test_solicitar_y_verificar_correo(client, admin_engine):
    usuario = _crear_usuario_no_verificado(admin_engine)
    login = client.post(
        "/auth/login", json={"email": usuario["email"], "password": "password-verificar-123"}
    )
    assert login.status_code == 200
    assert login.json()["perfil"]["email_verificado"] is False
    token_jwt = login.json()["token"]

    respuesta = client.post(
        "/auth/solicitar-verificacion", headers={"Authorization": f"Bearer {token_jwt}"}
    )
    assert respuesta.status_code == 202

    mensaje = ultimo_mensaje_para(usuario["email"], asunto_contiene="Verifica")
    token_en_claro = extraer_token_del_enlace(mensaje)

    respuesta_verificar = client.post("/auth/verificar-correo", json={"token": token_en_claro})
    assert respuesta_verificar.status_code == 200

    perfil = client.get("/auth/yo", headers={"Authorization": f"Bearer {token_jwt}"})
    assert perfil.json()["email_verificado"] is True

    # Reusar el mismo enlace -> 410.
    respuesta_reuso = client.post("/auth/verificar-correo", json={"token": token_en_claro})
    assert respuesta_reuso.status_code == 410


def test_token_de_verificacion_inexistente_da_410(client):
    respuesta = client.post("/auth/verificar-correo", json={"token": "999999999.no-existe"})
    assert respuesta.status_code == 410
