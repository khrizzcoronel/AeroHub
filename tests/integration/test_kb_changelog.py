"""Compuertas de pruebas de S1.8 (Plan Sec8.8, US4/US5): publicar/versionar/
buscar articulos de KB por texto y etiqueta; changelog visible a cualquier
tenant sin depender de licencia de modulo -- Escenario 4 de quickstart.md.
"""

from __future__ import annotations

import secrets

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_SUPPORT = "role_support"
_ROL_PLATFORM_ADMIN = "role_platform_admin"
_ROL_TENANT_ADMIN = "role_tenant_admin"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _titulo_unico(base: str) -> str:
    return f"{base} {secrets.token_hex(4)}"


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario = None
        if mec is not None:
            usuario = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
    if mec is None or usuario is None:
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {"tenant_id": mec.id, "usuario_id": usuario.id}


def _token_support(datos_canario) -> str:
    return codificar_jwt(
        rol=_ROL_SUPPORT,
        tenant_id=None,
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer", "support:escribir"],
    )


def _token_tenant(datos_canario, *, scopes: list[str]) -> str:
    return codificar_jwt(
        rol=_ROL_TENANT_ADMIN,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=scopes,
    )


def test_publicar_versionar_y_buscar_articulo_por_etiqueta(client, datos_canario):
    token_support = _token_support(datos_canario)
    titulo = _titulo_unico("Como resolver un incidente de AODB")
    etiqueta = f"aodb-{secrets.token_hex(3)}"

    r = client.post(
        "/support/kb/articulos",
        headers=_auth(token_support),
        json={"titulo": titulo, "cuerpo": "Contenido version 1.", "etiquetas": [etiqueta]},
    )
    assert r.status_code == 201, r.text
    assert r.json()["version"] == 1

    token_tenant = _token_tenant(datos_canario, scopes=["support:leer"])

    r = client.get(
        "/support/kb/articulos", params={"etiqueta": etiqueta}, headers=_auth(token_tenant)
    )
    assert r.status_code == 200, r.text
    assert titulo in [a["titulo"] for a in r.json()]

    r = client.get(
        "/support/kb/articulos", params={"q": "incidente de AODB"}, headers=_auth(token_tenant)
    )
    assert titulo in [a["titulo"] for a in r.json()]

    # FR-013: nueva version del mismo titulo, ambas identificables por separado.
    r = client.post(
        "/support/kb/articulos",
        headers=_auth(token_support),
        json={"titulo": titulo, "cuerpo": "Contenido version 2.", "etiquetas": [etiqueta]},
    )
    assert r.status_code == 201, r.text
    assert r.json()["version"] == 2

    r = client.get(
        "/support/kb/articulos", params={"etiqueta": etiqueta}, headers=_auth(token_tenant)
    )
    versiones = sorted(a["version"] for a in r.json() if a["titulo"] == titulo)
    assert versiones == [1, 2]


def test_role_tenant_no_puede_publicar_kb(client, datos_canario):
    token_tenant = _token_tenant(datos_canario, scopes=["support:leer", "support:escribir"])
    r = client.post(
        "/support/kb/articulos",
        headers=_auth(token_tenant),
        json={"titulo": _titulo_unico("Articulo no autorizado"), "cuerpo": "x", "etiquetas": []},
    )
    assert r.status_code == 403, r.text


def test_changelog_visible_a_tenant_sin_depender_de_licencia(client, datos_canario):
    token_admin = codificar_jwt(
        rol=_ROL_PLATFORM_ADMIN,
        tenant_id=None,
        usuario_id=datos_canario["usuario_id"],
        scopes=["support:leer", "support:escribir"],
    )
    version_producto = f"S1.8-test-{secrets.token_hex(4)}"
    r = client.post(
        "/support/changelog",
        headers=_auth(token_admin),
        json={
            "version_producto": version_producto,
            "resumen": "Changelog de prueba de integracion.",
            "items": [
                {
                    "modulo_codigo": "M5",
                    "tipo_cambio": "mejora",
                    "descripcion": "Mejora del motor de facturacion.",
                }
            ],
        },
    )
    assert r.status_code == 201, r.text

    # FR-016: visible sin condicionar a licencia de M5 -- la ruta /support/*
    # ni siquiera pasa por el middleware de licenciamiento (research.md
    # Decision 7), asi que cualquier tenant autenticado lo ve.
    token_tenant = _token_tenant(datos_canario, scopes=["support:leer"])
    r = client.get("/support/changelog", headers=_auth(token_tenant))
    assert r.status_code == 200, r.text
    entradas = [c for c in r.json() if c["version_producto"] == version_producto]
    assert len(entradas) == 1
    assert entradas[0]["items"][0]["tipo_cambio"] == "mejora"


def test_role_tenant_no_puede_publicar_changelog(client, datos_canario):
    token_tenant = _token_tenant(datos_canario, scopes=["support:leer", "support:escribir"])
    r = client.post(
        "/support/changelog",
        headers=_auth(token_tenant),
        json={
            "version_producto": _titulo_unico("v"),
            "resumen": "x",
            "items": [],
        },
    )
    assert r.status_code == 403, r.text
