"""Integracion HTTP de la superficie de Soporte D6 (Sprint S1.20, PLAN
v3.0 §8-bis.6, specs/022-soporte-d6/) -- confirma (sin corregir, a
diferencia de S1.16/S1.19) que tickets/KB ya eran alcanzables por los 3
roles esperados, y verifica el hallazgo real de este sprint:
`POST /support/changelog` era inalcanzable por cualquier rol porque
`role_platform_admin` (el unico autorizado por dominio) no tenia ningun
scope `support:*`. Mismo patron que test_compliance_hub.py: `client`/
`admin_engine` vienen de tests/integration/conftest.py.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_SRE = "role_sre"
_ROL_SUPPORT = "role_support"
_ROL_TENANT_ADMIN = "role_tenant_admin"
_ROL_PLATFORM_ADMIN = "role_platform_admin"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, rol: str, tenant_id: int | None, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario_mec = None
        if mec is not None:
            usuario_mec = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
        categoria = conn.execute(
            text("SELECT id FROM support.categoria_ticket WHERE codigo = 'AODB'")
        ).fetchone()
    faltantes = (mec, usuario_mec, categoria)
    if any(f is None for f in faltantes):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "usuario_id": usuario_mec.id,
        "categoria_id": categoria.id,
    }


def _token_support(datos_canario) -> str:
    return _token(
        rol=_ROL_SUPPORT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer", "support:escribir"],
    )


def _token_tenant_admin(datos_canario) -> str:
    return _token(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer", "support:escribir"],
    )


def _token_platform_admin(datos_canario) -> str:
    return _token(
        rol=_ROL_PLATFORM_ADMIN,
        tenant_id=None,
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer", "support:escribir"],
    )


# ---------------------------------------------------------------------------
# Catalogo nuevo de este sprint (T001c) -- necesario para el formulario de
# alta de ticket.
# ---------------------------------------------------------------------------


def test_catalogo_categorias_ticket_no_esta_vacio(client, datos_canario):
    token = _token_support(datos_canario)
    r = client.get("/support/catalogo/categorias-ticket", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert any(c["codigo"] == "AODB" for c in r.json())


# ---------------------------------------------------------------------------
# US1: tickets con SLA y conversacion -- sin hallazgo de scopes, se
# confirma con role_tenant_admin (tenant-scoped) y role_support (global).
# ---------------------------------------------------------------------------


def test_role_tenant_admin_crea_y_ve_su_ticket_en_la_bandeja(client, datos_canario):
    token = _token_tenant_admin(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "alta",
            "asunto": "Vuelo no aparece en la tira",
            "cuerpo_inicial": "El vuelo XX123 no aparece en tiempo real.",
        },
    )
    assert r.status_code == 201, r.text
    ticket_id = r.json()["ticket_id"]
    assert r.json()["sla_objetivo_min"] > 0

    r_listar = client.get("/support/tickets", headers=_auth(token))
    assert r_listar.status_code == 200, r_listar.text
    assert any(t["id"] == ticket_id for t in r_listar.json())


def test_role_support_responde_marca_interno_y_tenant_no_lo_ve(client, datos_canario):
    token_tenant = _token_tenant_admin(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token_tenant),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "media",
            "asunto": "Duda de facturacion",
            "cuerpo_inicial": "No entiendo un cargo en mi factura.",
        },
    )
    ticket_id = r.json()["ticket_id"]

    token_support = _token_support(datos_canario)
    r_interno = client.post(
        f"/support/tickets/{ticket_id}/mensajes",
        headers=_auth(token_support),
        json={"cuerpo": "Nota interna: escalar a billing.", "es_interno": True},
    )
    assert r_interno.status_code == 201, r_interno.text

    # FR-003/hallazgo de contracts/support-api.md: role_tenant_admin NO
    # puede marcar un mensaje como interno (403).
    r_rechazado = client.post(
        f"/support/tickets/{ticket_id}/mensajes",
        headers=_auth(token_tenant),
        json={"cuerpo": "Intento de nota interna desde el tenant.", "es_interno": True},
    )
    assert r_rechazado.status_code == 403, r_rechazado.text

    # El tenant nunca ve la nota interna en su propio hilo.
    r_detalle_tenant = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_tenant))
    assert r_detalle_tenant.status_code == 200, r_detalle_tenant.text
    assert all(not m["es_interno"] for m in r_detalle_tenant.json()["mensajes"])

    # role_support si ve la nota interna (alcance_global).
    r_detalle_support = client.get(f"/support/tickets/{ticket_id}", headers=_auth(token_support))
    assert any(m["es_interno"] for m in r_detalle_support.json()["mensajes"])


def test_transicion_de_estado_invalida_se_rechaza(client, datos_canario):
    token_tenant = _token_tenant_admin(datos_canario)
    r = client.post(
        "/support/tickets",
        headers=_auth(token_tenant),
        json={
            "categoria_id": str(datos_canario["categoria_id"]),
            "severidad": "baja",
            "asunto": "Consulta general",
            "cuerpo_inicial": "Pregunta sobre el producto.",
        },
    )
    ticket_id = r.json()["ticket_id"]

    # Hallazgo: cambiar_estado_ticket() (gestionar_tickets.py linea 342-344)
    # es EXCLUSIVO de role_support -- role_tenant_admin/role_sre no pueden,
    # aunque tengan support:escribir (documentado en research.md).
    token_support = _token_support(datos_canario)
    r_rechazado_por_rol = client.patch(
        f"/support/tickets/{ticket_id}/estado",
        headers=_auth(token_tenant),
        json={"estado": "en_progreso"},
    )
    assert r_rechazado_por_rol.status_code == 403, r_rechazado_por_rol.text

    # abierto -> resuelto directo, invalido (debe pasar por en_progreso).
    r_invalida = client.patch(
        f"/support/tickets/{ticket_id}/estado",
        headers=_auth(token_support),
        json={"estado": "resuelto"},
    )
    assert r_invalida.status_code == 409, r_invalida.text

    r_valida = client.patch(
        f"/support/tickets/{ticket_id}/estado",
        headers=_auth(token_support),
        json={"estado": "en_progreso"},
    )
    assert r_valida.status_code == 200, r_valida.text


# ---------------------------------------------------------------------------
# US2: base de conocimientos compartida entre tenants.
# ---------------------------------------------------------------------------


def test_articulo_kb_publicado_por_role_support_es_visible_para_cualquier_tenant(
    client, datos_canario
):
    token_support = _token_support(datos_canario)
    titulo = f"Como resolver X {datetime.now(UTC).timestamp()}"
    r = client.post(
        "/support/kb/articulos",
        headers=_auth(token_support),
        json={"titulo": titulo, "cuerpo": "Pasos para resolver X.", "etiquetas": ["aodb"]},
    )
    assert r.status_code == 201, r.text

    token_tenant = _token_tenant_admin(datos_canario)
    r_buscar = client.get(
        "/support/kb/articulos", headers=_auth(token_tenant), params={"q": titulo[:10]}
    )
    assert r_buscar.status_code == 200, r_buscar.text
    assert any(a["titulo"] == titulo for a in r_buscar.json())


def test_role_tenant_admin_no_puede_publicar_articulo(client, datos_canario):
    token = _token_tenant_admin(datos_canario)
    r = client.post(
        "/support/kb/articulos",
        headers=_auth(token),
        json={"titulo": "Intento no autorizado", "cuerpo": "cuerpo", "etiquetas": []},
    )
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# US3 + hallazgo del sprint: publicar_changelog() exige role_platform_admin,
# que no tenia ningun scope support:* antes de este sprint.
# ---------------------------------------------------------------------------


def test_role_platform_admin_publica_changelog_y_aparece_en_el_listado(client, datos_canario):
    token = _token_platform_admin(datos_canario)
    version = f"1.20.{int(datetime.now(UTC).timestamp())}"
    r = client.post(
        "/support/changelog",
        headers=_auth(token),
        json={
            "version_producto": version,
            "resumen": "Cierre de Fase 1.5.",
            "items": [
                {
                    "modulo_codigo": "M1",
                    "tipo_cambio": "mejora",
                    "descripcion": "Superficie de soporte D6.",
                }
            ],
        },
    )
    assert r.status_code == 201, r.text

    r_listar = client.get("/support/changelog", headers=_auth(token))
    assert r_listar.status_code == 200, r_listar.text
    assert any(c["version_producto"] == version for c in r_listar.json())


def test_role_support_no_puede_publicar_changelog(client, datos_canario):
    token = _token_support(datos_canario)
    r = client.post(
        "/support/changelog",
        headers=_auth(token),
        json={
            "version_producto": "1.20.0-rechazado",
            "resumen": "No deberia poder.",
            "items": [
                {"modulo_codigo": "M1", "tipo_cambio": "nuevo", "descripcion": "x"}
            ],
        },
    )
    assert r.status_code == 403, r.text
