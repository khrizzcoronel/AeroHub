"""Integracion contra MonetDB real de los catalogos de apoyo al formulario
de alta de vuelo (Sprint S1.15, PLAN v3.0 §8-bis.1). Requiere
`docker compose -f infra/docker-compose.yml up -d monetdb` con la DDL
aplicada y el seed corrido -- se salta automaticamente si no hay conexion
disponible.
"""

from __future__ import annotations

import pytest
from aerohub_aodb.application import consultar_aerolineas, consultar_aeronaves, consultar_tipos_vuelo
from aerohub_repository import contexto
from sqlalchemy import create_engine, text

DSN_ADMIN = "monetdb://monetdb:aerohub@localhost:50000/aerohub"


def _hay_monetdb() -> bool:
    try:
        engine = create_engine(DSN_ADMIN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _hay_monetdb(), reason="MonetDB no disponible en localhost:50000"
)


@pytest.fixture()
def admin_engine():
    return create_engine(DSN_ADMIN)


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
    if mec is None:
        pytest.fail(
            "Tenant canario MEC no encontrado -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {"tenant_id": mec.id}


@pytest.fixture()
def contexto_operaciones(datos_canario):
    token_t = contexto._establecer_tenant_id(datos_canario["tenant_id"])
    token_r = contexto._establecer_rol_actor("role_operations_controller")
    token_u = contexto._establecer_usuario_id(None)
    yield datos_canario
    contexto._tenant_id.reset(token_t)
    contexto._rol_actor.reset(token_r)
    contexto._usuario_id.reset(token_u)


def test_consultar_aerolineas_devuelve_el_catalogo_sembrado(contexto_operaciones):
    aerolineas = consultar_aerolineas()
    assert len(aerolineas) > 0
    codigos = {a.codigo_iata for a in aerolineas}
    assert "XX" in codigos  # aerolinea canario sembrada por db/seeds/generate.py


def test_consultar_aeronaves_trae_fabricante_y_modelo_del_join(contexto_operaciones):
    aeronaves = consultar_aeronaves()
    assert len(aeronaves) > 0
    canario = next((a for a in aeronaves if a.matricula == "HC-DEV1"), None)
    assert canario is not None, "aeronave canario HC-DEV1 no encontrada -- correr el seed"
    # El join contra catalogo.modelo_aeronave debe traer datos reales, no
    # vacios -- confirma que listar_aeronaves() no se quedo con un LEFT
    # JOIN silenciosamente nulo.
    assert canario.fabricante
    assert canario.modelo


def test_consultar_tipos_vuelo_incluye_los_5_codigos_del_check(contexto_operaciones):
    tipos = consultar_tipos_vuelo()
    codigos = {t.codigo for t in tipos}
    # chk_tipo_vuelo_codigo (db/ddl/monetdb/01_catalogo.sql) fija exactamente
    # estos 5 valores -- catalogo cerrado, cobertura exhaustiva esperable.
    assert codigos == {"comercial", "carga", "charter", "aviacion_general", "militar"}
