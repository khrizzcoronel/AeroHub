"""Integracion contra MonetDB real de los casos de uso escritos en S1.1
(Plan §8.1): CU-O18 `aprovisionar_tenant` y las altas/transiciones de vuelo
de `aerohub_aodb`. Requiere `docker compose -f infra/docker-compose.yml up -d
monetdb` con la DDL aplicada y el seed corrido (`uv run python -m
db.migrations.apply` + `uv run python -m db.seeds.generate`) -- se salta
automaticamente si no hay conexion disponible.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime

import pytest
from aerohub_aodb.application import (
    EstadoDesconocido,
    VueloNoEncontrado,
    alta_vuelo,
    registrar_cambio_estado,
)
from aerohub_aodb.domain import TransicionEstadoInvalida
from aerohub_kernel import generar_id
from aerohub_repository import contexto
from aerohub_tenancy.application import aprovisionar_tenant
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
    """Referencias fijas sembradas por db/seeds/generate.py (tenant MEC/UIO,
    aerolinea XX, aeronave HC-DEV1, tipo_vuelo comercial, catalogo de
    estados) -- falla con un mensaje claro si el seed no corrio.
    """
    with admin_engine.connect() as conn:
        mec = conn.execute(
            text("SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).fetchone()
        uio = conn.execute(
            text("SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).fetchone()
        aerolinea = conn.execute(
            text("SELECT id FROM catalogo.aerolinea WHERE codigo_iata = 'XX'")
        ).fetchone()
        aeronave = conn.execute(
            text("SELECT id FROM catalogo.aeronave WHERE matricula = 'HC-DEV1'")
        ).fetchone()
        tipo_vuelo = conn.execute(
            text("SELECT id FROM catalogo.tipo_vuelo WHERE codigo = 'comercial'")
        ).fetchone()
        plan = conn.execute(
            text("SELECT id FROM tenants.plan WHERE codigo = 'PLAN-CANARIO'")
        ).fetchone()
    faltantes = [
        nombre
        for nombre, fila in (
            ("tenant MEC", mec),
            ("tenant UIO", uio),
            ("aerolinea XX", aerolinea),
            ("aeronave HC-DEV1", aeronave),
            ("tipo_vuelo comercial", tipo_vuelo),
            ("plan PLAN-CANARIO", plan),
        )
        if fila is None
    ]
    if faltantes:
        pytest.fail(
            f"Datos canario no encontrados ({', '.join(faltantes)}) -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "aeropuerto_origen_id": mec.aeropuerto_id,
        "aeropuerto_destino_id": uio.aeropuerto_id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "tipo_vuelo_id": tipo_vuelo.id,
        "plan_id": plan.id,
    }


@pytest.fixture()
def contexto_operaciones(datos_canario):
    token_t = contexto._establecer_tenant_id(datos_canario["tenant_id"])
    token_r = contexto._establecer_rol_actor("role_operations_controller")
    token_u = contexto._establecer_usuario_id(None)
    yield datos_canario
    contexto._tenant_id.reset(token_t)
    contexto._rol_actor.reset(token_r)
    contexto._usuario_id.reset(token_u)


def test_alta_vuelo_persiste_journal_y_auditoria_en_una_transaccion(
    contexto_operaciones, admin_engine
):
    datos = contexto_operaciones
    numero_vuelo = f"IT{generar_id() % 100_000}"

    resultado = alta_vuelo(
        aerolinea_id=datos["aerolinea_id"],
        aeronave_id=datos["aeronave_id"],
        numero_vuelo=numero_vuelo,
        tipo_vuelo_id=datos["tipo_vuelo_id"],
        fecha_operacion=date(2026, 9, 1),
        sentido="S",
        aeropuerto_origen_id=datos["aeropuerto_origen_id"],
        aeropuerto_destino_id=datos["aeropuerto_destino_id"],
        sta_utc=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        std_utc=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
    )

    with admin_engine.connect() as conn:
        fila_vuelo = conn.execute(
            text("SELECT tenant_id, numero_vuelo FROM ops.vuelo WHERE id = :id"),
            {"id": resultado.vuelo_id},
        ).fetchone()
        filas_journal = conn.execute(
            text(
                "SELECT clave_primaria FROM continuidad.journal_mutacion "
                "WHERE esquema = 'ops' AND tabla = 'vuelo' AND tenant_id = :t"
            ),
            {"t": datos["tenant_id"]},
        ).fetchall()
        filas_auditoria = conn.execute(
            text(
                "SELECT rol_codigo FROM compliance.log_auditoria "
                "WHERE esquema = 'ops' AND tabla = 'vuelo' AND registro_id = :id"
            ),
            {"id": resultado.vuelo_id},
        ).fetchall()

    assert fila_vuelo is not None
    assert fila_vuelo.tenant_id == datos["tenant_id"]
    assert fila_vuelo.numero_vuelo == numero_vuelo
    assert any(str(resultado.vuelo_id) in str(f.clave_primaria) for f in filas_journal), (
        "no se encontro entrada de journal para el vuelo recien creado"
    )
    assert len(filas_auditoria) == 1
    assert filas_auditoria[0].rol_codigo == "role_operations_controller"


def test_alta_vuelo_rechaza_datos_invalidos_antes_de_tocar_la_base(contexto_operaciones):
    """Fail-fast (RNF-M01): sentido invalido nunca llega al motor -- lo
    rechaza el dominio (Vuelo.__post_init__) antes de abrir sesion().
    """
    datos = contexto_operaciones
    from aerohub_aodb.domain import VueloInvalido

    with pytest.raises(VueloInvalido):
        alta_vuelo(
            aerolinea_id=datos["aerolinea_id"],
            aeronave_id=datos["aeronave_id"],
            numero_vuelo="ZZ999",
            tipo_vuelo_id=datos["tipo_vuelo_id"],
            fecha_operacion=date(2026, 9, 1),
            sentido="X",
            aeropuerto_origen_id=datos["aeropuerto_origen_id"],
            aeropuerto_destino_id=datos["aeropuerto_destino_id"],
            sta_utc=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            std_utc=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        )


def test_registrar_cambio_estado_transicion_valida_persiste(contexto_operaciones, admin_engine):
    datos = contexto_operaciones
    numero_vuelo = f"IT{generar_id() % 100_000}"
    vuelo = alta_vuelo(
        aerolinea_id=datos["aerolinea_id"],
        aeronave_id=datos["aeronave_id"],
        numero_vuelo=numero_vuelo,
        tipo_vuelo_id=datos["tipo_vuelo_id"],
        fecha_operacion=date(2026, 9, 2),
        sentido="S",
        aeropuerto_origen_id=datos["aeropuerto_origen_id"],
        aeropuerto_destino_id=datos["aeropuerto_destino_id"],
        sta_utc=datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
        std_utc=datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
    )

    resultado = registrar_cambio_estado(
        vuelo_id=vuelo.vuelo_id, codigo_estado_nuevo="embarcando", origen_cambio="manual"
    )

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT vuelo_id, origen_cambio FROM ops.vuelo_estado WHERE id = :id"),
            {"id": resultado.vuelo_estado_id},
        ).fetchone()
    assert fila is not None
    assert fila.vuelo_id == vuelo.vuelo_id
    assert fila.origen_cambio == "manual"


def test_registrar_cambio_estado_transicion_invalida_desde_terminal_se_rechaza(
    contexto_operaciones,
):
    datos = contexto_operaciones
    numero_vuelo = f"IT{generar_id() % 100_000}"
    vuelo = alta_vuelo(
        aerolinea_id=datos["aerolinea_id"],
        aeronave_id=datos["aeronave_id"],
        numero_vuelo=numero_vuelo,
        tipo_vuelo_id=datos["tipo_vuelo_id"],
        fecha_operacion=date(2026, 9, 3),
        sentido="S",
        aeropuerto_origen_id=datos["aeropuerto_origen_id"],
        aeropuerto_destino_id=datos["aeropuerto_destino_id"],
        sta_utc=datetime(2026, 9, 3, 10, 0, tzinfo=UTC),
        std_utc=datetime(2026, 9, 3, 9, 0, tzinfo=UTC),
    )
    registrar_cambio_estado(
        vuelo_id=vuelo.vuelo_id, codigo_estado_nuevo="cancelado", origen_cambio="manual"
    )

    with pytest.raises(TransicionEstadoInvalida):
        registrar_cambio_estado(
            vuelo_id=vuelo.vuelo_id, codigo_estado_nuevo="embarcando", origen_cambio="manual"
        )


def test_registrar_cambio_estado_vuelo_ajeno_es_no_encontrado(contexto_operaciones, admin_engine):
    """PN-01: un vuelo_id que existe pero es de OTRO tenant se trata como
    inexistente, nunca como un caso de "prohibido" que confirme su
    existencia.
    """
    with admin_engine.connect() as conn:
        vuelo_uio = conn.execute(
            text(
                "SELECT v.id FROM ops.vuelo v JOIN tenants.tenant t ON v.tenant_id = t.id "
                "WHERE t.codigo = 'UIO'"
            )
        ).fetchone()
    assert vuelo_uio is not None

    with pytest.raises(VueloNoEncontrado):
        registrar_cambio_estado(
            vuelo_id=vuelo_uio.id, codigo_estado_nuevo="embarcando", origen_cambio="manual"
        )


def test_registrar_cambio_estado_codigo_desconocido_se_rechaza(contexto_operaciones):
    datos = contexto_operaciones
    numero_vuelo = f"IT{generar_id() % 100_000}"
    vuelo = alta_vuelo(
        aerolinea_id=datos["aerolinea_id"],
        aeronave_id=datos["aeronave_id"],
        numero_vuelo=numero_vuelo,
        tipo_vuelo_id=datos["tipo_vuelo_id"],
        fecha_operacion=date(2026, 9, 4),
        sentido="S",
        aeropuerto_origen_id=datos["aeropuerto_origen_id"],
        aeropuerto_destino_id=datos["aeropuerto_destino_id"],
        sta_utc=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
        std_utc=datetime(2026, 9, 4, 9, 0, tzinfo=UTC),
    )

    with pytest.raises(EstadoDesconocido):
        registrar_cambio_estado(
            vuelo_id=vuelo.vuelo_id, codigo_estado_nuevo="no-existe", origen_cambio="manual"
        )


def test_aprovisionar_tenant_crea_tenant_y_admin_en_una_transaccion(datos_canario, admin_engine):
    codigo = f"IT{generar_id() % 1_000_000}"
    inicio = time.monotonic()

    resultado = aprovisionar_tenant(
        codigo=codigo,
        razon_social=f"Tenant de integracion {codigo}",
        aeropuerto_id=datos_canario["aeropuerto_origen_id"],
        plan_id=datos_canario["plan_id"],
        email_admin=f"admin@{codigo.lower()}.aerohub.test",
        nombre_admin="Admin de integracion",
    )

    duracion_s = time.monotonic() - inicio
    # RNF-P04: aprovisionamiento de tenant < 10 minutos. En la practica esto
    # es una sola transaccion sincronica -- la medicion es una guarda contra
    # una regresion catastrofica, no un benchmark de rendimiento.
    assert duracion_s < 600

    with admin_engine.connect() as conn:
        fila_tenant = conn.execute(
            text("SELECT codigo, estado FROM tenants.tenant WHERE id = :id"),
            {"id": resultado.tenant_id},
        ).fetchone()
        fila_usuario = conn.execute(
            text("SELECT tenant_id, email FROM tenants.usuario WHERE id = :id"),
            {"id": resultado.usuario_admin_id},
        ).fetchone()
        filas_journal = conn.execute(
            text(
                "SELECT tabla, tenant_id FROM continuidad.journal_mutacion "
                "WHERE tenant_id = :t"
            ),
            {"t": resultado.tenant_id},
        ).fetchall()
        filas_auditoria = conn.execute(
            text(
                "SELECT tabla, rol_codigo, tenant_id FROM compliance.log_auditoria "
                "WHERE tenant_id = :t"
            ),
            {"t": resultado.tenant_id},
        ).fetchall()

    assert fila_tenant is not None
    assert fila_tenant.codigo == codigo
    assert fila_tenant.estado == "en_onboarding"
    assert fila_usuario is not None
    assert fila_usuario.tenant_id == resultado.tenant_id
    assert resultado.password_temporal  # no vacio -- se muestra una sola vez

    tablas_journal = {f.tabla for f in filas_journal}
    assert tablas_journal == {"tenant", "usuario"}
    assert all(f.tenant_id == resultado.tenant_id for f in filas_journal), (
        "el journal de aprovisionamiento debe atribuirse al tenant nuevo, "
        "no a None, aunque quien ejecuta la operacion sea role_platform_admin "
        "sin tenant propio (alcance_global)"
    )

    tablas_auditoria = {f.tabla for f in filas_auditoria}
    assert tablas_auditoria == {"tenant", "usuario"}
    assert all(f.rol_codigo == "role_platform_admin" for f in filas_auditoria)
    assert all(f.tenant_id == resultado.tenant_id for f in filas_auditoria)
