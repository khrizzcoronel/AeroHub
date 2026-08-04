"""Integracion contra MonetDB real de los listados de administracion FIDS
(Sprint S1.16, PLAN v3.0 §8-bis.2). Requiere
`docker compose -f infra/docker-compose.yml up -d monetdb` con la DDL
aplicada y el seed corrido -- se salta automaticamente si no hay conexion
disponible.
"""

from __future__ import annotations

import pytest
from aerohub_aodb.application import alta_vuelo  # noqa: F401 -- fuerza registro de alcances de ops.*
from aerohub_fids.application import (
    consultar_pantallas,
    consultar_plantillas,
    consultar_terminales,
    publicar_plantilla,
    registrar_pantalla,
)
from aerohub_kernel import generar_id
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
def terminal_canario(admin_engine, datos_canario):
    """No existe (ni lo exige S1.3/S1.16) un endpoint de creacion de
    terminal -- se obtiene o crea directamente por SQL admin, mismo
    patron que tests/integration/test_fids_pn11_rnf_p02_rnf_r04.py.
    """
    tenant_id = datos_canario["tenant_id"]
    with admin_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT id FROM ops.terminal WHERE tenant_id = :t AND codigo = 'T1'"),
            {"t": tenant_id},
        ).fetchone()
        if fila is not None:
            return fila.id
        terminal_id = generar_id()
        conn.execute(
            text(
                "INSERT INTO ops.terminal (id, tenant_id, codigo, nombre) "
                "VALUES (:id, :t, 'T1', 'Terminal 1 (canario)')"
            ),
            {"id": terminal_id, "t": tenant_id},
        )
        conn.commit()
    return terminal_id


@pytest.fixture()
def contexto_fids(datos_canario):
    token_t = contexto._establecer_tenant_id(datos_canario["tenant_id"])
    token_r = contexto._establecer_rol_actor("role_tenant_admin")
    token_u = contexto._establecer_usuario_id(datos_canario["tenant_id"])  # cualquier id valido
    yield datos_canario
    contexto._tenant_id.reset(token_t)
    contexto._rol_actor.reset(token_r)
    contexto._usuario_id.reset(token_u)


def test_consultar_plantillas_devuelve_solo_la_ultima_version(contexto_fids):
    nombre = f"IT-{generar_id() % 1_000_000}"
    r1 = publicar_plantilla(nombre=nombre, definicion_json={"filas": [{"texto": "v1"}]})
    r2 = publicar_plantilla(nombre=nombre, definicion_json={"filas": [{"texto": "v2"}]})
    assert r2.version == r1.version + 1

    plantillas = consultar_plantillas()
    coincidencias = [p for p in plantillas if p.nombre == nombre]
    assert len(coincidencias) == 1, "debe listar solo la ultima version por nombre"
    assert coincidencias[0].version == r2.version
    assert coincidencias[0].id == r2.plantilla_id


def test_consultar_pantallas_incluye_telemetria_real(contexto_fids, terminal_canario):
    nombre = f"IT-{generar_id() % 1_000_000}"
    plantilla = publicar_plantilla(nombre=nombre, definicion_json={"filas": [{"texto": "x"}]})
    codigo = f"IT-PANT-{generar_id() % 1_000_000}"
    resultado = registrar_pantalla(
        terminal_id=terminal_canario, codigo=codigo, plantilla_id=plantilla.plantilla_id
    )

    pantallas = consultar_pantallas()
    creada = next((p for p in pantallas if p.id == resultado.pantalla_id), None)
    assert creada is not None
    assert creada.codigo == codigo
    # sin heartbeat todavia -- 'sin_senal' de entrada (comandos.py::insertar_pantalla).
    assert creada.estado == "sin_senal"
    assert creada.ultima_senal_en is None


def test_consultar_terminales_devuelve_el_catalogo_del_tenant(contexto_fids, terminal_canario):
    terminales = consultar_terminales()
    assert any(t.id == terminal_canario for t in terminales)
