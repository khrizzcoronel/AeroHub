"""Integracion contra MonetDB real (Sprint S0.2, Plan §7.2, compuerta de
pruebas). Requiere `docker compose -f infra/docker-compose.yml up -d monetdb`
con la DDL aplicada (`uv run python -m db.migrations.apply`); se salta
automaticamente si no hay conexion disponible, en vez de fallar en un
entorno donde el contenedor no esta corriendo.
"""

from __future__ import annotations

import pytest
from aerohub_kernel import generar_id
from aerohub_repository import contexto, registrar_auditoria, sesion
from aerohub_repository.guard import TenantScopeViolation
from aerohub_repository.journal import escribir_journal
from sqlalchemy import BigInteger, Column, MetaData, String, Table, create_engine, insert, text

DSN_ADMIN = "monetdb://monetdb:aerohub@localhost:50000/aerohub"

# Tabla Core minima para este test -- mirror parcial de tenants.usuario
# (db/ddl/monetdb/02_tenants.sql). El objeto Table "real", usado por codigo
# de produccion, llega con services/tenancy/infrastructure/ (Fase 1); aqui
# sirve para ejercitar el flujo con una construccion estructurada (P1), no
# con text() -- el guardian rechaza TextClause categoricamente (ver
# guard.py, test_sql_crudo_texto_se_rechaza_siempre), por diseno.
_metadata = MetaData()
usuario = Table(
    "usuario",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("email", String(254)),
    Column("hash_credencial", String(255)),
    Column("nombre", String(150)),
    Column("estado", String(20)),
    schema="tenants",
)


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
def tenant_de_prueba(admin_engine):
    """Crea pais/aeropuerto/plan/tenant minimos via conexion admin (sin
    pasar por el guardian -- es fixture de datos, no el flujo bajo prueba)
    y los borra al finalizar, en orden inverso de FK.
    """
    pais_id, aeropuerto_id, plan_id, tenant_id = (generar_id() for _ in range(4))
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO catalogo.pais (id, codigo_iso2, codigo_iso3, nombre) "
                "VALUES (:id, :c2, :c3, :n)"
            ),
            {"id": pais_id, "c2": "ZZ", "c3": "ZZZ", "n": "Pais de prueba S0.2"},
        )
        conn.execute(
            text(
                "INSERT INTO catalogo.aeropuerto "
                "(id, codigo_iata, codigo_icao, nombre, pais_id, ciudad, zona_horaria, "
                "latitud, longitud) "
                "VALUES (:id, 'ZZZ', 'ZZZZ', 'Aeropuerto de prueba', :pais_id, 'Ciudad', "
                "'UTC', 0, 0)"
            ),
            {"id": aeropuerto_id, "pais_id": pais_id},
        )
        conn.execute(
            text(
                "INSERT INTO tenants.plan (id, codigo, nombre, tarifa_base_mensual, moneda) "
                "VALUES (:id, :codigo, 'Plan de prueba', 100, 'USD')"
            ),
            {"id": plan_id, "codigo": f"PLAN-TEST-{plan_id}"},
        )
        conn.execute(
            text(
                "INSERT INTO tenants.tenant "
                "(id, codigo, razon_social, aeropuerto_id, plan_id, estado) "
                "VALUES (:id, :codigo, 'Tenant de prueba S0.2', :aeropuerto_id, :plan_id, "
                "'activo')"
            ),
            {
                "id": tenant_id,
                "codigo": f"TEN-TEST-{tenant_id}",
                "aeropuerto_id": aeropuerto_id,
                "plan_id": plan_id,
            },
        )
    yield tenant_id
    with admin_engine.begin() as conn:
        conn.execute(text("DELETE FROM tenants.usuario WHERE tenant_id = :t"), {"t": tenant_id})
        conn.execute(text("DELETE FROM tenants.tenant WHERE id = :t"), {"t": tenant_id})
        conn.execute(text("DELETE FROM tenants.plan WHERE id = :p"), {"p": plan_id})
        conn.execute(text("DELETE FROM catalogo.aeropuerto WHERE id = :a"), {"a": aeropuerto_id})
        conn.execute(text("DELETE FROM catalogo.pais WHERE id = :p"), {"p": pais_id})


@pytest.fixture()
def contexto_role_admin(tenant_de_prueba):
    token_t = contexto._establecer_tenant_id(tenant_de_prueba)
    token_r = contexto._establecer_rol_actor("role_platform_admin")
    token_u = contexto._establecer_usuario_id(None)
    yield tenant_de_prueba
    contexto._tenant_id.reset(token_t)
    contexto._rol_actor.reset(token_r)
    contexto._usuario_id.reset(token_u)


def test_flujo_completo_mutacion_journal_y_auditoria_en_una_transaccion(
    contexto_role_admin, admin_engine
):
    """El caso feliz de P8: una mutacion de negocio real, su journal y su
    auditoria, todo en la MISMA transaccion via sesion(), bajo un rol de
    negocio activado por SET ROLE -- exactamente el flujo que el hallazgo
    de S0.2 sobre IDENTITY/SET ROLE obligo a rediseñar.
    """
    tenant_id = contexto_role_admin
    usuario_id = generar_id()

    with sesion() as conn:
        conn.execute(
            insert(usuario).values(
                id=usuario_id,
                tenant_id=tenant_id,
                email=f"prueba-{usuario_id}@aerohub.test",
                hash_credencial="hash-fake",
                nombre="Prueba S0.2",
                estado="activo",
            )
        )
        lsn = escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario",
            operacion="INSERT",
            clave_primaria={"id": usuario_id},
            payload={"id": usuario_id, "tenant_id": tenant_id},
        )
        auditoria_id = registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=usuario_id,
            operacion="INSERT",
            valores_nuevos={"id": usuario_id, "tenant_id": tenant_id},
        )

    with admin_engine.connect() as conn:
        fila_usuario = conn.execute(
            text("SELECT tenant_id FROM tenants.usuario WHERE id = :id"), {"id": usuario_id}
        ).fetchone()
        fila_journal = conn.execute(
            text("SELECT tenant_id FROM continuidad.journal_mutacion WHERE lsn = :lsn"),
            {"lsn": lsn},
        ).fetchone()
        fila_auditoria = conn.execute(
            text("SELECT tenant_id, rol_codigo FROM compliance.log_auditoria WHERE id = :id"),
            {"id": auditoria_id},
        ).fetchone()

    assert fila_usuario is not None and fila_usuario[0] == tenant_id
    assert fila_journal is not None and fila_journal[0] == tenant_id
    assert fila_auditoria is not None
    assert fila_auditoria[0] == tenant_id
    assert fila_auditoria[1] == "role_platform_admin"


def test_guardian_bloquea_insert_con_tenant_id_ajeno_y_no_persiste_nada(
    contexto_role_admin, admin_engine
):
    tenant_id = contexto_role_admin
    tenant_ajeno = tenant_id + 999999  # nunca existe -- no importa, ni siquiera llega al motor
    usuario_id = generar_id()

    with pytest.raises(TenantScopeViolation), sesion() as conn:
        conn.execute(
            insert(usuario).values(
                id=usuario_id,
                tenant_id=tenant_ajeno,
                email="no-deberia-existir@aerohub.test",
                hash_credencial="hash-fake",
                nombre="Prueba",
                estado="activo",
            )
        )

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT 1 FROM tenants.usuario WHERE id = :id"), {"id": usuario_id}
        ).fetchone()
    assert fila is None


def test_atomicidad_p8_un_fallo_posterior_revierte_journal_y_auditoria(
    contexto_role_admin, admin_engine
):
    """Mutacion + journal + auditoria exitosos, pero la sesion nunca
    confirma (se simula un fallo posterior con una excepcion propia) --
    ninguna de las tres escrituras debe sobrevivir.
    """
    tenant_id = contexto_role_admin
    usuario_id = generar_id()
    lsn_capturado = None
    auditoria_id_capturado = None

    class FalloForzado(Exception):
        pass

    with pytest.raises(FalloForzado), sesion() as conn:
        conn.execute(
            insert(usuario).values(
                id=usuario_id,
                tenant_id=tenant_id,
                email=f"atomicidad-{usuario_id}@aerohub.test",
                hash_credencial="hash-fake",
                nombre="Prueba",
                estado="activo",
            )
        )
        lsn_capturado = escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario",
            operacion="INSERT",
            clave_primaria={"id": usuario_id},
            payload={"id": usuario_id},
        )
        auditoria_id_capturado = registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=usuario_id,
            operacion="INSERT",
        )
        raise FalloForzado("simula un error de negocio posterior al journal/auditoria")

    with admin_engine.connect() as conn:
        assert conn.execute(
            text("SELECT 1 FROM tenants.usuario WHERE id = :id"), {"id": usuario_id}
        ).fetchone() is None
        assert (
            conn.execute(
                text("SELECT 1 FROM continuidad.journal_mutacion WHERE lsn = :lsn"),
                {"lsn": lsn_capturado},
            ).fetchone()
            is None
        )
        assert (
            conn.execute(
                text("SELECT 1 FROM compliance.log_auditoria WHERE id = :id"),
                {"id": auditoria_id_capturado},
            ).fetchone()
            is None
        )
