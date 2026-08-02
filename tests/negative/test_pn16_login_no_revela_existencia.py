"""PN-16 (Sprint S1.10, spec.md US1, FR-004): el login no revela si un
correo existe -- la respuesta ante credencial invalida y ante correo
inexistente debe ser byte a byte identica (mismo status, mismo cuerpo).
Es HTTP puro (usa `client`, no `set_role`), por eso vive junto a las
demas suites HTTP-negativas en integration/negative con TestClient --
mismo criterio ya aplicado a PN-09 (S1.7).
"""

from __future__ import annotations

import pytest
from aerohub_kernel import generar_id, hash_credencial
from sqlalchemy import text

_SQL_USUARIO = (
    "INSERT INTO tenants.usuario (id, tenant_id, email, hash_credencial, nombre, estado) "
    "VALUES (:id, :t, :email, :hash, :nombre, 'activo')"
)


@pytest.fixture()
def usuario_con_password_conocida(admin_engine):
    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).scalar_one()
        usuario_id = generar_id()
        email = f"pn16-{usuario_id}@mec.aerohub.test"
        conn.execute(
            text(_SQL_USUARIO),
            {
                "id": usuario_id,
                "t": tenant_id,
                "email": email,
                "hash": hash_credencial("la-password-correcta-123"),
                "nombre": "Usuario PN-16",
            },
        )
    return email


def test_respuesta_identica_entre_correo_inexistente_y_password_incorrecta(
    client, usuario_con_password_conocida
):
    respuesta_inexistente = client.post(
        "/auth/login",
        json={"email": "definitivamente-no-existe@aerohub.test", "password": "lo-que-sea"},
    )
    respuesta_password_incorrecta = client.post(
        "/auth/login",
        json={"email": usuario_con_password_conocida, "password": "password-equivocada"},
    )

    assert respuesta_inexistente.status_code == respuesta_password_incorrecta.status_code == 401
    assert respuesta_inexistente.json() == respuesta_password_incorrecta.json()
