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
import secrets
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

# Catalogo de tareas de rampa (CU-O16, Sprint S1.5) -- dominio ABIERTO
# (rampa.tipo_tarea no tiene CHECK cerrado sobre codigo, a diferencia de
# catalogo.tipo_vuelo). combustible y equipaje se marcan de ruta critica:
# ambas bloquean el resto del turnaround si se retrasan (no puede salir el
# vuelo sin repostar ni sin cargar equipaje), a diferencia de catering o
# limpieza, que pueden solaparse con otras tareas sin extender el
# turnaround completo.
TIPOS_TAREA = [
    ("combustible", "Reabastecimiento de combustible", 30, True),
    ("catering", "Carga de catering", 20, False),
    ("limpieza", "Limpieza de cabina", 15, False),
    ("equipaje", "Carga y descarga de equipaje", 25, True),
]

TIPOS_INCIDENCIA_RAMPA = [
    ("desviacion_estandar", "Tarea de rampa que supero la duracion estandar de su tipo"),
]

# Catalogo global de conceptos facturables (M5, Sprint S1.6) -- estandar de
# industria, no configuracion por tenant (SDD-DATA-001 Sec9.1). base_calculo
# es informativo para este sprint: el motor de facturacion (CU-O17) usa
# tarifa_unitaria x cantidad, sin variar la formula por base_calculo todavia
# (fuera de alcance -- ver Assumptions de specs/008-.../spec.md).
CONCEPTOS_CARGO = [
    ("tasa_aterrizaje", "Tasa de aterrizaje", "ton", "peso_mtow"),
    ("uso_manga", "Uso de manga de embarque", "hora", "tiempo_estacionamiento"),
    ("estacionamiento", "Estacionamiento de aeronave", "hora", "tiempo_estacionamiento"),
    ("tasa_pasajero", "Tasa por pasajero embarcado", "pax", "pax"),
]

# Catalogos del Compliance Hub (Sprint S1.7). catalogo.modulo NO se
# siembra aqui -- ya viene poblado ('M1'..'M9') desde el propio DDL
# fundacional (01_catalogo.sql, INSERT de S0.1).
TIPOS_INCIDENTE = [
    ("acceso_no_autorizado", "Intento de acceso sin autorizacion valida", "seguridad_acceso"),
]

TIPOS_REPORTE_REGULATORIO = [
    ("informe_mensual_operaciones", "Informe mensual de operaciones", "mensual", "DGAC"),
]

CONTROLES_SOC2 = [
    ("CC6.1", "Controles de acceso logico", "seguridad"),
]


def _obtener_o_crear_tipo_tarea(
    cur, codigo: str, nombre: str, duracion_estandar_min: int, es_ruta_critica: bool
) -> int:
    cur.execute("SELECT id FROM rampa.tipo_tarea WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO rampa.tipo_tarea "
        "(id, codigo, nombre, duracion_estandar_min, es_ruta_critica) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_, codigo, nombre, duracion_estandar_min, es_ruta_critica),
    )
    return id_


def _obtener_o_crear_tipo_incidencia_rampa(cur, codigo: str, descripcion: str) -> int:
    cur.execute("SELECT id FROM rampa.tipo_incidencia_rampa WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO rampa.tipo_incidencia_rampa (id, codigo, descripcion) VALUES (%s, %s, %s)",
        (id_, codigo, descripcion),
    )
    return id_


def _obtener_o_crear_concepto_cargo(
    cur, codigo: str, nombre: str, unidad_medida: str, base_calculo: str
) -> int:
    cur.execute("SELECT id FROM billing.concepto_cargo WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO billing.concepto_cargo "
        "(id, codigo, nombre, unidad_medida, base_calculo) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_, codigo, nombre, unidad_medida, base_calculo),
    )
    return id_


def _obtener_o_crear_tipo_incidente(cur, codigo: str, descripcion: str, categoria: str) -> int:
    cur.execute("SELECT id FROM compliance.tipo_incidente WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO compliance.tipo_incidente (id, codigo, descripcion, categoria) "
        "VALUES (%s, %s, %s, %s)",
        (id_, codigo, descripcion, categoria),
    )
    return id_


def _obtener_o_crear_tipo_reporte_regulatorio(
    cur, codigo: str, nombre: str, periodicidad: str, autoridad: str
) -> int:
    cur.execute("SELECT id FROM compliance.tipo_reporte_regulatorio WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO compliance.tipo_reporte_regulatorio "
        "(id, codigo, nombre, periodicidad, autoridad) VALUES (%s, %s, %s, %s, %s)",
        (id_, codigo, nombre, periodicidad, autoridad),
    )
    return id_


def _obtener_o_crear_control_soc2(cur, codigo_control: str, nombre: str, categoria: str) -> int:
    cur.execute(
        "SELECT id FROM compliance.control_soc2 WHERE codigo_control = %s", (codigo_control,)
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO compliance.control_soc2 (id, codigo_control, nombre, categoria) "
        "VALUES (%s, %s, %s, %s)",
        (id_, codigo_control, nombre, categoria),
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


def _obtener_o_crear_api_key_canaria(cur, *, tenant_id: int) -> int:
    """El secreto en claro no importa para estos fines (G4 solo lee filas
    por id, nunca autentica con ella) -- se genera y se descarta.
    """
    cur.execute("SELECT id FROM tenants.api_key WHERE tenant_id = %s", (tenant_id,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    prefijo = secrets.token_hex(6)
    hash_secreto = hash_credencial(secrets.token_urlsafe(32))
    cur.execute(
        "INSERT INTO tenants.api_key "
        "(id, tenant_id, prefijo, hash_secreto, creada_en, estado) "
        "VALUES (%s, %s, %s, %s, %s, 'activa')",
        (id_, tenant_id, prefijo, hash_secreto, datetime.now(UTC)),
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


def _obtener_o_crear_licencia(cur, *, tenant_id: int, modulo_codigo: str) -> int:
    """RF-O18/CU-O20 (Sprint S1.7): licencia vigente e indefinida
    (`activa_hasta` NULL) para el modulo -- sin esto, el middleware de
    licenciamiento del Gateway rechazaria con 403 CUALQUIER endpoint de
    los tenants canario, rompiendo toda la suite de integracion de
    sprints anteriores (S1.1-S1.6) que no conocia el concepto de
    licencia. `catalogo.modulo` YA esta sembrado desde el DDL (M1..M9,
    01_catalogo.sql) -- solo se resuelve su id aqui."""
    cur.execute("SELECT id FROM catalogo.modulo WHERE codigo = %s", (modulo_codigo,))
    modulo_id = cur.fetchone()[0]
    cur.execute(
        "SELECT id FROM tenants.licencia WHERE tenant_id = %s AND modulo_id = %s",
        (tenant_id, modulo_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO tenants.licencia (id, tenant_id, modulo_id, activa_desde, activa_hasta) "
        "VALUES (%s, %s, %s, %s, NULL)",
        (id_, tenant_id, modulo_id, datetime(2020, 1, 1, tzinfo=UTC)),
    )
    return id_


# Modulos con endpoint HTTP licenciable en este sprint (research.md
# Decision 2 de specs/009-.../ ) -- M7-M9 no tienen ruta propia todavia.
MODULOS_LICENCIABLES = ("M1", "M2", "M3", "M4", "M5", "M6")


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

        for codigo, nombre, duracion_estandar_min, es_ruta_critica in TIPOS_TAREA:
            _obtener_o_crear_tipo_tarea(cur, codigo, nombre, duracion_estandar_min, es_ruta_critica)
        for codigo, descripcion in TIPOS_INCIDENCIA_RAMPA:
            _obtener_o_crear_tipo_incidencia_rampa(cur, codigo, descripcion)
        for codigo, nombre, unidad_medida, base_calculo in CONCEPTOS_CARGO:
            _obtener_o_crear_concepto_cargo(cur, codigo, nombre, unidad_medida, base_calculo)
        for codigo, descripcion, categoria in TIPOS_INCIDENTE:
            _obtener_o_crear_tipo_incidente(cur, codigo, descripcion, categoria)
        for codigo, nombre, periodicidad, autoridad in TIPOS_REPORTE_REGULATORIO:
            _obtener_o_crear_tipo_reporte_regulatorio(cur, codigo, nombre, periodicidad, autoridad)
        for codigo_control, nombre, categoria in CONTROLES_SOC2:
            _obtener_o_crear_control_soc2(cur, codigo_control, nombre, categoria)

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

            for modulo_codigo in MODULOS_LICENCIABLES:
                _obtener_o_crear_licencia(cur, tenant_id=tenant_id, modulo_codigo=modulo_codigo)

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

            api_key_id = _obtener_o_crear_api_key_canaria(
                cur, tenant_id=info_tenants[codigo]["tenant_id"]
            )
            print(f"  api_key canaria de {codigo} lista (id={api_key_id})")

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
