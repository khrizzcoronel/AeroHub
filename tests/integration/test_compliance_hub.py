"""Integracion HTTP de los listados/catalogos nuevos del Compliance Hub
(Sprint S1.19, PLAN v3.0 §8-bis.5, specs/021-compliance-hub/) -- cierra
en el frontend a M9, que hasta este sprint no tenia ninguna vista propia
en apps/web. Mismo patron que test_billing_tarifarios_conciliacion.py:
`client`/`admin_engine` vienen de tests/integration/conftest.py.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_SRE = "role_sre"
_ROL_REGULATORY_AUDITOR = "role_regulatory_auditor"
_ROL_TENANT_ADMIN = "role_tenant_admin"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(*, rol: str, tenant_id: int, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        uio = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'UIO'")).fetchone()
        usuario_mec = None
        usuario_uio = None
        if mec is not None:
            usuario_mec = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
        if uio is not None:
            usuario_uio = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": uio.id}
            ).fetchone()
        tipo_incidente = conn.execute(
            text("SELECT id FROM compliance.tipo_incidente WHERE codigo = 'acceso_no_autorizado'")
        ).fetchone()
        tipo_reporte = conn.execute(
            text(
                "SELECT id FROM compliance.tipo_reporte_regulatorio "
                "WHERE codigo = 'informe_mensual_operaciones'"
            )
        ).fetchone()
        control_soc2 = conn.execute(
            text("SELECT id FROM compliance.control_soc2 WHERE codigo_control = 'CC6.1'")
        ).fetchone()
    faltantes = (mec, uio, usuario_mec, usuario_uio, tipo_incidente, tipo_reporte, control_soc2)
    if any(f is None for f in faltantes):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_mec_id": mec.id,
        "tenant_uio_id": uio.id,
        "usuario_mec_id": usuario_mec.id,
        "usuario_uio_id": usuario_uio.id,
        "tipo_incidente_id": tipo_incidente.id,
        "tipo_reporte_id": tipo_reporte.id,
        "control_soc2_id": control_soc2.id,
    }


def _token_sre(datos_canario, *, tenant: str = "mec") -> str:
    tenant_id = datos_canario[f"tenant_{tenant}_id"]
    usuario_id = datos_canario[f"usuario_{tenant}_id"]
    return _token(
        rol=_ROL_SRE,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=["compliance:leer", "compliance:escribir"],
    )


def _token_auditor(datos_canario, *, tenant: str = "mec") -> str:
    tenant_id = datos_canario[f"tenant_{tenant}_id"]
    usuario_id = datos_canario[f"usuario_{tenant}_id"]
    return _token(
        rol=_ROL_REGULATORY_AUDITOR,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=["compliance:leer"],
    )


# ---------------------------------------------------------------------------
# role_sre alcanza post-mortems end-to-end (hallazgo corregido en este
# sprint: role_sre no tenia ningun scope compliance:* pese a que
# _exigir_role_sre() lo exige exactamente a el).
# ---------------------------------------------------------------------------


def test_role_sre_crea_incidente_y_post_mortem_y_los_ve_en_los_listados(client, datos_canario):
    token = _token_sre(datos_canario)

    r = client.post(
        "/compliance/incidentes",
        headers=_auth(token),
        json={
            "tipo_incidente_id": str(datos_canario["tipo_incidente_id"]),
            "descripcion": "Intento de acceso detectado por el WAF",
            "severidad": "alta",
            "detectado_en": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/compliance/post-mortems",
        headers=_auth(token),
        json={
            "incidente_ref": "INC-HUB-001",
            "severidad": "alta",
            "iniciado_en": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    post_mortem_id = r.json()["post_mortem_id"]

    r_listar = client.get("/compliance/post-mortems", headers=_auth(token))
    assert r_listar.status_code == 200, r_listar.text
    assert any(p["id"] == post_mortem_id for p in r_listar.json())


def test_role_sre_emite_reporte_dgac_y_lo_ve_en_el_listado_con_hash(client, datos_canario):
    token = _token_sre(datos_canario)
    r = client.post(
        "/compliance/reportes-dgac",
        headers=_auth(token),
        json={
            "tipo_reporte_id": str(datos_canario["tipo_reporte_id"]),
            "periodo_inicio": "2026-07-01",
            "periodo_fin": "2026-07-31",
            "contenido_ref": "s3://reportes/2026-07.pdf",
            "hash_contenido": "a" * 64,
        },
    )
    assert r.status_code == 201, r.text
    reporte_id = r.json()["reporte_id"]

    r_listar = client.get("/compliance/reportes-dgac", headers=_auth(token))
    assert r_listar.status_code == 200, r_listar.text
    encontrado = next((rep for rep in r_listar.json() if rep["id"] == reporte_id), None)
    assert encontrado is not None
    assert encontrado["hash_contenido"] == "a" * 64


# ---------------------------------------------------------------------------
# Catalogos, con role_regulatory_auditor (solo compliance:leer).
# ---------------------------------------------------------------------------


def test_catalogos_compliance_no_estan_vacios(client, datos_canario):
    token = _token_auditor(datos_canario)
    r_tipos_incidente = client.get("/compliance/catalogo/tipos-incidente", headers=_auth(token))
    r_tipos_reporte = client.get("/compliance/catalogo/tipos-reporte", headers=_auth(token))
    r_controles = client.get("/compliance/catalogo/controles-soc2", headers=_auth(token))
    assert r_tipos_incidente.status_code == 200, r_tipos_incidente.text
    assert r_tipos_reporte.status_code == 200, r_tipos_reporte.text
    assert r_controles.status_code == 200, r_controles.text
    assert any(t["codigo"] == "acceso_no_autorizado" for t in r_tipos_incidente.json())
    assert any(t["codigo"] == "informe_mensual_operaciones" for t in r_tipos_reporte.json())
    assert any(c["codigo_control"] == "CC6.1" for c in r_controles.json())


def test_evidencia_soc2_registrar_y_listar_con_role_sre_leer_con_auditor(client, datos_canario):
    token_sre = _token_sre(datos_canario)
    r = client.post(
        "/compliance/evidencia-soc2",
        headers=_auth(token_sre),
        json={
            "control_soc2_id": str(datos_canario["control_soc2_id"]),
            "periodo_inicio": "2026-07-01",
            "periodo_fin": "2026-07-31",
            "ruta_artefacto": "s3://evidencia/cc6.1-2026-07.zip",
            "hash_artefacto": "ffaa0011",
        },
    )
    assert r.status_code == 201, r.text
    evidencia_id = r.json()["evidencia_id"]

    token_auditor = _token_auditor(datos_canario)
    r_listar = client.get("/compliance/evidencia-soc2", headers=_auth(token_auditor))
    assert r_listar.status_code == 200, r_listar.text
    assert any(e["id"] == evidencia_id for e in r_listar.json())


# ---------------------------------------------------------------------------
# Aislamiento de tenant: los listados nuevos filtran por tenant (guardian
# G1/G2, ver CLAUDE.md "Patrones arquitectonicos establecidos").
# ---------------------------------------------------------------------------


def test_listados_nuevos_no_cruzan_tenant(client, datos_canario):
    token_mec = _token_sre(datos_canario, tenant="mec")
    token_uio = _token_sre(datos_canario, tenant="uio")

    r = client.post(
        "/compliance/post-mortems",
        headers=_auth(token_mec),
        json={
            "incidente_ref": "INC-HUB-MEC-001",
            "severidad": "media",
            "iniciado_en": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    post_mortem_mec_id = r.json()["post_mortem_id"]

    r_listar_uio = client.get("/compliance/post-mortems", headers=_auth(token_uio))
    assert r_listar_uio.status_code == 200, r_listar_uio.text
    assert not any(p["id"] == post_mortem_mec_id for p in r_listar_uio.json())
