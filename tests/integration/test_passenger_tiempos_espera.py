"""Compuertas de pruebas de S1.6 (M6, Plan Sec8.6): PN-11 (0 campos de PII
en billing.tiempo_espera_agregado), frescura <= 15 min (RF-O17), y
segregacion de funciones (role_support sin acceso a `passenger`, mismo
mecanismo que `billing` -- ver test_billing_facturacion.py).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id
from sqlalchemy import text

_ROL_OPERATIONS_CONTROLLER = "role_operations_controller"
_ROL_SUPPORT = "role_support"

_COLUMNAS_ESPERADAS = {
    "id",
    "tenant_id",
    "terminal_id",
    "fecha",
    "franja_inicio",
    "franja_fin",
    "minutos_estimados",
    "muestra_n",
    "calculado_en",
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
    if mec is None or usuario is None:
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {"tenant_id": mec.id, "usuario_id": usuario.id}


@pytest.fixture()
def terminal_y_puerta_con_asignacion_completada(admin_engine, datos_canario):
    """MonetDB no expone un endpoint de alta de terminal/puerta en el
    alcance de S1.6 -- se insertan directo por SQL admin (mismo patron que
    tests/integration/test_pn05_asignacion_puertas.py)."""
    tenant_id = datos_canario["tenant_id"]
    terminal_id = generar_id()
    puerta_id = generar_id()
    asignacion_id = generar_id()
    vuelo_id = generar_id()

    ahora = datetime.now(UTC).replace(microsecond=0)
    inicio_previsto = ahora.replace(hour=8, minute=10, second=0)
    inicio_real = inicio_previsto
    fin_real = inicio_previsto + timedelta(minutes=18)

    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ops.terminal (id, tenant_id, codigo, nombre) "
                "VALUES (:id, :t, :codigo, 'Terminal de prueba S1.6')"
            ),
            {"id": terminal_id, "t": tenant_id, "codigo": f"PX{terminal_id % 100000}"},
        )
        conn.execute(
            text(
                "INSERT INTO ops.puerta "
                "(id, tenant_id, terminal_id, codigo, tipo, envergadura_max_m, tiene_pasarela) "
                "VALUES (:id, :t, :term, :codigo, 'contacto', 36.0, false)"
            ),
            {
                "id": puerta_id,
                "t": tenant_id,
                "term": terminal_id,
                "codigo": f"G{puerta_id % 100000}",
            },
        )
        # asignacion_puerta.vuelo_id lleva FK a ops.vuelo -- se inserta un
        # vuelo minimo solo para satisfacerla, no participa del calculo.
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
        conn.execute(
            text(
                "INSERT INTO ops.vuelo "
                "(id, tenant_id, aerolinea_id, aeronave_id, numero_vuelo, tipo_vuelo_id, "
                "fecha_operacion, sentido, aeropuerto_origen_id, aeropuerto_destino_id, "
                "sta_utc, std_utc) "
                "VALUES (:id, :t, :aerolinea, :aeronave, :numero, :tipo_vuelo, :fecha, 'S', "
                ":origen, :destino, :sta, :std)"
            ),
            {
                "id": vuelo_id,
                "t": tenant_id,
                "aerolinea": aerolinea.id,
                "aeronave": aeronave.id,
                "numero": f"PX{vuelo_id % 100000}",
                "tipo_vuelo": tipo_vuelo.id,
                "fecha": ahora.date(),
                "origen": aeropuerto_mec.aeropuerto_id,
                "destino": aeropuerto_uio.aeropuerto_id,
                "sta": ahora,
                "std": ahora,
            },
        )
        conn.execute(
            text(
                "INSERT INTO ops.asignacion_puerta "
                "(id, tenant_id, vuelo_id, puerta_id, inicio_previsto, fin_previsto, "
                "inicio_real, fin_real, asignado_por_usuario_id, estado) "
                "VALUES (:id, :t, :vuelo, :puerta, :ip, :fp, :ir, :fr, :usuario, 'finalizada')"
            ),
            {
                "id": asignacion_id,
                "t": tenant_id,
                "vuelo": vuelo_id,
                "puerta": puerta_id,
                "ip": inicio_previsto,
                "fp": inicio_previsto + timedelta(hours=1),
                "ir": inicio_real,
                "fr": fin_real,
                "usuario": datos_canario["usuario_id"],
            },
        )
    return {"terminal_id": terminal_id, "fecha": ahora.date().isoformat()}


def _token_operations_controller(datos_canario) -> str:
    return _token(
        rol=_ROL_OPERATIONS_CONTROLLER,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["passenger:leer", "passenger:escribir"],
    )


# ---------------------------------------------------------------------------
# US4: estimacion agregada de tiempos de espera (CU-O19, RF-O17)
# ---------------------------------------------------------------------------


def test_recalcular_y_leer_tiempos_espera(
    client, datos_canario, terminal_y_puerta_con_asignacion_completada
):
    token = _token_operations_controller(datos_canario)
    terminal_id = terminal_y_puerta_con_asignacion_completada["terminal_id"]
    fecha = terminal_y_puerta_con_asignacion_completada["fecha"]

    r = client.post(
        "/passenger/tiempos-espera/recalcular",
        headers=_auth(token),
        json={"terminal_id": str(terminal_id), "fecha": fecha, "franja_minutos": 30},
    )
    assert r.status_code == 200, r.text
    assert r.json()["franjas_actualizadas"] == 1

    r_leer = client.get(
        "/passenger/tiempos-espera",
        headers=_auth(token),
        params={"terminal_id": str(terminal_id), "fecha": fecha},
    )
    assert r_leer.status_code == 200, r_leer.text
    franjas = r_leer.json()["franjas"]
    assert len(franjas) == 1
    assert franjas[0]["muestra_n"] == 1
    # 18 minutos de ocupacion real de la unica asignacion de la fixture.
    assert franjas[0]["minutos_estimados"] == "18.00"


def test_frescura_calculado_en_reciente(
    client, datos_canario, terminal_y_puerta_con_asignacion_completada
):
    token = _token_operations_controller(datos_canario)
    terminal_id = terminal_y_puerta_con_asignacion_completada["terminal_id"]
    fecha = terminal_y_puerta_con_asignacion_completada["fecha"]

    client.post(
        "/passenger/tiempos-espera/recalcular",
        headers=_auth(token),
        json={"terminal_id": str(terminal_id), "fecha": fecha, "franja_minutos": 30},
    )
    r = client.get(
        "/passenger/tiempos-espera",
        headers=_auth(token),
        params={"terminal_id": str(terminal_id), "fecha": fecha},
    )
    calculado_en = datetime.fromisoformat(r.json()["franjas"][0]["calculado_en"])
    antiguedad = datetime.now(UTC) - calculado_en
    assert antiguedad < timedelta(minutes=15), (
        f"calculado_en tiene {antiguedad} de antiguedad -- RF-O17 exige <= 15 min"
    )


def test_pn11_columnas_de_tiempo_espera_agregado_sin_pii(admin_engine):
    with admin_engine.connect() as conn:
        filas = conn.execute(
            text(
                "SELECT c.name FROM sys.columns c "
                "JOIN sys.tables t ON c.table_id = t.id "
                "JOIN sys.schemas s ON t.schema_id = s.id "
                "WHERE s.name = 'billing' AND t.name = 'tiempo_espera_agregado'"
            )
        ).fetchall()
    columnas = {f.name for f in filas}
    assert columnas == _COLUMNAS_ESPERADAS, (
        f"billing.tiempo_espera_agregado tiene columnas inesperadas: "
        f"{columnas - _COLUMNAS_ESPERADAS} -- PN-11 exige 0 campos de PII"
    )


# ---------------------------------------------------------------------------
# FR-008 / SC-003 analogo en M6: segregacion de funciones
# ---------------------------------------------------------------------------


def test_role_support_no_puede_leer_tiempos_espera(client, datos_canario):
    token_support = _token(
        rol=_ROL_SUPPORT,
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["passenger:leer"],
    )
    r = client.get(
        "/passenger/tiempos-espera",
        headers=_auth(token_support),
        params={"terminal_id": "1", "fecha": "2026-01-01"},
    )
    assert r.status_code == 403, r.text
    assert r.json() == {"detail": "acceso denegado"}
