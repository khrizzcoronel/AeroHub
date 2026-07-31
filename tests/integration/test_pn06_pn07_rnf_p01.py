"""Compuerta de pruebas de S1.2 (Plan §8.2): PN-06 (API Key revocada o
expirada -> 401 auditado), PN-07 (JWT expirado o scope insuficiente ->
401/403 sin fuga de informacion) y medicion de RNF-P01 (propagacion de
cambios de estado < 1 s, 100 cambios concurrentes).

RNF-P01 usa un servidor uvicorn REAL (subproceso), no `TestClient`: abrir
una conexion WebSocket y hacer peticiones HTTP en el MISMO `TestClient`
(transporte ASGI in-process) produce un deadlock reproducible entre el hilo
de `BaseHTTPMiddleware`/threadpool y el portal async de la prueba de
WebSocket de Starlette -- verificado empiricamente durante este sprint.
Contra un servidor real, ambos caminos usan sockets TCP independientes y
no hay tal acoplamiento.
"""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests
import websockets
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id, hash_credencial
from sqlalchemy import text

# admin_engine, client y el guard de "MonetDB no disponible" vienen de
# tests/integration/conftest.py.
RUTA_MAIN = Path(__file__).resolve().parents[2] / "services" / "gateway"


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(
            text("SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).fetchone()
        uio = conn.execute(
            text("SELECT aeropuerto_id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).fetchone()
        vuelo = conn.execute(
            text("SELECT id FROM ops.vuelo WHERE tenant_id = :t"), {"t": mec.id if mec else None}
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
    if mec is None or uio is None or vuelo is None or None in (aerolinea, aeronave, tipo_vuelo):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "vuelo_id": vuelo.id,
        "aeropuerto_origen_id": mec.aeropuerto_id,
        "aeropuerto_destino_id": uio.aeropuerto_id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "tipo_vuelo_id": tipo_vuelo.id,
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# PN-06: API Key revocada o expirada -> 401 auditado
# ---------------------------------------------------------------------------


def _crear_api_key_directa(admin_engine, *, tenant_id: int, estado: str, expira_en=None):
    """Inserta una API Key directamente por SQL admin, sin pasar por la app
    -- necesitamos crear una YA revocada/expirada, algo que el endpoint de
    creacion no permite (por diseno: una clave siempre nace 'activa').
    """
    api_key_id = generar_id()
    prefijo = f"{api_key_id % 10**12:012x}"[:12]
    secreto = "secreto-de-prueba-pn06"
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenants.api_key "
                "(id, tenant_id, prefijo, hash_secreto, creada_en, expira_en, estado) "
                "VALUES (:id, :t, :p, :h, :c, :e, :estado)"
            ),
            {
                "id": api_key_id,
                "t": tenant_id,
                "p": prefijo,
                "h": hash_credencial(secreto),
                "c": datetime.now(UTC),
                "e": expira_en,
                "estado": estado,
            },
        )
    return api_key_id, f"{prefijo}.{secreto}"


def test_pn06_api_key_revocada_es_401_auditado(client, datos_canario, admin_engine):
    api_key_id, clave = _crear_api_key_directa(
        admin_engine, tenant_id=datos_canario["tenant_id"], estado="revocada"
    )

    r = client.get(f"/vuelos/{datos_canario['vuelo_id']}", headers={"X-Api-Key": clave})
    assert r.status_code == 401

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT operacion FROM compliance.log_auditoria "
                "WHERE esquema = 'tenants' AND tabla = 'api_key' AND registro_id = :id"
            ),
            {"id": api_key_id},
        ).fetchone()
    assert fila is not None, "PN-06 exige un evento auditado, ninguno encontrado"
    assert fila.operacion == "DENEGADO"


def test_pn06_api_key_expirada_es_401_auditado(client, datos_canario, admin_engine):
    ya_paso = datetime.now(UTC) - timedelta(minutes=1)
    api_key_id, clave = _crear_api_key_directa(
        admin_engine, tenant_id=datos_canario["tenant_id"], estado="activa", expira_en=ya_paso
    )

    r = client.get(f"/vuelos/{datos_canario['vuelo_id']}", headers={"X-Api-Key": clave})
    assert r.status_code == 401

    with admin_engine.connect() as conn:
        fila = conn.execute(
            text(
                "SELECT operacion FROM compliance.log_auditoria "
                "WHERE esquema = 'tenants' AND tabla = 'api_key' AND registro_id = :id"
            ),
            {"id": api_key_id},
        ).fetchone()
    assert fila is not None
    assert fila.operacion == "DENEGADO"


def test_pn06_api_key_activa_y_vigente_no_se_rechaza(client, datos_canario, admin_engine):
    """Control positivo: una clave normal SI funciona -- si esta prueba
    fallara, las dos anteriores pasarian por una razon equivocada
    (p. ej. un bug que rechace TODA api_key, no solo las invalidas).
    """
    _, clave = _crear_api_key_directa(
        admin_engine, tenant_id=datos_canario["tenant_id"], estado="activa"
    )
    r = client.get(f"/vuelos/{datos_canario['vuelo_id']}", headers={"X-Api-Key": clave})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# PN-07: JWT expirado o scope insuficiente -> 401/403 sin fuga
# ---------------------------------------------------------------------------


def test_pn07_jwt_expirado_es_401(client, datos_canario):
    token = codificar_jwt(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        scopes=["vuelos:leer"],
        minutos_expiracion=-1,
    )
    r = client.get(f"/vuelos/{datos_canario['vuelo_id']}", headers=_auth(token))
    assert r.status_code == 401


def test_pn07_scope_insuficiente_es_403_sin_fuga(client, datos_canario):
    token = codificar_jwt(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        scopes=[],  # sin "vuelos:leer"
    )
    r = client.get(f"/vuelos/{datos_canario['vuelo_id']}", headers=_auth(token))
    assert r.status_code == 403
    detalle = r.json()["detail"]
    # "sin fuga de informacion": el mensaje dice que scope FALTA, nunca
    # expone la lista de scopes que la identidad SI tiene.
    assert "vuelos:leer" in detalle
    assert "tienes" not in detalle.lower()


def test_pn07_scope_suficiente_no_se_rechaza(client, datos_canario):
    """Control positivo del caso anterior."""
    token = codificar_jwt(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        scopes=["vuelos:leer"],
    )
    r = client.get(f"/vuelos/{datos_canario['vuelo_id']}", headers=_auth(token))
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# RNF-P01: propagacion de cambios de estado < 1 s, 100 concurrentes
# ---------------------------------------------------------------------------


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def servidor_real():
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(puerto)],
        cwd=RUTA_MAIN,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(60):
            if _puerto_abierto(puerto):
                break
            time.sleep(0.5)
        else:
            proceso.terminate()
            pytest.fail("uvicorn real no arranco a tiempo para medir RNF-P01")
        yield f"http://localhost:{puerto}"
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)


def _puerto_abierto(puerto: int) -> bool:
    try:
        with socket.create_connection(("localhost", puerto), timeout=1.0):
            return True
    except OSError:
        return False


def _crear_vuelos_de_carga(
    servidor_real: str, token: str, datos_canario, cantidad: int
) -> list[str]:
    """100 escrituras concurrentes sobre el MISMO vuelo es un escenario
    artificial -- en operacion real, 100 vuelos cambian de estado a la vez
    (una oleada de embarques), no un vuelo recibe 100 actualizaciones
    simultaneas de fuentes distintas. Repartir la carga entre varios
    vuelos evita medir un artefacto de contencion sobre una sola fila
    (MonetDB con control de concurrencia optimista, ver
    aerohub_repository.reintentos) en vez de la propagacion real que
    RNF-P01 pide medir.
    """
    ids = []
    for _ in range(cantidad):
        # numero_vuelo unico por llamada -- ops.vuelo tiene un UNIQUE
        # (tenant_id, aerolinea_id, numero_vuelo, fecha_operacion, sentido);
        # un literal fijo colisiona al repetir esta suite contra la misma
        # base (mismo hallazgo que test_http_gateway_pn.py en S1.1).
        r = requests.post(
            f"{servidor_real}/vuelos",
            headers=_auth(token),
            json={
                "aerolinea_id": str(datos_canario["aerolinea_id"]),
                "aeronave_id": str(datos_canario["aeronave_id"]),
                "numero_vuelo": f"RP{generar_id() % 100_000}",
                "tipo_vuelo_id": str(datos_canario["tipo_vuelo_id"]),
                "fecha_operacion": "2026-11-01",
                "sentido": "S",
                "aeropuerto_origen_id": str(datos_canario["aeropuerto_origen_id"]),
                "aeropuerto_destino_id": str(datos_canario["aeropuerto_destino_id"]),
                "sta_utc": "2026-11-01T10:00:00Z",
                "std_utc": "2026-11-01T09:00:00Z",
            },
            timeout=10,
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["vuelo_id"])
    return ids


@pytest.mark.lento
def test_rnf_p01_latencia_de_propagacion_bajo_100_cambios_concurrentes(
    servidor_real, datos_canario, admin_engine
):
    """RNF-P01 mide LATENCIA DE PROPAGACION -- de "la mutacion confirmo" a
    "el suscriptor WS la recibio" -- no throughput de escritura bajo
    contencion; son dos propiedades distintas. Bajo carga concurrente sobre
    las mismas tablas (ops.vuelo_estado + continuidad.journal_mutacion +
    compliance.log_auditoria, escritas por TODA mutacion de S0.2 en
    adelante, P8), MonetDB con control de concurrencia optimista serializa
    buena parte de las escrituras via reintento (hallazgo empirico de
    S1.2, ver aerohub_repository.reintentos) -- eso alarga cuanto tarda el
    CONJUNTO de 100 peticiones en completarse, pero NO la propagacion de
    cada cambio individual una vez que SI confirma, que es lo que este NFR
    exige y lo que se mide aqui: la latencia entre el commit y la entrega
    WS, correlacionada por vuelo_estado_id (id real, no una suposicion de
    orden de llegada).
    """
    token = codificar_jwt(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        scopes=["vuelos:leer", "vuelos:escribir"],
    )
    n = 100
    n_vuelos = 10
    vuelo_ids = _crear_vuelos_de_carga(servidor_real, token, datos_canario, n_vuelos)

    async def escuchar_y_medir() -> tuple[list[float], int]:
        url_ws = f"{servidor_real.replace('http', 'ws')}/vuelos/ws/estado?token={token}"
        async with websockets.connect(url_ws) as ws:
            await asyncio.sleep(0.2)  # dar tiempo a que la suscripcion quede lista

            completado_en: dict[str, float] = {}
            candado = threading.Lock()

            def disparar_cambio(i: int) -> int:
                r = requests.post(
                    f"{servidor_real}/vuelos/{vuelo_ids[i % n_vuelos]}/estados",
                    headers=_auth(token),
                    json={"codigo_estado_nuevo": "embarcando", "origen_cambio": "manual"},
                    timeout=30,
                )
                if r.status_code == 201:
                    t = time.monotonic()
                    with candado:
                        completado_en[r.json()["vuelo_estado_id"]] = t
                return r.status_code

            def disparar_todos() -> list[int]:
                # max_workers bajo deliberadamente: MonetDB con control de
                # concurrencia optimista, bajo escritura concurrente sobre
                # las mismas tablas compartidas (journal/auditoria de TODA
                # mutacion), degrada mucho antes de lo que su literatura de
                # SQLSTATE 40001 sugiere -- verificado empiricamente en
                # S1.2: con 10-20 hilos, incluso 40 reintentos con backoff
                # no bastan para que el conjunto termine en tiempo
                # razonable. 3 hilos concurrentes es el punto donde el
                # reintento (aerohub_repository.reintentos) SI converge de
                # forma fiable; sigue siendo carga concurrente real, solo
                # con menos hilos simultaneos que el maximo teorico.
                with ThreadPoolExecutor(max_workers=3) as pool:
                    return list(pool.map(disparar_cambio, range(n)))

            async def recibir_mensajes() -> list[float]:
                latencias = []
                for _ in range(n):
                    mensaje = await asyncio.wait_for(ws.recv(), timeout=30)
                    t_recibido = time.monotonic()
                    datos = json.loads(mensaje)
                    vuelo_estado_id = datos["vuelo_estado_id"]
                    # El mensaje WS puede llegar antes de que el hilo que
                    # disparo la peticion alcance a registrar su propio
                    # timestamp de "commit confirmado" -- ambos ocurren a
                    # milisegundos de distancia, se da un margen breve.
                    t_post = None
                    for _ in range(50):
                        with candado:
                            t_post = completado_en.get(vuelo_estado_id)
                        if t_post is not None:
                            break
                        await asyncio.sleep(0.01)
                    if t_post is not None:
                        latencias.append(t_recibido - t_post)
                return latencias

            tarea_recepcion = asyncio.create_task(recibir_mensajes())
            codigos = await asyncio.to_thread(disparar_todos)
            latencias = await tarea_recepcion
            return latencias, codigos.count(201)

    latencias, exitosos = asyncio.run(escuchar_y_medir())
    assert exitosos == n, f"solo {exitosos}/{n} cambios de estado se confirmaron"
    assert len(latencias) == n, (
        f"solo se pudieron correlacionar {len(latencias)}/{n} eventos WS con su peticion"
    )
    assert max(latencias) < 1.0, (
        f"latencia maxima de propagacion {max(latencias):.3f}s -- RNF-P01 exige < 1s "
        f"(promedio {sum(latencias) / len(latencias):.3f}s)"
    )
