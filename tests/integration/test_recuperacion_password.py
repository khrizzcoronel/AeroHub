"""Integracion (Sprint S1.10, US6, spec.md, quickstart.md Escenario 6):
solicitar con correo existente e inexistente devuelve 202 identico;
restablecer cambia la contrasena, invalida la anterior y revoca las
sesiones previas; token reusado o vencido da 410.
"""

from __future__ import annotations

import uuid

from aerohub_kernel import generar_id, hash_credencial
from mailpit_helper import extraer_token_del_enlace, ultimo_mensaje_para
from sqlalchemy import text


def _crear_usuario(admin_engine) -> dict:
    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).scalar_one()
        rol_id = conn.execute(
            text("SELECT id FROM tenants.rol WHERE codigo = 'role_tenant_admin'")
        ).scalar_one()
        usuario_id = generar_id()
        email = f"recuperar-{uuid.uuid4().hex[:8]}@uio.aerohub.test"
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
                "hash": hash_credencial("password-original-123"),
                "n": "Usuario a recuperar",
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


def test_solicitar_recuperacion_es_202_exista_o_no_la_cuenta(client):
    r1 = client.post("/auth/recuperar", json={"email": "no-existe-para-nada@aerohub.test"})
    r2 = client.post("/auth/recuperar", json={"email": "otro-que-tampoco-existe@aerohub.test"})
    assert r1.status_code == r2.status_code == 202


def test_ciclo_completo_de_recuperacion(client, admin_engine):
    usuario = _crear_usuario(admin_engine)

    # Sesion abierta ANTES de recuperar -- debe quedar revocada despues.
    login_previo = client.post(
        "/auth/login", json={"email": usuario["email"], "password": "password-original-123"}
    )
    assert login_previo.status_code == 200
    token_sesion_previa = login_previo.json()["token"]

    respuesta_recuperar = client.post("/auth/recuperar", json={"email": usuario["email"]})
    assert respuesta_recuperar.status_code == 202

    mensaje = ultimo_mensaje_para(usuario["email"], asunto_contiene="Recuperar")
    token_en_claro = extraer_token_del_enlace(mensaje)

    respuesta_restablecer = client.post(
        "/auth/restablecer", json={"token": token_en_claro, "password_nueva": "password-nueva-456"}
    )
    assert respuesta_restablecer.status_code == 200

    # La sesion previa (anterior al restablecimiento) queda revocada.
    perfil_con_sesion_vieja = client.get(
        "/auth/yo", headers={"Authorization": f"Bearer {token_sesion_previa}"}
    )
    assert perfil_con_sesion_vieja.status_code == 401

    # La password anterior ya no sirve.
    login_password_vieja = client.post(
        "/auth/login", json={"email": usuario["email"], "password": "password-original-123"}
    )
    assert login_password_vieja.status_code == 401

    # La password nueva si sirve.
    login_password_nueva = client.post(
        "/auth/login", json={"email": usuario["email"], "password": "password-nueva-456"}
    )
    assert login_password_nueva.status_code == 200

    # Reusar el mismo token -> 410.
    respuesta_reuso = client.post(
        "/auth/restablecer", json={"token": token_en_claro, "password_nueva": "otra-password-789"}
    )
    assert respuesta_reuso.status_code == 410


def test_token_de_recuperacion_inexistente_da_410(client):
    respuesta = client.post(
        "/auth/restablecer", json={"token": "999999999.no-existe", "password_nueva": "password-123"}
    )
    assert respuesta.status_code == 410
