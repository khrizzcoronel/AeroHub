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
import json
import secrets
from datetime import UTC, date, datetime, timedelta

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

# Catalogo de categorias de ticket de soporte (D6, Sprint S1.8) -- un
# codigo por modulo/categoria de ejemplo (spec.md, Escenario 1 de
# quickstart.md usa "AODB").
CATEGORIAS_TICKET = [
    ("AODB", "Seguimiento de vuelos (AODB)"),
    ("FIDS", "Pantallas y plantillas FIDS"),
    ("GATES", "Asignacion de puertas"),
    ("RAMPA", "Operaciones de rampa (turnaround)"),
    ("BILLING", "Facturacion y conciliacion"),
    ("CUENTA", "Gestion de cuenta y acceso"),
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


def _obtener_o_crear_categoria_ticket(cur, codigo: str, nombre: str) -> int:
    cur.execute("SELECT id FROM support.categoria_ticket WHERE codigo = %s", (codigo,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO support.categoria_ticket (id, codigo, nombre) VALUES (%s, %s, %s)",
        (id_, codigo, nombre),
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
    sentido: str = "S",
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
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            aerolinea_id,
            aeronave_id,
            numero_vuelo,
            tipo_vuelo_id,
            date(2026, 8, 1),
            sentido,
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


# ---------------------------------------------------------------------------
# Fase 2 de docs/diseno/PLAN_CORRECCION_MODULOS.md (2026-08-07): datos
# operativos minimos para que ningun modulo de la capa operativa se abra
# vacio -- terminales/puertas, FIDS, turnaround con tareas/incidencias,
# tarifario con conceptos y facturas en varios estados, KB y changelog.
# Mismo criterio "obtener o crear" que el resto del archivo: idempotente,
# nunca duplica en una segunda corrida.
# ---------------------------------------------------------------------------


def _obtener_o_crear_terminal(cur, *, tenant_id: int, codigo: str, nombre: str) -> int:
    cur.execute(
        "SELECT id FROM ops.terminal WHERE tenant_id = %s AND codigo = %s", (tenant_id, codigo)
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO ops.terminal (id, tenant_id, codigo, nombre) VALUES (%s, %s, %s, %s)",
        (id_, tenant_id, codigo, nombre),
    )
    return id_


def _obtener_o_crear_puerta(
    cur, *, tenant_id: int, terminal_id: int, codigo: str, tipo: str, envergadura_max_m: float
) -> int:
    cur.execute(
        "SELECT id FROM ops.puerta WHERE tenant_id = %s AND codigo = %s", (tenant_id, codigo)
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO ops.puerta "
        "(id, tenant_id, terminal_id, codigo, tipo, envergadura_max_m, tiene_pasarela) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (id_, tenant_id, terminal_id, codigo, tipo, envergadura_max_m, tipo == "contacto"),
    )
    return id_


def _obtener_o_crear_plantilla_fids(
    cur, *, tenant_id: int, nombre: str, filas_texto: list[str], creada_por_usuario_id: int
) -> int:
    version = 1
    cur.execute(
        "SELECT id FROM ops.plantilla_fids WHERE tenant_id = %s AND nombre = %s AND version = %s",
        (tenant_id, nombre, version),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    # Convencion "filas: [{texto}]" (S1.14, apps/fids-player/.../pantalla-player.ts)
    # -- domain deja definicion_json libre, esta es la forma que el player sabe
    # interpretar sin caer al respaldo de JSON crudo.
    definicion = {"filas": [{"texto": t} for t in filas_texto]}
    cur.execute(
        "INSERT INTO ops.plantilla_fids "
        "(id, tenant_id, nombre, definicion_json, version, vigente_desde, creada_por_usuario_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            nombre,
            json.dumps(definicion),
            version,
            datetime(2026, 1, 1, tzinfo=UTC),
            creada_por_usuario_id,
        ),
    )
    return id_


def _obtener_o_crear_pantalla_fids(
    cur,
    *,
    tenant_id: int,
    terminal_id: int,
    codigo: str,
    plantilla_id: int,
    estado: str,
    ubicacion_descripcion: str,
) -> int:
    cur.execute(
        "SELECT id FROM ops.pantalla_fids WHERE tenant_id = %s AND codigo = %s",
        (tenant_id, codigo),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    ultima_senal = datetime.now(UTC) if estado == "en_linea" else None
    cur.execute(
        "INSERT INTO ops.pantalla_fids "
        "(id, tenant_id, terminal_id, codigo, ubicacion_descripcion, plantilla_id, "
        "ultima_senal_en, version_firmware, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            terminal_id,
            codigo,
            ubicacion_descripcion,
            plantilla_id,
            ultima_senal,
            "1.0.0",
            estado,
        ),
    )
    return id_


def _obtener_o_crear_turnaround(
    cur,
    *,
    tenant_id: int,
    vuelo_llegada_id: int,
    vuelo_salida_id: int,
    aeronave_id: int,
    inicio_previsto: datetime,
    fin_previsto: datetime,
    estado: str,
) -> int:
    cur.execute(
        "SELECT id FROM rampa.turnaround "
        "WHERE tenant_id = %s AND vuelo_llegada_id = %s AND vuelo_salida_id = %s",
        (tenant_id, vuelo_llegada_id, vuelo_salida_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    inicio_real = inicio_previsto if estado in ("en_curso", "completado") else None
    fin_real = fin_previsto if estado == "completado" else None
    cur.execute(
        "INSERT INTO rampa.turnaround "
        "(id, tenant_id, vuelo_llegada_id, vuelo_salida_id, aeronave_id, inicio_previsto, "
        "fin_previsto, inicio_real, fin_real, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            vuelo_llegada_id,
            vuelo_salida_id,
            aeronave_id,
            inicio_previsto,
            fin_previsto,
            inicio_real,
            fin_real,
            estado,
        ),
    )
    return id_


def _obtener_o_crear_tarea_turnaround(
    cur,
    *,
    tenant_id: int,
    turnaround_id: int,
    tipo_tarea_id: int,
    agente_usuario_id: int,
    estado: str,
) -> int:
    cur.execute(
        "SELECT id FROM rampa.tarea_turnaround WHERE turnaround_id = %s AND tipo_tarea_id = %s",
        (turnaround_id, tipo_tarea_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    ahora = datetime.now(UTC)
    inicio_real = ahora - timedelta(minutes=40) if estado in ("en_curso", "completada") else None
    fin_real = ahora - timedelta(minutes=10) if estado == "completada" else None
    cur.execute(
        "INSERT INTO rampa.tarea_turnaround "
        "(id, tenant_id, turnaround_id, tipo_tarea_id, agente_usuario_id, inicio_real, "
        "fin_real, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            turnaround_id,
            tipo_tarea_id,
            agente_usuario_id,
            inicio_real,
            fin_real,
            estado,
        ),
    )
    return id_


def _obtener_o_crear_incidencia_rampa(
    cur,
    *,
    tenant_id: int,
    tarea_turnaround_id: int,
    tipo_incidencia_id: int,
    descripcion: str,
    severidad: str,
) -> int:
    cur.execute(
        "SELECT id FROM rampa.incidencia_rampa "
        "WHERE tarea_turnaround_id = %s AND tipo_incidencia_id = %s",
        (tarea_turnaround_id, tipo_incidencia_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO rampa.incidencia_rampa "
        "(id, tenant_id, tarea_turnaround_id, tipo_incidencia_id, descripcion, severidad) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (id_, tenant_id, tarea_turnaround_id, tipo_incidencia_id, descripcion, severidad),
    )
    return id_


def _obtener_o_crear_tarifario(
    cur,
    *,
    tenant_id: int,
    nombre: str,
    moneda: str,
    vigente_desde: date,
    estado: str,
    creado_por_usuario_id: int,
) -> int:
    cur.execute(
        "SELECT id FROM billing.tarifario WHERE tenant_id = %s AND nombre = %s",
        (tenant_id, nombre),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO billing.tarifario "
        "(id, tenant_id, nombre, moneda, vigente_desde, estado, creado_por_usuario_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (id_, tenant_id, nombre, moneda, vigente_desde, estado, creado_por_usuario_id),
    )
    return id_


def _obtener_o_crear_tarifario_concepto(
    cur, *, tarifario_id: int, concepto_cargo_id: int, tarifa_unitaria: float
) -> int:
    cur.execute(
        "SELECT id FROM billing.tarifario_concepto "
        "WHERE tarifario_id = %s AND concepto_cargo_id = %s",
        (tarifario_id, concepto_cargo_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO billing.tarifario_concepto "
        "(id, tarifario_id, concepto_cargo_id, tarifa_unitaria) VALUES (%s, %s, %s, %s)",
        (id_, tarifario_id, concepto_cargo_id, tarifa_unitaria),
    )
    return id_


def _obtener_o_crear_cargo_aeronautico(
    cur,
    *,
    tenant_id: int,
    vuelo_id: int,
    concepto_cargo_id: int,
    tarifario_concepto_id: int,
    cantidad: float,
    tarifa_aplicada: float,
    monto_calculado: float,
) -> int:
    cur.execute(
        "SELECT id FROM billing.cargo_aeronautico "
        "WHERE tenant_id = %s AND vuelo_id = %s AND concepto_cargo_id = %s",
        (tenant_id, vuelo_id, concepto_cargo_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO billing.cargo_aeronautico "
        "(id, tenant_id, vuelo_id, concepto_cargo_id, tarifario_concepto_id, cantidad, "
        "tarifa_aplicada, monto_calculado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            vuelo_id,
            concepto_cargo_id,
            tarifario_concepto_id,
            cantidad,
            tarifa_aplicada,
            monto_calculado,
        ),
    )
    return id_


def _obtener_o_crear_factura(
    cur,
    *,
    tenant_id: int,
    aerolinea_id: int,
    periodo_inicio: date,
    periodo_fin: date,
    moneda: str,
    estado: str,
) -> int:
    cur.execute(
        "SELECT id FROM billing.factura "
        "WHERE tenant_id = %s AND aerolinea_id = %s AND periodo_inicio = %s AND periodo_fin = %s",
        (tenant_id, aerolinea_id, periodo_inicio, periodo_fin),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    emitida_en = datetime.now(UTC) if estado != "borrador" else None
    vence_en = datetime.now(UTC) + timedelta(days=30) if estado != "borrador" else None
    cur.execute(
        "INSERT INTO billing.factura "
        "(id, tenant_id, aerolinea_id, periodo_inicio, periodo_fin, moneda, estado, "
        "emitida_en, vence_en) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_,
            tenant_id,
            aerolinea_id,
            periodo_inicio,
            periodo_fin,
            moneda,
            estado,
            emitida_en,
            vence_en,
        ),
    )
    return id_


def _obtener_o_crear_factura_linea(
    cur,
    *,
    factura_id: int,
    cargo_aeronautico_id: int,
    descripcion: str,
    cantidad: float,
    precio_unitario: float,
    monto: float,
) -> int:
    cur.execute(
        "SELECT id FROM billing.factura_linea WHERE factura_id = %s AND cargo_aeronautico_id = %s",
        (factura_id, cargo_aeronautico_id),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO billing.factura_linea "
        "(id, factura_id, cargo_aeronautico_id, descripcion, cantidad, precio_unitario, monto) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (id_, factura_id, cargo_aeronautico_id, descripcion, cantidad, precio_unitario, monto),
    )
    return id_


def _obtener_o_crear_etiqueta(cur, nombre: str) -> int:
    cur.execute("SELECT id FROM support.etiqueta WHERE nombre = %s", (nombre,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute("INSERT INTO support.etiqueta (id, nombre) VALUES (%s, %s)", (id_, nombre))
    return id_


def _obtener_o_crear_articulo_kb(
    cur, *, titulo: str, cuerpo: str, autor_usuario_id: int, etiquetas: list[str]
) -> int:
    """Global (sin tenant_id) -- se siembra UNA vez, no por tenant."""
    version = 1
    cur.execute(
        "SELECT id FROM support.articulo_kb WHERE titulo = %s AND version = %s", (titulo, version)
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO support.articulo_kb "
        "(id, titulo, cuerpo, version, estado, publicado_en, autor_usuario_id) "
        "VALUES (%s, %s, %s, %s, 'publicado', %s, %s)",
        (id_, titulo, cuerpo, version, datetime.now(UTC), autor_usuario_id),
    )
    for nombre_etiqueta in etiquetas:
        etiqueta_id = _obtener_o_crear_etiqueta(cur, nombre_etiqueta)
        cur.execute(
            "SELECT 1 FROM support.articulo_kb_etiqueta "
            "WHERE articulo_id = %s AND etiqueta_id = %s",
            (id_, etiqueta_id),
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO support.articulo_kb_etiqueta (articulo_id, etiqueta_id) "
                "VALUES (%s, %s)",
                (id_, etiqueta_id),
            )
    return id_


def _obtener_o_crear_changelog(
    cur, *, version_producto: str, resumen: str, items: list[tuple[str, str, str]]
) -> int:
    """Global (sin tenant_id) -- se siembra UNA vez. `items`: lista de
    (modulo_codigo, tipo_cambio, descripcion)."""
    cur.execute("SELECT id FROM support.changelog WHERE version_producto = %s", (version_producto,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    id_ = generar_id()
    cur.execute(
        "INSERT INTO support.changelog (id, version_producto, resumen) VALUES (%s, %s, %s)",
        (id_, version_producto, resumen),
    )
    for modulo_codigo, tipo_cambio, descripcion in items:
        cur.execute("SELECT id FROM catalogo.modulo WHERE codigo = %s", (modulo_codigo,))
        modulo_id = cur.fetchone()[0]
        item_id = generar_id()
        cur.execute(
            "INSERT INTO support.changelog_item "
            "(id, changelog_id, modulo_id, tipo_cambio, descripcion) VALUES (%s, %s, %s, %s, %s)",
            (item_id, id_, modulo_id, tipo_cambio, descripcion),
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

        tipos_tarea_por_codigo: dict[str, int] = {}
        for codigo, nombre, duracion_estandar_min, es_ruta_critica in TIPOS_TAREA:
            tipos_tarea_por_codigo[codigo] = _obtener_o_crear_tipo_tarea(
                cur, codigo, nombre, duracion_estandar_min, es_ruta_critica
            )
        tipos_incidencia_por_codigo: dict[str, int] = {}
        for codigo, descripcion in TIPOS_INCIDENCIA_RAMPA:
            tipos_incidencia_por_codigo[codigo] = _obtener_o_crear_tipo_incidencia_rampa(
                cur, codigo, descripcion
            )
        conceptos_cargo_por_codigo: dict[str, int] = {}
        for codigo, nombre, unidad_medida, base_calculo in CONCEPTOS_CARGO:
            conceptos_cargo_por_codigo[codigo] = _obtener_o_crear_concepto_cargo(
                cur, codigo, nombre, unidad_medida, base_calculo
            )
        for codigo, descripcion, categoria in TIPOS_INCIDENTE:
            _obtener_o_crear_tipo_incidente(cur, codigo, descripcion, categoria)
        for codigo, nombre, periodicidad, autoridad in TIPOS_REPORTE_REGULATORIO:
            _obtener_o_crear_tipo_reporte_regulatorio(cur, codigo, nombre, periodicidad, autoridad)
        for codigo_control, nombre, categoria in CONTROLES_SOC2:
            _obtener_o_crear_control_soc2(cur, codigo_control, nombre, categoria)
        for codigo, nombre in CATEGORIAS_TICKET:
            _obtener_o_crear_categoria_ticket(cur, codigo, nombre)

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
            for modulo_codigo in MODULOS_LICENCIABLES:
                _obtener_o_crear_licencia(cur, tenant_id=tenant_id, modulo_codigo=modulo_codigo)

            email_canario = f"canario@{spec['codigo'].lower()}.aerohub.test"
            cur.execute(
                "SELECT id FROM tenants.usuario WHERE tenant_id = %s AND email = %s",
                (tenant_id, email_canario),
            )
            fila_usuario = cur.fetchone()
            if fila_usuario:
                usuario_id = fila_usuario[0]
                print(f"  usuario canario {email_canario} ya existe, se reutiliza")
            else:
                usuario_id = generar_id()
                cur.execute(
                    "INSERT INTO tenants.usuario "
                    "(id, tenant_id, email, hash_credencial, nombre, estado, "
                    "debe_cambiar_password, email_verificado_en) "
                    "VALUES (%s, %s, %s, %s, %s, 'activo', FALSE, NOW())",
                    (
                        usuario_id,
                        tenant_id,
                        email_canario,
                        hash_credencial("canario-dev-password"),
                        f"Usuario Canario {spec['codigo']}",
                    ),
                )
                # S1.10: sin un rol vigente el canario no puede loguearse
                # (iniciar_sesion.py exige uno) -- suite de integracion y
                # cross_tenant necesitan poder loguearse con este usuario.
                cur.execute("SELECT id FROM tenants.rol WHERE codigo = 'role_tenant_admin'")
                rol_admin_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO tenants.usuario_rol "
                    "(usuario_id, rol_id, otorgado_por, otorgado_en) "
                    "VALUES (%s, %s, %s, NOW())",
                    (usuario_id, rol_admin_id, usuario_id),
                )
                print(f"  usuario canario {email_canario} creado (id={usuario_id})")

            info_tenants[spec["codigo"]] = {
                "tenant_id": tenant_id,
                "aeropuerto_id": aeropuerto_id,
                "usuario_id": usuario_id,
            }

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

            # --- Fase 2 de docs/diseno/PLAN_CORRECCION_MODULOS.md: datos
            # operativos por tenant para que ningun modulo se abra vacio.
            t_id = info_tenants[codigo]["tenant_id"]
            u_id = info_tenants[codigo]["usuario_id"]

            terminal_id = _obtener_o_crear_terminal(
                cur, tenant_id=t_id, codigo="T1", nombre="Terminal 1"
            )
            _obtener_o_crear_puerta(
                cur, tenant_id=t_id, terminal_id=terminal_id, codigo="A1",
                tipo="contacto", envergadura_max_m=36.0,
            )
            _obtener_o_crear_puerta(
                cur, tenant_id=t_id, terminal_id=terminal_id, codigo="A2",
                tipo="contacto", envergadura_max_m=36.0,
            )
            _obtener_o_crear_puerta(
                cur, tenant_id=t_id, terminal_id=terminal_id, codigo="R1",
                tipo="remota", envergadura_max_m=45.0,
            )

            plantilla_id = _obtener_o_crear_plantilla_fids(
                cur, tenant_id=t_id, nombre="Salidas estandar",
                filas_texto=[f"Vuelo XX{100 + i} -- Embarcando", "Bienvenido a AeroHub"],
                creada_por_usuario_id=u_id,
            )
            _obtener_o_crear_pantalla_fids(
                cur, tenant_id=t_id, terminal_id=terminal_id, codigo=f"{codigo}-FIDS-01",
                plantilla_id=plantilla_id, estado="en_linea",
                ubicacion_descripcion="Sala de embarque A",
            )
            _obtener_o_crear_pantalla_fids(
                cur, tenant_id=t_id, terminal_id=terminal_id, codigo=f"{codigo}-FIDS-02",
                plantilla_id=plantilla_id, estado="sin_senal",
                ubicacion_descripcion="Vestibulo principal",
            )

            # Segundo vuelo (sentido 'L', llegada) del mismo tenant, para
            # emparejarlo con el ya existente (sentido 'S', salida) en un
            # turnaround real.
            vuelo_llegada_id = _obtener_o_crear_vuelo_canario(
                cur,
                tenant_id=t_id,
                numero_vuelo=f"XX{200 + i}",
                aerolinea_id=aerolinea_id,
                aeronave_id=aeronave_id,
                tipo_vuelo_id=tipo_vuelo_id,
                aeropuerto_origen_id=info_tenants[otro]["aeropuerto_id"],
                aeropuerto_destino_id=info_tenants[codigo]["aeropuerto_id"],
                sentido="L",
            )
            ahora = datetime.now(UTC)
            turnaround_id = _obtener_o_crear_turnaround(
                cur, tenant_id=t_id, vuelo_llegada_id=vuelo_llegada_id,
                vuelo_salida_id=vuelo_id, aeronave_id=aeronave_id,
                inicio_previsto=ahora - timedelta(minutes=45),
                fin_previsto=ahora + timedelta(minutes=15), estado="en_curso",
            )
            tarea_completada_id = _obtener_o_crear_tarea_turnaround(
                cur, tenant_id=t_id, turnaround_id=turnaround_id,
                tipo_tarea_id=tipos_tarea_por_codigo["equipaje"], agente_usuario_id=u_id,
                estado="completada",
            )
            _obtener_o_crear_tarea_turnaround(
                cur, tenant_id=t_id, turnaround_id=turnaround_id,
                tipo_tarea_id=tipos_tarea_por_codigo["combustible"],
                agente_usuario_id=u_id, estado="en_curso",
            )
            _obtener_o_crear_incidencia_rampa(
                cur, tenant_id=t_id, tarea_turnaround_id=tarea_completada_id,
                tipo_incidencia_id=tipos_incidencia_por_codigo["desviacion_estandar"],
                descripcion="Carga y descarga de equipaje superó la duración estándar",
                severidad="baja",
            )

            tarifario_id = _obtener_o_crear_tarifario(
                cur, tenant_id=t_id, nombre="Tarifario general 2026",
                moneda="USD", vigente_desde=date(2026, 1, 1), estado="vigente",
                creado_por_usuario_id=u_id,
            )
            tarifario_conceptos_id: dict[str, int] = {}
            for concepto_codigo, tarifa in (
                ("tasa_aterrizaje", 120.0),
                ("uso_manga", 45.0),
                ("estacionamiento", 30.0),
            ):
                tarifario_conceptos_id[concepto_codigo] = _obtener_o_crear_tarifario_concepto(
                    cur, tarifario_id=tarifario_id,
                    concepto_cargo_id=conceptos_cargo_por_codigo[concepto_codigo],
                    tarifa_unitaria=tarifa,
                )

            cargo_id = _obtener_o_crear_cargo_aeronautico(
                cur, tenant_id=t_id, vuelo_id=vuelo_id,
                concepto_cargo_id=conceptos_cargo_por_codigo["tasa_aterrizaje"],
                tarifario_concepto_id=tarifario_conceptos_id["tasa_aterrizaje"],
                cantidad=1, tarifa_aplicada=120.0, monto_calculado=120.0,
            )

            for periodo_offset, estado_factura in ((2, "vencida"), (1, "emitida"), (0, "borrador")):
                periodo_inicio = date(2026, 6 - periodo_offset, 1)
                periodo_fin = date(2026, 6 - periodo_offset, 28)
                factura_id = _obtener_o_crear_factura(
                    cur, tenant_id=t_id, aerolinea_id=aerolinea_id,
                    periodo_inicio=periodo_inicio, periodo_fin=periodo_fin,
                    moneda="USD", estado=estado_factura,
                )
                if estado_factura == "vencida":
                    _obtener_o_crear_factura_linea(
                        cur, factura_id=factura_id, cargo_aeronautico_id=cargo_id,
                        descripcion="Tasa de aterrizaje", cantidad=1,
                        precio_unitario=120.0, monto=120.0,
                    )
            print(
                f"  datos operativos (terminal/FIDS/turnaround/tarifario/facturas) "
                f"de {codigo} listos"
            )

        autor_kb_id = info_tenants[codigos[0]]["usuario_id"]
        _obtener_o_crear_articulo_kb(
            cur, titulo="Como registrar un cambio de estado de vuelo",
            cuerpo=(
                "Desde el panel 'Vuelos en tiempo real', use el boton 'Cambiar "
                "estado' en la fila del vuelo. El nuevo estado se refleja para "
                "todos los usuarios conectados via WebSocket en menos de 1 "
                "segundo, sin necesidad de recargar la pantalla."
            ),
            autor_usuario_id=autor_kb_id,
            etiquetas=["vuelos", "operacion"],
        )
        _obtener_o_crear_articulo_kb(
            cur, titulo="Politica de conciliacion de pasajeros",
            cuerpo=(
                "Una conciliacion solo puede cerrarse cuando la diferencia entre "
                "el pax reportado por la aerolinea y el pax registrado en el "
                "sistema es exactamente cero. Si existe una diferencia, revise "
                "la fuente del reporte antes de reintentar."
            ),
            autor_usuario_id=autor_kb_id,
            etiquetas=["billing", "conciliacion"],
        )
        _obtener_o_crear_changelog(
            cur, version_producto="1.5.0",
            resumen="Cierre de la Fase 1.5: superficie completa de administracion",
            items=[
                ("M2", "nuevo", "Administracion de plantillas y pantallas FIDS desde la interfaz"),
                ("M5", "nuevo", "Tarifarios y conciliacion de pasajeros con historial completo"),
            ],
        )
        print("  articulos de KB y changelog globales listos")

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
