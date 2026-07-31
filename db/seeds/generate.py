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


def sembrar(*, hostname: str, port: int, database: str, username: str, password: str) -> None:
    conn = pymonetdb.connect(
        hostname=hostname, port=port, database=database, username=username, password=password
    )
    try:
        cur = conn.cursor()
        pais_id = _obtener_o_crear_pais(cur, "EC", "ECU", "Ecuador")
        plan_id = _obtener_o_crear_plan(cur, "PLAN-CANARIO")

        for spec in TENANTS_CANARIO:
            cur.execute("SELECT id FROM tenants.tenant WHERE codigo = %s", (spec["codigo"],))
            fila = cur.fetchone()
            if fila:
                tenant_id = fila[0]
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

            email_canario = f"canario@{spec['codigo'].lower()}.aerohub.test"
            cur.execute(
                "SELECT id FROM tenants.usuario WHERE tenant_id = %s AND email = %s",
                (tenant_id, email_canario),
            )
            if cur.fetchone():
                print(f"  usuario canario {email_canario} ya existe, se reutiliza")
                continue
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
