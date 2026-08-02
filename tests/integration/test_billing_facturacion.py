"""Compuertas de pruebas de S1.6 (Plan Sec8.6): inmutabilidad de tarifas
tras un cambio del tarifario vigente, conciliacion con diferencia cero, y
segregacion de funciones (role_support sin acceso a billing).

Mismo patron de `test_rampa_min_privilegio_incidencia.py`: role_billing_
officer no puede escribir en `ops` (matriz 4.3.1, celda '-'), asi que los
vuelos de prueba se crean con un token de role_operations_controller.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from sqlalchemy import text

_ROL_BILLING_OFFICER = "role_billing_officer"
_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"
_ROL_SUPPORT = "role_support"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fecha_unica() -> str:
    """Periodo unico por invocacion -- `factura` lleva UNIQUE sobre
    (tenant_id, aerolinea_id, periodo_inicio, periodo_fin), y
    `calcular_facturacion` agrupa TODOS los vuelos de la aerolinea que
    caigan en el periodo. `generar_id() % N` no sirve para esto: un
    Snowflake incrementa lentamente entre llamadas de la MISMA corrida,
    asi que el modulo colisiona con facilidad entre pruebas o corridas
    sucesivas -- se usa `secrets` (aleatoriedad real) sobre un rango
    amplio (~10000 anios) para que la probabilidad de choque con datos de
    corridas previas sea despreciable."""
    return (date(2000, 1, 1) + timedelta(days=secrets.randbelow(2_900_000))).isoformat()


def _token(*, rol: str, tenant_id: int, usuario_id: int, scopes: list[str]) -> str:
    return codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario = None
        if mec is not None:
            usuario = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
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
        aeropuerto_mec = conn.execute(
            text("SELECT aeropuerto_id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).fetchone()
        aeropuerto_uio = conn.execute(
            text("SELECT aeropuerto_id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).fetchone()
        concepto_aterrizaje = conn.execute(
            text("SELECT id FROM billing.concepto_cargo WHERE codigo = 'tasa_aterrizaje'")
        ).fetchone()
        concepto_pax = conn.execute(
            text("SELECT id FROM billing.concepto_cargo WHERE codigo = 'tasa_pasajero'")
        ).fetchone()
    faltantes = (
        mec,
        usuario,
        aerolinea,
        aeronave,
        tipo_vuelo,
        aeropuerto_mec,
        aeropuerto_uio,
        concepto_aterrizaje,
        concepto_pax,
    )
    if any(f is None for f in faltantes):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "usuario_id": usuario.id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "tipo_vuelo_id": tipo_vuelo.id,
        "aeropuerto_mec_id": aeropuerto_mec.aeropuerto_id,
        "aeropuerto_uio_id": aeropuerto_uio.aeropuerto_id,
        "concepto_aterrizaje_id": concepto_aterrizaje.id,
        "concepto_pax_id": concepto_pax.id,
    }


def _token_billing(datos_canario) -> str:
    return _token(
        rol=_ROL_BILLING_OFFICER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["billing:leer", "billing:escribir"],
    )


def _crear_vuelo(
    client, datos_canario, *, numero_vuelo: str, fecha_operacion: str, pax_estimado: int
):
    token_vuelos = _token(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:escribir"],
    )
    r = client.post(
        "/vuelos",
        headers=_auth(token_vuelos),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "aeronave_id": str(datos_canario["aeronave_id"]),
            "numero_vuelo": numero_vuelo,
            "tipo_vuelo_id": str(datos_canario["tipo_vuelo_id"]),
            "fecha_operacion": fecha_operacion,
            "sentido": "S",
            "aeropuerto_origen_id": str(datos_canario["aeropuerto_mec_id"]),
            "aeropuerto_destino_id": str(datos_canario["aeropuerto_uio_id"]),
            "sta_utc": f"{fecha_operacion}T10:00:00Z",
            "std_utc": f"{fecha_operacion}T09:00:00Z",
            "pax_estimado": pax_estimado,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["vuelo_id"]


def _fijar_tarifa(
    client, token_billing: str, *, tarifario_id, concepto_id, tarifa_unitaria
) -> None:
    r = client.post(
        f"/billing/tarifarios/{tarifario_id}/conceptos",
        headers=_auth(token_billing),
        json={"concepto_cargo_id": str(concepto_id), "tarifa_unitaria": str(tarifa_unitaria)},
    )
    assert r.status_code == 200, r.text


@pytest.fixture()
def tarifario_activo(client, datos_canario, admin_engine):
    """UN solo tarifario 'vigente' en USD, compartido entre las pruebas de
    este archivo (creado una vez, reutilizado despues). `calcular_
    facturacion` elige entre TODOS los tarifarios vigentes del tenant sin
    filtrar por moneda (research.md Decision: multi-moneda simultanea
    fuera de alcance) -- si cada prueba creara su propio tarifario en una
    moneda distinta, coexistirian varios "vigentes" a la vez y el motor
    podria escoger uno ajeno a la prueba. Cada prueba fija la tarifa que
    necesita con `_fijar_tarifa` justo antes de calcular, en vez de crear
    tarifarios nuevos."""
    token_billing = _token_billing(datos_canario)
    with admin_engine.connect() as conn:
        existente = conn.execute(
            text(
                "SELECT id FROM billing.tarifario "
                "WHERE tenant_id = :t AND moneda = 'USD' AND estado = 'vigente'"
            ),
            {"t": datos_canario["tenant_id"]},
        ).fetchone()
    if existente is not None:
        return existente.id

    r = client.post(
        "/billing/tarifarios",
        headers=_auth(token_billing),
        json={
            "nombre": "Tarifario compartido de pruebas",
            "moneda": "USD",
            "vigente_desde": "2020-01-01",
        },
    )
    assert r.status_code == 201, r.text
    tarifario_id = r.json()["tarifario_id"]

    for concepto_id in (datos_canario["concepto_aterrizaje_id"], datos_canario["concepto_pax_id"]):
        _fijar_tarifa(
            client,
            token_billing,
            tarifario_id=tarifario_id,
            concepto_id=concepto_id,
            tarifa_unitaria="0.0000",
        )

    r = client.post(f"/billing/tarifarios/{tarifario_id}/activar", headers=_auth(token_billing))
    assert r.status_code == 204, r.text
    return tarifario_id


# ---------------------------------------------------------------------------
# US1: motor de facturacion (RF-O15)
# ---------------------------------------------------------------------------


def test_calcular_facturacion_genera_cargos_y_factura_que_concilia(
    client, datos_canario, tarifario_activo
):
    token_billing = _token_billing(datos_canario)
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_activo,
        concepto_id=datos_canario["concepto_aterrizaje_id"],
        tarifa_unitaria="100.0000",
    )
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_activo,
        concepto_id=datos_canario["concepto_pax_id"],
        tarifa_unitaria="5.0000",
    )
    fecha = _fecha_unica()
    numero = f"BF{secrets.randbelow(100_000_000)}"
    _crear_vuelo(
        client, datos_canario, numero_vuelo=numero, fecha_operacion=fecha, pax_estimado=100
    )

    r = client.post(
        "/billing/facturacion/calcular",
        headers=_auth(token_billing),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "periodo_inicio": fecha,
            "periodo_fin": fecha,
        },
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["factura_id"] is not None
    assert cuerpo["cargos_calculados"] == 2  # tasa_aterrizaje (x1) + tasa_pasajero (x100 pax)

    r_factura = client.get(
        f"/billing/facturas/{cuerpo['factura_id']}", headers=_auth(token_billing)
    )
    assert r_factura.status_code == 200, r_factura.text
    detalle = r_factura.json()
    # total = 100.00 (aterrizaje, cantidad=1) + 500.00 (pax, 100 * 5.00) -- concilia
    # al 100% con los cargos generados, sin diferencias (RF-O15/SC-001).
    assert detalle["factura"]["total"] == "600.00"
    assert len(detalle["lineas"]) == 2


def test_periodo_sin_vuelos_produce_cero_cargos_sin_error(client, datos_canario):
    token_billing = _token_billing(datos_canario)
    r = client.post(
        "/billing/facturacion/calcular",
        headers=_auth(token_billing),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "periodo_inicio": "2019-01-01",
            "periodo_fin": "2019-01-31",
        },
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["factura_id"] is None
    assert cuerpo["cargos_calculados"] == 0


# ---------------------------------------------------------------------------
# US2: inmutabilidad de tarifas (compuerta de pruebas obligatoria)
# ---------------------------------------------------------------------------


def test_cambiar_tarifa_vigente_no_altera_cargo_ya_calculado(
    client, datos_canario, admin_engine, tarifario_activo
):
    token_billing = _token_billing(datos_canario)
    tarifario_id = tarifario_activo
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_id,
        concepto_id=datos_canario["concepto_aterrizaje_id"],
        tarifa_unitaria="100.0000",
    )
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_id,
        concepto_id=datos_canario["concepto_pax_id"],
        tarifa_unitaria="5.0000",
    )
    fecha = _fecha_unica()
    numero = f"BI{secrets.randbelow(100_000_000)}"
    _crear_vuelo(client, datos_canario, numero_vuelo=numero, fecha_operacion=fecha, pax_estimado=50)

    r = client.post(
        "/billing/facturacion/calcular",
        headers=_auth(token_billing),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "periodo_inicio": fecha,
            "periodo_fin": fecha,
        },
    )
    assert r.status_code == 200, r.text
    factura_id_antes = r.json()["factura_id"]
    r_antes = client.get(f"/billing/facturas/{factura_id_antes}", headers=_auth(token_billing))
    total_antes = r_antes.json()["factura"]["total"]
    assert total_antes == "350.00"  # 100.00 aterrizaje + 250.00 (50 pax * 5.00)

    # Simula una publicacion posterior de tarifas mas altas para el MISMO
    # tarifario -- MonetDB no expone triggers, se hace directo por SQL
    # admin (mismo patron que otras suites que insertan fixtures fuera de
    # los endpoints expuestos).
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE billing.tarifario_concepto SET tarifa_unitaria = 999.0000 "
                "WHERE tarifario_id = :tid AND concepto_cargo_id = :cid"
            ),
            {"tid": int(tarifario_id), "cid": datos_canario["concepto_aterrizaje_id"]},
        )

    r_despues = client.get(f"/billing/facturas/{factura_id_antes}", headers=_auth(token_billing))
    total_despues = r_despues.json()["factura"]["total"]
    assert total_despues == total_antes, (
        "el cargo/factura historico cambio tras publicar una tarifa nueva -- "
        "viola la inmutabilidad financiera (SC-002)"
    )


def test_cargos_calculados_despues_del_cambio_usan_la_tarifa_nueva(
    client, datos_canario, admin_engine, tarifario_activo
):
    token_billing = _token_billing(datos_canario)
    tarifario_id = tarifario_activo
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_id,
        concepto_id=datos_canario["concepto_aterrizaje_id"],
        tarifa_unitaria="200.0000",
    )
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_id,
        concepto_id=datos_canario["concepto_pax_id"],
        tarifa_unitaria="0.0000",
    )

    fecha = _fecha_unica()
    numero = f"BN{secrets.randbelow(100_000_000)}"
    _crear_vuelo(client, datos_canario, numero_vuelo=numero, fecha_operacion=fecha, pax_estimado=0)

    r = client.post(
        "/billing/facturacion/calcular",
        headers=_auth(token_billing),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "periodo_inicio": fecha,
            "periodo_fin": fecha,
        },
    )
    assert r.status_code == 200, r.text
    r_factura = client.get(
        f"/billing/facturas/{r.json()['factura_id']}", headers=_auth(token_billing)
    )
    # Solo el cargo de aterrizaje (pax_estimado=0 -> sin cargo de pasajero)
    # con la tarifa NUEVA (200.00) -- la inmutabilidad protege lo
    # historico, no congela el sistema completo.
    assert r_factura.json()["factura"]["total"] == "200.00"


# ---------------------------------------------------------------------------
# US3: conciliacion (diferencia derivada, nunca forzable a cero) y disputa
# ---------------------------------------------------------------------------


def test_conciliacion_diferencia_cero_permite_marcar_conciliado(client, datos_canario):
    token_billing = _token_billing(datos_canario)
    numero = f"BC{secrets.randbelow(100_000_000)}"
    vuelo_id = _crear_vuelo(
        client, datos_canario, numero_vuelo=numero, fecha_operacion="2026-09-04", pax_estimado=120
    )

    r = client.post(
        "/billing/conciliaciones",
        headers=_auth(token_billing),
        json={
            "vuelo_id": vuelo_id,
            "periodo": "2026-09",
            "pax_reportado_aerolinea": 120,
            "pax_registrado_sistema": 120,
            "fuente_reporte": "manifiesto_aerolinea",
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["diferencia"] == 0

    r_conciliar = client.post(
        f"/billing/conciliaciones/{cuerpo['conciliacion_id']}/conciliar",
        headers=_auth(token_billing),
    )
    assert r_conciliar.status_code == 204, r_conciliar.text


def test_conciliacion_diferencia_no_nula_rechaza_conciliar(client, datos_canario):
    token_billing = _token_billing(datos_canario)
    numero = f"BD{secrets.randbelow(100_000_000)}"
    vuelo_id = _crear_vuelo(
        client, datos_canario, numero_vuelo=numero, fecha_operacion="2026-09-05", pax_estimado=120
    )

    r = client.post(
        "/billing/conciliaciones",
        headers=_auth(token_billing),
        json={
            "vuelo_id": vuelo_id,
            "periodo": "2026-09",
            "pax_reportado_aerolinea": 120,
            "pax_registrado_sistema": 115,
            "fuente_reporte": "manifiesto_aerolinea",
        },
    )
    assert r.status_code == 201, r.text
    conciliacion_id = r.json()["conciliacion_id"]
    assert r.json()["diferencia"] == 5

    r_conciliar = client.post(
        f"/billing/conciliaciones/{conciliacion_id}/conciliar", headers=_auth(token_billing)
    )
    assert r_conciliar.status_code == 409, r_conciliar.text


def test_disputar_factura_no_altera_montos_calculados(client, datos_canario, tarifario_activo):
    token_billing = _token_billing(datos_canario)
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_activo,
        concepto_id=datos_canario["concepto_aterrizaje_id"],
        tarifa_unitaria="100.0000",
    )
    _fijar_tarifa(
        client,
        token_billing,
        tarifario_id=tarifario_activo,
        concepto_id=datos_canario["concepto_pax_id"],
        tarifa_unitaria="0.0000",
    )
    fecha = _fecha_unica()
    numero = f"BP{secrets.randbelow(100_000_000)}"
    _crear_vuelo(client, datos_canario, numero_vuelo=numero, fecha_operacion=fecha, pax_estimado=0)

    r = client.post(
        "/billing/facturacion/calcular",
        headers=_auth(token_billing),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "periodo_inicio": fecha,
            "periodo_fin": fecha,
        },
    )
    factura_id = r.json()["factura_id"]
    client.post(f"/billing/facturas/{factura_id}/emitir", headers=_auth(token_billing))
    total_antes = client.get(
        f"/billing/facturas/{factura_id}", headers=_auth(token_billing)
    ).json()["factura"]["total"]

    r_disputa = client.post(
        f"/billing/facturas/{factura_id}/disputar",
        headers=_auth(token_billing),
        json={"motivo": "monto no coincide con lo esperado"},
    )
    assert r_disputa.status_code == 204, r_disputa.text

    r_despues = client.get(f"/billing/facturas/{factura_id}", headers=_auth(token_billing))
    assert r_despues.json()["factura"]["estado"] == "disputada"
    assert r_despues.json()["factura"]["total"] == total_antes


# ---------------------------------------------------------------------------
# FR-008 / SC-003: segregacion de funciones -- role_support sin acceso
# ---------------------------------------------------------------------------


def test_role_support_no_puede_leer_facturas(client, datos_canario):
    token_support = _token(
        rol=_ROL_SUPPORT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["billing:leer"],
    )
    r = client.get("/billing/facturas", headers=_auth(token_support))
    # 403 sin fuga de informacion (PN-07) -- role_support no tiene NINGUN
    # grant sobre `billing` (98_grants_billing.sql); el motor mismo
    # rechaza el SELECT via SET ROLE, traducido por
    # services/gateway/main.py::_manejador_acceso_denegado_motor.
    assert r.status_code == 403, r.text
    assert r.json() == {"detail": "acceso denegado"}
