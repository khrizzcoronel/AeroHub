"""PN-09 (Sprint S1.7, Plan Sec8.7): tenant sin licencia activa invoca la
API de un modulo -> HTTP 403 en el 100% de los casos, evento auditado.

Usa un tenant DESECHABLE creado directo por SQL admin (sin ninguna fila de
`tenants.licencia`) -- los tenants canario (MEC/UIO) YA tienen licencia
para todos los modulos desde S1.7 (db/seeds/generate.py,
MODULOS_LICENCIABLES), necesarios para que el resto de la suite (S1.1-S1.6)
no se rompa con el middleware de licenciamiento nuevo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id, hash_credencial
from sqlalchemy import text

_ROL_BILLING_OFFICER = "role_billing_officer"

_SQL_TENANT = (
    "INSERT INTO tenants.tenant (id, codigo, razon_social, aeropuerto_id, plan_id, estado) "
    "VALUES (:id, :codigo, :razon_social, :aeropuerto, :plan, 'activo')"
)
_SQL_USUARIO = (
    "INSERT INTO tenants.usuario (id, tenant_id, email, hash_credencial, nombre, estado) "
    "VALUES (:id, :t, :email, :hash, :nombre, 'activo')"
)
_SQL_LICENCIA = (
    "INSERT INTO tenants.licencia (id, tenant_id, modulo_id, activa_desde, activa_hasta) "
    "VALUES (:id, :t, :m, :desde, :hasta)"
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _crear_tenant_desechable(conn, *, razon_social: str, nombre_usuario: str) -> dict[str, int]:
    """Tenant nuevo, sin ninguna fila de tenants.licencia -- mismo patron
    de fixture directo-por-SQL que usuario_b_canario en S1.5."""
    tenant_id = generar_id()
    usuario_id = generar_id()
    plan_id = conn.execute(text("SELECT id FROM tenants.plan LIMIT 1")).scalar_one()
    aeropuerto_id = conn.execute(text("SELECT id FROM catalogo.aeropuerto LIMIT 1")).scalar_one()
    conn.execute(
        text(_SQL_TENANT),
        {
            "id": tenant_id,
            "codigo": f"PN9{tenant_id % 100000}",
            "razon_social": razon_social,
            "aeropuerto": aeropuerto_id,
            "plan": plan_id,
        },
    )
    conn.execute(
        text(_SQL_USUARIO),
        {
            "id": usuario_id,
            "t": tenant_id,
            "email": f"pn09-{usuario_id}@aerohub.test",
            "hash": hash_credencial("password-de-prueba"),
            "nombre": nombre_usuario,
        },
    )
    return {"tenant_id": tenant_id, "usuario_id": usuario_id}


@pytest.fixture()
def tenant_desechable(admin_engine):
    with admin_engine.begin() as conn:
        return _crear_tenant_desechable(
            conn, razon_social="Tenant desechable PN-09", nombre_usuario="Usuario PN-09"
        )


def _token_billing(tenant_id: int, usuario_id: int) -> str:
    return codificar_jwt(
        rol=_ROL_BILLING_OFFICER,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=["billing:leer"],
    )


def test_sin_licencia_deniega_con_403_y_audita(client, tenant_desechable, admin_engine):
    token = _token_billing(tenant_desechable["tenant_id"], tenant_desechable["usuario_id"])
    r = client.get("/billing/facturas", headers=_auth(token))
    assert r.status_code == 403, r.text
    assert "sin licencia vigente" in r.json()["detail"]

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT COUNT(*) FROM compliance.log_auditoria "
                "WHERE tenant_id = :t AND tabla = 'licencia' AND operacion = 'DENEGADO'"
            ),
            {"t": tenant_desechable["tenant_id"]},
        ).scalar_one()
    assert fila >= 1, "no se audito el intento denegado por licencia"


def test_licencia_vigente_no_bloquea(client, tenant_desechable, admin_engine):
    tenant_id = tenant_desechable["tenant_id"]
    with admin_engine.begin() as conn:
        modulo_id = conn.execute(
            text("SELECT id FROM catalogo.modulo WHERE codigo = 'M5'")
        ).scalar_one()
        conn.execute(
            text(_SQL_LICENCIA),
            {
                "id": generar_id(),
                "t": tenant_id,
                "m": modulo_id,
                "desde": datetime(2020, 1, 1, tzinfo=UTC),
                "hasta": None,
            },
        )

    token = _token_billing(tenant_id, tenant_desechable["usuario_id"])
    r = client.get("/billing/facturas", headers=_auth(token))
    assert r.status_code == 200, r.text


def test_licencia_vencida_deniega_igual_que_ausente(client, admin_engine):
    """Tenant desechable DISTINTO al de los otros tests -- evita que la
    licencia vigente insertada en test_licencia_vigente_no_bloquea
    contamine este caso."""
    with admin_engine.begin() as conn:
        datos = _crear_tenant_desechable(
            conn, razon_social="Tenant vencido PN-09", nombre_usuario="Usuario PN-09 vencido"
        )
        modulo_id = conn.execute(
            text("SELECT id FROM catalogo.modulo WHERE codigo = 'M5'")
        ).scalar_one()
        hace_un_dia = datetime.now(UTC) - timedelta(days=1)
        conn.execute(
            text(_SQL_LICENCIA),
            {
                "id": generar_id(),
                "t": datos["tenant_id"],
                "m": modulo_id,
                "desde": datetime(2020, 1, 1, tzinfo=UTC),
                "hasta": hace_un_dia,
            },
        )

    token = _token_billing(datos["tenant_id"], datos["usuario_id"])
    r = client.get("/billing/facturas", headers=_auth(token))
    assert r.status_code == 403, r.text
