"""Genera datos sinteticos de desarrollo: 2 tenants + filas canario
permanentes (Plan §7.2, S0.2).

Las filas canario tienen codigo/email FIJOS (no aleatorios): la suite
cruzada por tenant (tests/cross_tenant/, ADR-019 G4) y la suite de PN-01/02
de fases posteriores las referencian por nombre para verificar, en cada
ejecucion, que el tenant A nunca ve una fila del tenant B -- necesitan un
punto de referencia estable, no datos que cambien en cada corrida.

Se ejecuta con conexion admin directa (no via aerohub_repository.sesion()):
es un script de arranque de entorno de desarrollo, no una peticion de
aplicacion con contexto de tenant/rol ya establecido -- el mismo principio
que db/migrations/apply.py.

Uso:
    uv run python -m db.seeds.generate
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

import pymonetdb
from aerohub_kernel import generar_id, hash_credencial

# Codigos y emails fijos -- referenciados por tests/cross_tenant/.
TENANTS_CANARIO = [
    {
        "codigo": "MEC",
        "razon_social": "Aeropuerto de prueba MEC (canario)",
        "aeropuerto_iata": "MEC",
    },
    {
        "codigo": "UIO",
        "razon_social": "Aeropuerto de prueba UIO (canario)",
        "aeropuerto_iata": "UIO",
    },
]


def _obtener_o_crear_pais(cur, codigo_iso2: str, codigo_iso3: str, nombre: str) -> int:
    cur.execute("SELECT id FROM catalogo.pais WHERE codigo_iso2 = %s", (codigo_iso2,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO catalogo.pais (id, codigo_iso2, codigo_iso3, nombre) VALUES (%s, %s, %s, %s)",
        (id_, codigo_iso2, codigo_iso3, nombre),
    )
    return id_


def _obtener_o_crear_aeropuerto(cur, codigo_iata: str, pais_id: int) -> int:
    cur.execute("SELECT id FROM catalogo.aeropuerto WHERE codigo_iata = %s", (codigo_iata,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO catalogo.aeropuerto "
        "(id, codigo_iata, codigo_icao, nombre, pais_id, ciudad, zona_horaria, latitud, longitud) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            codigo_iata,
            f"S{codigo_iata}",
            f"Aeropuerto {codigo_iata}",
            pais_id,
            codigo_iata,
            "America/Guayaquil",
            -0.5,
            -78.5,
        ),
    )
    return id_


def _obtener_o_crear_aerolinea(cur, codigo_iata: str, pais_id: int) -> int:
    cur.execute("SELECT id FROM catalogo.aerolinea WHERE codigo_iata = %s", (codigo_iata,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO catalogo.aerolinea (id, codigo_iata, codigo_icao, nombre, pais_id) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_, codigo_iata, f"{codigo_iata}X", f"Aerolinea {codigo_iata} (desarrollo)", pais_id),
    )
    return id_


def _obtener_o_crear_modelo_aeronave(cur, codigo_icao_tipo: str) -> int:
    cur.execute(
        "SELECT id FROM catalogo.modelo_aeronave WHERE codigo_icao_tipo = %s", (codigo_icao_tipo,)
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO catalogo.modelo_aeronave "
        "(id, codigo_icao_tipo, fabricante, modelo, capacidad_pax_tipica, envergadura_m, "
        "categoria_estela) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (id_, codigo_icao_tipo, "Fabricante de desarrollo", codigo_icao_tipo, 180, 35.8, "M"),
    )
    return id_


def _obtener_o_crear_aeronave(
    cur, matricula: str, modelo_aeronave_id: int, aerolinea_id: int
) -> int:
    cur.execute("SELECT id FROM catalogo.aeronave WHERE matricula = %s", (matricula,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO catalogo.aeronave (id, matricula, modelo_aeronave_id, aerolinea_id) "
        "VALUES (%s, %s, %s, %s)",
        (id_, matricula, modelo_aeronave_id, aerolinea_id),
    )
    return id_


def _obtener_o_crear_estado_vuelo(cur, codigo: str, descripcion: str, es_terminal: bool) -> int:
    cur.execute("SELECT id FROM catalogo.estado_vuelo_catalogo WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO catalogo.estado_vuelo_catalogo (id, codigo, descripcion, es_terminal) "
        "VALUES (%s, %s, %s, %s)",
        (id_, codigo, descripcion, es_terminal),
    )
    return id_


# Catalogo de estados de vuelo minimo para desarrollo/pruebas -- dominio
# ABIERTO por SDD-DATA-001 §5.8 (a diferencia de catalogo.tipo_vuelo, que
# es cerrado por CHECK y se siembra en la DDL misma, 01_catalogo.sql). Este
# conjunto cubre el ciclo de vida basico de un vuelo; se amplia cuando un
# caso de uso real lo requiera, no antes.
ESTADOS_VUELO = [
    ("programado", "Vuelo programado", False),
    ("embarcando", "Embarque en curso", False),
    ("en_vuelo", "En vuelo", False),
    ("aterrizado", "Aterrizado", True),
    ("cancelado", "Cancelado", True),
    ("desviado", "Desviado a otro aeropuerto", True),
]


def _obtener_o_crear_plan(cur, codigo: str) -> int:
    cur.execute("SELECT id FROM tenants.plan WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO tenants.plan (id, codigo, nombre, tarifa_base_mensual, moneda) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_, codigo, "Plan Canario (desarrollo)", 0, "USD"),
    )
    return id_


def _obtener_o_crear_vuelo_canario(
    cur,
    *,
    tenant_id: int,
    numero_vuelo: str,
    aerolinea_id: int,
    aeronave_id: int,
    tipo_vuelo_id: int,
    aeropuerto_origen_id: int,
    aeropuerto_destino_id: int,
) -> int:
    cur.execute(
        "SELECT id FROM ops.vuelo WHERE tenant_id = %s AND numero_vuelo = %s",
        (tenant_id, numero_vuelo),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO ops.vuelo "
        "(id, tenant_id, aerolinea_id, aeronave_id, numero_vuelo, tipo_vuelo_id, "
        "fecha_operacion, sentido, aeropuerto_origen_id, aeropuerto_destino_id, sta_utc, std_utc) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'S', %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            aerolinea_id,
            aeronave_id,
            numero_vuelo,
            tipo_vuelo_id,
            date(2026, 8, 1),
            aeropuerto_origen_id,
            aeropuerto_destino_id,
            datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
        ),
    )
    return id_


def _obtener_o_crear_estado_vuelo_actual(
    cur, *, tenant_id: int, vuelo_id: int, estado_id: int
) -> int:
    cur.execute(
        "SELECT id FROM ops.vuelo_estado WHERE vuelo_id = %s ORDER BY registrado_en DESC",
        (vuelo_id,),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO ops.vuelo_estado "
        "(id, tenant_id, vuelo_id, estado_id, origen_cambio) "
        "VALUES (%s, %s, %s, %s, 'manual')",
        (id_, tenant_id, vuelo_id, estado_id),
    )
    return id_


def sembrar(*, hostname: str, port: int, database: str, username: str, password: str) -> None:
    conn = pymonetdb.connect(
        hostname=hostname, port=port, database=database, username=username, password=password
    )
    try:
        cur = conn.cursor()
        pais_id = _obtener_o_crear_pais(cur, "EC", "ECU", "Ecuador")
        plan_id = _obtener_o_crear_plan(cur, "PLAN-CANARIO")

        estados_por_codigo: dict[str, int] = {}
        for codigo, descripcion, es_terminal in ESTADOS_VUELO:
            estados_por_codigo[codigo] = _obtener_o_crear_estado_vuelo(
                cur, codigo, descripcion, es_terminal
            )

        aerolinea_id = _obtener_o_crear_aerolinea(cur, "XX", pais_id)
        modelo_aeronave_id = _obtener_o_crear_modelo_aeronave(cur, "B738")
        aeronave_id = _obtener_o_crear_aeronave(cur, "HC-DEV1", modelo_aeronave_id, aerolinea_id)
        _obtener_o_crear_aeronave(cur, "HC-DEV2", modelo_aeronave_id, aerolinea_id)
        cur.execute("SELECT id FROM catalogo.tipo_vuelo WHERE codigo = 'comercial'")
        tipo_vuelo_id = cur.fetchone()[0]

        # Primera pasada: tenant + usuario + aeropuerto por spec (necesita
        # existir ANTES de poder emparejar origen/destino entre tenants).
        info_tenants: dict[str, dict[str, int]] = {}
        for spec in TENANTS_CANARIO:
            cur.execute(
                "SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = %s",
                (spec["codigo"],),
            )
            fila = cur.fetchone()
            if fila:
                tenant_id, aeropuerto_id = fila
                print(f"tenant {spec['codigo']} ya existe (id={tenant_id}), se reutiliza")
            else:
                aeropuerto_id = _obtener_o_crear_aeropuerto(cur, spec["aeropuerto_iata"], pais_id)
                tenant_id = generar_id()
                cur.execute(
                    "INSERT INTO tenants.tenant "
                    "(id, codigo, razon_social, aeropuerto_id, plan_id, estado) "
                    "VALUES (%s, %s, %s, %s, %s, 'activo')",
                    (tenant_id, spec["codigo"], spec["razon_social"], aeropuerto_id, plan_id),
                )
                print(f"tenant {spec['codigo']} creado (id={tenant_id})")
            info_tenants[spec["codigo"]] = {"tenant_id": tenant_id, "aeropuerto_id": aeropuerto_id}

            email_canario = f"canario@{spec['codigo'].lower()}.aerohub.test"
            cur.execute(
                "SELECT id FROM tenants.usuario WHERE tenant_id = %s AND email = %s",
                (tenant_id, email_canario),
            )
            if cur.fetchone():
                print(f"  usuario canario {email_canario} ya existe, se reutiliza")
            else:
                usuario_id = generar_id()
                cur.execute(
                    "INSERT INTO tenants.usuario "
                    "(id, tenant_id, email, hash_credencial, nombre, estado) "
                    "VALUES (%s, %s, %s, %s, %s, 'activo')",
                    (
                        usuario_id,
                        tenant_id,
                        email_canario,
                        hash_credencial("canario-dev-password"),
                        f"Usuario Canario {spec['codigo']}",
                    ),
                )
                print(f"  usuario canario {email_canario} creado (id={usuario_id})")

        # Segunda pasada: un vuelo canario por tenant, origen=su propio
        # aeropuerto, destino=el del OTRO tenant -- ambos ya existen tras
        # la primera pasada (tests/cross_tenant/ necesita un vuelo_id fijo
        # por tenant, igual que ya necesitaba un usuario_id fijo).
        codigos = list(info_tenants)
        for i, codigo in enumerate(codigos):
            otro = codigos[(i + 1) % len(codigos)]
            vuelo_id = _obtener_o_crear_vuelo_canario(
                cur,
                tenant_id=info_tenants[codigo]["tenant_id"],
                numero_vuelo=f"XX{100 + i}",
                aerolinea_id=aerolinea_id,
                aeronave_id=aeronave_id,
                tipo_vuelo_id=tipo_vuelo_id,
                aeropuerto_origen_id=info_tenants[codigo]["aeropuerto_id"],
                aeropuerto_destino_id=info_tenants[otro]["aeropuerto_id"],
            )
            print(f"  vuelo canario XX{100 + i} de {codigo} listo (id={vuelo_id})")

            estado_id = _obtener_o_crear_estado_vuelo_actual(
                cur,
                tenant_id=info_tenants[codigo]["tenant_id"],
                vuelo_id=vuelo_id,
                estado_id=estados_por_codigo["programado"],
            )
            print(f"  estado 'programado' de XX{100 + i} listo (id={estado_id})")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=50000)
    parser.add_argument("--database", default="aerohub")
    parser.add_argument("--username", default="monetdb")
    parser.add_argument("--password", default="aerohub")
    args = parser.parse_args()

    sembrar(
        hostname=args.host,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password,
    )


if __name__ == "__main__":
    main()
