"""Integracion (Sprint S1.10, US2, spec.md, quickstart.md Escenario 2):
`GET /auth/yo` devuelve el perfil con los modulos visibles resueltos
como interseccion rol x licencia vigente. Usa el canario MEC
(role_tenant_admin, licencia vigente en M1-M6 desde S1.7).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

_EMAIL_CANARIO_MEC = "canario@mec.aerohub.test"
_PASSWORD_CANARIO = "canario-dev-password"


def _login(client) -> str:
    respuesta = client.post(
        "/auth/login", json={"email": _EMAIL_CANARIO_MEC, "password": _PASSWORD_CANARIO}
    )
    assert respuesta.status_code == 200
    return respuesta.json()["token"]


def test_get_auth_yo_devuelve_perfil_con_modulos_visibles(client):
    token = _login(client)
    respuesta = client.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["rol_codigo"] == "role_tenant_admin"
    codigos = {m["codigo"] for m in cuerpo["modulos_visibles"]}
    # role_tenant_admin puede M1-M6 (todo salvo M7/M8) y MEC tiene licencia
    # vigente en M1-M6 (db/seeds/generate.py, MODULOS_LICENCIABLES).
    assert codigos == {"M1", "M2", "M3", "M4", "M5", "M6"}


def test_retirar_licencia_de_un_modulo_lo_oculta_del_perfil(client, admin_engine):
    token = _login(client)

    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).scalar_one()
        modulo_m5_id = conn.execute(
            text("SELECT id FROM catalogo.modulo WHERE codigo = 'M5'")
        ).scalar_one()

    try:
        with admin_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE tenants.licencia SET activa_hasta = :ahora "
                    "WHERE tenant_id = :t AND modulo_id = :m AND activa_hasta IS NULL"
                ),
                {"ahora": datetime.now(UTC), "t": tenant_id, "m": modulo_m5_id},
            )
        # El UPDATE debe quedar confirmado (fuera del `with`, que hace commit
        # al salir) ANTES de que el gateway lea con su propia conexion --
        # llamar al endpoint todavia dentro de la transaccion no veria el
        # cambio (aislamiento de MonetDB).
        respuesta = client.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
        assert respuesta.status_code == 200
        codigos = {m["codigo"] for m in respuesta.json()["modulos_visibles"]}
        assert "M5" not in codigos
        assert "M1" in codigos
    finally:
        # Restaurar la licencia indefinida -- no dejar el canario compartido
        # sin M5 para el resto de la suite.
        with admin_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE tenants.licencia SET activa_hasta = NULL "
                    "WHERE tenant_id = :t AND modulo_id = :m"
                ),
                {"t": tenant_id, "m": modulo_m5_id},
            )


def test_dos_roles_distintos_devuelven_conjuntos_de_modulos_distintos(client, admin_engine):
    from aerohub_kernel import generar_id, hash_credencial

    with admin_engine.begin() as conn:
        tenant_id = conn.execute(
            text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).scalar_one()
        rol_id = conn.execute(
            text("SELECT id FROM tenants.rol WHERE codigo = 'role_ramp_agent'")
        ).scalar_one()
        usuario_id = generar_id()
        email = f"perfil-test-{usuario_id}@mec.aerohub.test"
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
                "hash": hash_credencial("password-ramp-123"),
                "n": "Usuario Ramp",
            },
        )
        conn.execute(
            text(
                "INSERT INTO tenants.usuario_rol (usuario_id, rol_id, otorgado_por, otorgado_en) "
                "VALUES (:u, :r, :u, NOW())"
            ),
            {"u": usuario_id, "r": rol_id},
        )

    respuesta = client.post("/auth/login", json={"email": email, "password": "password-ramp-123"})
    assert respuesta.status_code == 200
    modulos_ramp = {m["codigo"] for m in respuesta.json()["perfil"]["modulos_visibles"]}

    token_admin = _login(client)
    modulos_admin = {
        m["codigo"]
        for m in client.get("/auth/yo", headers={"Authorization": f"Bearer {token_admin}"}).json()[
            "modulos_visibles"
        ]
    }

    assert modulos_ramp != modulos_admin
    assert modulos_ramp == {"M4"}
