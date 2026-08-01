"""Compuerta de pruebas de S1.4 (Plan §8.4): PN-05 (asignacion de dos
vuelos solapados a la misma puerta) en variante SECUENCIAL y CONCURRENTE,
mas los controles de envergadura/no-solapamiento a nivel HTTP.

La variante concurrente usa un servidor uvicorn REAL (subproceso), no
`TestClient` -- mismo motivo que RNF-P01/RNF-P02: un WebSocket y peticiones
HTTP concurrentes reales sobre el MISMO `TestClient` (transporte ASGI
in-process) producen comportamiento distinto al de sockets TCP
independientes; para PN-05 concurrente en particular, lo que se quiere
medir es el conflicto de escritura REAL que produce MonetDB entre dos
conexiones de base de datos separadas (ver
aerohub_gates.infrastructure.comandos.bloquear_puerta_para_asignacion),
algo que dos hilos contra un TestClient in-process no reproducen de forma
fiable.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import requests
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id
from sqlalchemy import text

RUTA_MAIN = Path(__file__).resolve().parents[2] / "services" / "gateway"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(
            text("SELECT id, aeropuerto_id FROM tenants.tenant WHERE codigo = 'MEC'")
        ).fetchone()
        uio = conn.execute(
            text("SELECT aeropuerto_id FROM tenants.tenant WHERE codigo = 'UIO'")
        ).fetchone()
        usuario = None
        if mec is not None:
            usuario = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"), {"t": mec.id}
            ).fetchone()
        aerolinea = conn.execute(
            text("SELECT id FROM catalogo.aerolinea WHERE codigo_iata = 'XX'")
        ).fetchone()
        aeronave = conn.execute(
            text(
                "SELECT a.id, m.envergadura_m FROM catalogo.aeronave a "
                "JOIN catalogo.modelo_aeronave m ON m.id = a.modelo_aeronave_id "
                "WHERE a.matricula = 'HC-DEV1'"
            )
        ).fetchone()
        tipo_vuelo = conn.execute(
            text("SELECT id FROM catalogo.tipo_vuelo WHERE codigo = 'comercial'")
        ).fetchone()
    if mec is None or uio is None or usuario is None or None in (aerolinea, aeronave, tipo_vuelo):
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {
        "tenant_id": mec.id,
        "usuario_id": usuario.id,
        "aeropuerto_origen_id": mec.aeropuerto_id,
        "aeropuerto_destino_id": uio.aeropuerto_id,
        "aerolinea_id": aerolinea.id,
        "aeronave_id": aeronave.id,
        "envergadura_aeronave_m": aeronave.envergadura_m,
        "tipo_vuelo_id": tipo_vuelo.id,
    }


@pytest.fixture()
def terminal_canario(admin_engine, datos_canario):
    """No existe endpoint de creacion de terminal -- se obtiene o crea por
    SQL admin (mismo patron que tests/integration/test_fids_*)."""
    tenant_id = datos_canario["tenant_id"]
    with admin_engine.connect() as conn:
        fila = conn.execute(
            text("SELECT id FROM ops.terminal WHERE tenant_id = :t AND codigo = 'T1'"),
            {"t": tenant_id},
        ).fetchone()
    if fila is not None:
        return fila.id
    terminal_id = generar_id()
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ops.terminal (id, tenant_id, codigo, nombre) "
                "VALUES (:id, :t, 'T1', 'Terminal 1')"
            ),
            {"id": terminal_id, "t": tenant_id},
        )
    return terminal_id


@pytest.fixture()
def puerta_canaria(admin_engine, datos_canario, terminal_canario):
    """Puerta compatible con la aeronave canario (envergadura holgada) --
    tampoco existe endpoint de creacion de puerta (fuera de alcance de
    S1.4), se inserta directo por SQL admin, una nueva por prueba (codigo
    unico) para que ninguna prueba vea asignaciones de otra."""
    tenant_id = datos_canario["tenant_id"]
    puerta_id = generar_id()
    codigo = f"P{puerta_id % 100_000_000}"  # ops.puerta.codigo es VARCHAR(10)
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ops.puerta "
                "(id, tenant_id, terminal_id, codigo, tipo, envergadura_max_m, tiene_pasarela) "
                "VALUES (:id, :t, :term, :codigo, 'contacto', 60.00, TRUE)"
            ),
            {"id": puerta_id, "t": tenant_id, "term": terminal_canario, "codigo": codigo},
        )
    return puerta_id


@pytest.fixture()
def puerta_chica_canaria(admin_engine, datos_canario, terminal_canario):
    """Puerta DEMASIADO pequena para la aeronave canario (envergadura
    ~35.80m) -- control de PuertaIncompatible (422)."""
    tenant_id = datos_canario["tenant_id"]
    puerta_id = generar_id()
    codigo = f"C{puerta_id % 100_000_000}"  # ops.puerta.codigo es VARCHAR(10)
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ops.puerta "
                "(id, tenant_id, terminal_id, codigo, tipo, envergadura_max_m, tiene_pasarela) "
                "VALUES (:id, :t, :term, :codigo, 'remota', 10.00, FALSE)"
            ),
            {"id": puerta_id, "t": tenant_id, "term": terminal_canario, "codigo": codigo},
        )
    return puerta_id


def _token(datos_canario) -> str:
    return codificar_jwt(
        rol="role_operations_controller",
        tenant_id=datos_canario["tenant_id"],
        usuario_id=datos_canario["usuario_id"],
        scopes=["vuelos:escribir", "puertas:leer", "puertas:escribir"],
    )


def _crear_vuelo(base_url_o_client, token: str, datos_canario, *, headers_extra=None) -> str:
    r = _post(
        base_url_o_client,
        "/vuelos",
        headers=_auth(token),
        json={
            "aerolinea_id": str(datos_canario["aerolinea_id"]),
            "aeronave_id": str(datos_canario["aeronave_id"]),
            # "PN" + 8 digitos: numero_vuelo es VARCHAR(10), y modulo 100_000
            # (5 digitos) colisiona con demasiada frecuencia entre llamadas
            # rapidas dentro de la MISMA sesion de pytest (los ids Snowflake
            # generados en sucesion comparten casi todo el prefijo temporal,
            # verificado empiricamente: colision reproducible en <10
            # invocaciones); 100_000_000 (8 digitos) baja la probabilidad a
            # un nivel despreciable sin exceder el limite de columna.
            "numero_vuelo": f"PN{generar_id() % 100_000_000}",
            "tipo_vuelo_id": str(datos_canario["tipo_vuelo_id"]),
            "fecha_operacion": "2026-11-01",
            "sentido": "S",
            "aeropuerto_origen_id": str(datos_canario["aeropuerto_origen_id"]),
            "aeropuerto_destino_id": str(datos_canario["aeropuerto_destino_id"]),
            "sta_utc": "2026-11-01T10:00:00Z",
            "std_utc": "2026-11-01T09:00:00Z",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["vuelo_id"]


def _post(base_url_o_client, ruta, **kwargs):
    if isinstance(base_url_o_client, str):
        return requests.post(f"{base_url_o_client}{ruta}", timeout=15, **kwargs)
    return base_url_o_client.post(ruta, **kwargs)


# ---------------------------------------------------------------------------
# PN-05 secuencial (TestClient in-process)
# ---------------------------------------------------------------------------


def test_pn05_asignaciones_disjuntas_se_aceptan(client, datos_canario, puerta_canaria):
    token = _token(datos_canario)
    vuelo_1 = _crear_vuelo(client, token, datos_canario)
    vuelo_2 = _crear_vuelo(client, token, datos_canario)

    r1 = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_1,
            "puerta_id": str(puerta_canaria),
            "inicio_previsto": "2026-11-01T09:00:00Z",
            "fin_previsto": "2026-11-01T10:00:00Z",
        },
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_2,
            "puerta_id": str(puerta_canaria),
            "inicio_previsto": "2026-11-01T11:00:00Z",
            "fin_previsto": "2026-11-01T12:00:00Z",
        },
    )
    assert r2.status_code == 201, r2.text


def test_pn05_intervalo_adyacente_se_acepta(client, datos_canario, puerta_canaria):
    """[09:00,10:00) y [10:00,11:00) SOLO se tocan -- no es un
    solapamiento (mismo criterio del dominio, verificado end-to-end)."""
    token = _token(datos_canario)
    vuelo_1 = _crear_vuelo(client, token, datos_canario)
    vuelo_2 = _crear_vuelo(client, token, datos_canario)

    r1 = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_1,
            "puerta_id": str(puerta_canaria),
            "inicio_previsto": "2026-11-01T09:00:00Z",
            "fin_previsto": "2026-11-01T10:00:00Z",
        },
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_2,
            "puerta_id": str(puerta_canaria),
            "inicio_previsto": "2026-11-01T10:00:00Z",
            "fin_previsto": "2026-11-01T11:00:00Z",
        },
    )
    assert r2.status_code == 201, r2.text


def test_pn05_solapamiento_secuencial_se_rechaza_409(client, datos_canario, puerta_canaria):
    token = _token(datos_canario)
    vuelo_1 = _crear_vuelo(client, token, datos_canario)
    vuelo_2 = _crear_vuelo(client, token, datos_canario)

    r1 = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_1,
            "puerta_id": str(puerta_canaria),
            "inicio_previsto": "2026-11-01T09:00:00Z",
            "fin_previsto": "2026-11-01T10:00:00Z",
        },
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_2,
            "puerta_id": str(puerta_canaria),
            "inicio_previsto": "2026-11-01T09:30:00Z",
            "fin_previsto": "2026-11-01T10:30:00Z",
        },
    )
    assert r2.status_code == 409, r2.text
    assert "solapa" in r2.json()["detail"]


def test_pn05_envergadura_incompatible_se_rechaza_422(client, datos_canario, puerta_chica_canaria):
    token = _token(datos_canario)
    vuelo_1 = _crear_vuelo(client, token, datos_canario)

    r = client.post(
        "/puertas/asignaciones",
        headers=_auth(token),
        json={
            "vuelo_id": vuelo_1,
            "puerta_id": str(puerta_chica_canaria),
            "inicio_previsto": "2026-11-01T09:00:00Z",
            "fin_previsto": "2026-11-01T10:00:00Z",
        },
    )
    assert r.status_code == 422, r.text
    assert "envergadura" in r.json()["detail"]


# ---------------------------------------------------------------------------
# PN-05 concurrente (servidor real, dos peticiones simultaneas sobre la
# MISMA puerta)
# ---------------------------------------------------------------------------


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _puerto_abierto(puerto: int) -> bool:
    try:
        with socket.create_connection(("localhost", puerto), timeout=1.0):
            return True
    except OSError:
        return False


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
            pytest.fail("uvicorn real no arranco a tiempo para medir PN-05 concurrente")
        yield f"http://localhost:{puerto}"
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)


@pytest.mark.lento
def test_pn05_concurrente_solo_una_de_dos_se_acepta(servidor_real, datos_canario, puerta_canaria):
    """Dos peticiones HTTP SIMULTANEAS de asignacion sobre la MISMA puerta
    y ventana horaria -- exactamente una debe aceptarse (201) y la otra
    debe rechazarse por solapamiento (409), nunca ambas aceptadas (violaria
    PN-05) ni un 500 (el "bloqueo de fila" + reintento deben resolverlo
    limpiamente, ver aerohub_gates.infrastructure.comandos y
    aerohub_repository.reintentos)."""
    token = _token(datos_canario)
    vuelo_1 = _crear_vuelo(servidor_real, token, datos_canario)
    vuelo_2 = _crear_vuelo(servidor_real, token, datos_canario)

    def disparar(vuelo_id: str) -> int:
        r = requests.post(
            f"{servidor_real}/puertas/asignaciones",
            headers=_auth(token),
            json={
                "vuelo_id": vuelo_id,
                "puerta_id": str(puerta_canaria),
                "inicio_previsto": "2026-11-01T09:00:00Z",
                "fin_previsto": "2026-11-01T10:00:00Z",
            },
            timeout=15,
        )
        return r.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codigos = list(pool.map(disparar, [vuelo_1, vuelo_2]))

    assert sorted(codigos) == [201, 409], f"codigos obtenidos: {codigos}"
