"""Compuerta de pruebas de S1.3 (Plan §8.3): PN-11 (0 campos capaces de
identificar a un pasajero en el esquema de M2), medicion de RNF-P02
(propagacion de plantilla FIDS < 1s) y RNF-R04 (deteccion de pantalla sin
senal < 60s, por simulacion de corte).

RNF-P02 usa un servidor uvicorn REAL (subproceso), no `TestClient` -- mismo
motivo que RNF-P01 en test_pn06_pn07_rnf_p01.py: abrir una conexion
WebSocket y hacer peticiones HTTP en el MISMO `TestClient` produce un
deadlock reproducible. PN-11 y RNF-R04 no usan WebSocket, asi que usan el
`client` (TestClient in-process) de conftest.py.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests
import websockets
from aerohub_gateway.infrastructure import codificar_jwt
from aerohub_kernel import generar_id
from sqlalchemy import text

RUTA_MAIN = Path(__file__).resolve().parents[2] / "services" / "gateway"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def datos_canario(admin_engine):
    with admin_engine.connect() as conn:
        mec = conn.execute(text("SELECT id FROM tenants.tenant WHERE codigo = 'MEC'")).fetchone()
        usuario = None
        if mec is not None:
            usuario = conn.execute(
                text("SELECT id FROM tenants.usuario WHERE tenant_id = :t LIMIT 1"),
                {"t": mec.id},
            ).fetchone()
    if mec is None or usuario is None:
        pytest.fail(
            "Datos canario no encontrados -- ejecutar "
            "'uv run python -m db.seeds.generate' antes de esta suite."
        )
    return {"tenant_id": mec.id, "usuario_id": usuario.id}


@pytest.fixture()
def terminal_canario(admin_engine, datos_canario):
    """No existe (ni lo exige S1.3) un endpoint de creacion de terminal --
    se obtiene o crea directamente por SQL admin, igual que
    test_pn06_pn07_rnf_p01.py crea API Keys ya revocadas/expiradas que el
    endpoint de creacion tampoco permite producir.
    """
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


def _token_fids(tenant_id: int, usuario_id: int) -> str:
    return codificar_jwt(
        rol="role_tenant_admin",
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        scopes=["fids:administrar", "fids:leer", "fids:heartbeat"],
    )


# ---------------------------------------------------------------------------
# PN-11: 0 campos PII en el esquema de M2 (nivel HTTP, sobre el dominio ya
# cubierto por tests/unit/fids/test_plantilla.py)
# ---------------------------------------------------------------------------


def test_pn11_definicion_json_con_pii_es_422(client, datos_canario):
    token = _token_fids(datos_canario["tenant_id"], datos_canario["usuario_id"])
    r = client.post(
        "/fids/plantillas",
        headers=_auth(token),
        json={
            "nombre": f"pn11-{generar_id()}",
            "definicion_json": {"filas": [{"pasajero": "no deberia aceptarse"}]},
        },
    )
    assert r.status_code == 422
    assert "PN-11" in r.json()["detail"]


def test_pn11_definicion_json_sin_pii_no_se_rechaza(client, datos_canario):
    """Control positivo: si esta prueba fallara, la anterior pasaria por
    una razon equivocada (p. ej. un bug que rechace TODA plantilla)."""
    token = _token_fids(datos_canario["tenant_id"], datos_canario["usuario_id"])
    r = client.post(
        "/fids/plantillas",
        headers=_auth(token),
        json={"nombre": f"pn11-{generar_id()}", "definicion_json": {"filas": [{"texto": "ok"}]}},
    )
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# RNF-P02: plantilla publicada -> reflejada en pantalla por WS en < 1s
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
            pytest.fail("uvicorn real no arranco a tiempo para medir RNF-P02")
        yield f"http://localhost:{puerto}"
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)


@pytest.mark.lento
def test_rnf_p02_latencia_de_propagacion_bajo_1s(servidor_real, datos_canario, terminal_canario):
    """RNF-P02, a diferencia de RNF-P01 (100 cambios CONCURRENTES, exigido
    explicitamente por el Plan §8.2), no especifica concurrencia (Plan
    §8.3: solo "< 1s") -- se mide una serie de publicaciones SECUENCIALES
    (publicar -> asignar -> recibir por WS), suficiente para la garantia
    que el requisito realmente exige.
    """
    token = _token_fids(datos_canario["tenant_id"], datos_canario["usuario_id"])
    nombre_plantilla = f"rnfp02-{generar_id()}"

    r = requests.post(
        f"{servidor_real}/fids/plantillas",
        headers=_auth(token),
        json={"nombre": nombre_plantilla, "definicion_json": {"filas": [{"texto": "inicial"}]}},
        timeout=10,
    )
    assert r.status_code == 201, r.text
    plantilla_id_inicial = r.json()["plantilla_id"]

    codigo_pantalla = f"RNFP02-{generar_id() % 100_000}"
    r = requests.post(
        f"{servidor_real}/fids/pantallas",
        headers=_auth(token),
        json={
            "terminal_id": str(terminal_canario),
            "codigo": codigo_pantalla,
            "plantilla_id": plantilla_id_inicial,
        },
        timeout=10,
    )
    assert r.status_code == 201, r.text
    pantalla_id = r.json()["pantalla_id"]

    n = 20

    async def escuchar_y_medir() -> list[float]:
        base_ws = servidor_real.replace("http", "ws")
        url_ws = f"{base_ws}/fids/ws/pantalla/{codigo_pantalla}?token={token}"
        async with websockets.connect(url_ws) as ws:
            await asyncio.sleep(0.2)  # dar tiempo a que la suscripcion quede lista
            latencias: list[float] = []
            for i in range(n):
                r = await asyncio.to_thread(
                    requests.post,
                    f"{servidor_real}/fids/plantillas",
                    headers=_auth(token),
                    json={
                        "nombre": nombre_plantilla,
                        "definicion_json": {"filas": [{"texto": f"version {i}"}]},
                    },
                    timeout=10,
                )
                assert r.status_code == 201, r.text
                nueva_plantilla_id = r.json()["plantilla_id"]

                r2 = await asyncio.to_thread(
                    requests.patch,
                    f"{servidor_real}/fids/pantallas/{pantalla_id}/plantilla",
                    headers=_auth(token),
                    json={"plantilla_id": nueva_plantilla_id},
                    timeout=10,
                )
                assert r2.status_code == 204, r2.text
                t0 = time.monotonic()
                mensaje = await asyncio.wait_for(ws.recv(), timeout=5)
                latencias.append(time.monotonic() - t0)
                assert mensaje  # el contenido en si no importa aqui
            return latencias

    latencias = asyncio.run(escuchar_y_medir())
    assert len(latencias) == n
    assert max(latencias) < 1.0, (
        f"latencia maxima de propagacion {max(latencias):.3f}s -- RNF-P02 exige < 1s "
        f"(promedio {sum(latencias) / len(latencias):.3f}s)"
    )


# ---------------------------------------------------------------------------
# RNF-R04: pantalla sin senal detectada en < 60s (simulacion de corte)
# ---------------------------------------------------------------------------


def test_rnf_r04_pantalla_sin_senal_se_detecta(
    client, admin_engine, datos_canario, terminal_canario
):
    """No se espera el umbral real de produccion (60s) en la prueba -- se
    inyecta un umbral corto a `ejecutar_ciclo_monitoreo` (ya lo admite,
    ver aerohub_fids.application.monitorear_senal) y se retrocede
    `ultima_senal_en` por SQL admin para simular un corte de senal ya
    vencido; medir con el umbral real solo alargaria la prueba sin anadir
    cobertura -- la logica de comparacion es la misma para cualquier
    umbral (ver PantallaFids.esta_sin_senal, cubierta a nivel de dominio
    en tests/unit/fids/test_pantalla.py).
    """
    from aerohub_fids.application import ejecutar_ciclo_monitoreo

    token = _token_fids(datos_canario["tenant_id"], datos_canario["usuario_id"])
    nombre_plantilla = f"rnfr04-{generar_id()}"

    r = client.post(
        "/fids/plantillas",
        headers=_auth(token),
        json={"nombre": nombre_plantilla, "definicion_json": {"filas": [{"texto": "x"}]}},
    )
    assert r.status_code == 201
    plantilla_id = r.json()["plantilla_id"]

    codigo_cortada = f"RNFR04-CORTE-{generar_id() % 100_000}"
    r = client.post(
        "/fids/pantallas",
        headers=_auth(token),
        json={
            "terminal_id": str(terminal_canario),
            "codigo": codigo_cortada,
            "plantilla_id": plantilla_id,
        },
    )
    assert r.status_code == 201
    pantalla_cortada_id = int(r.json()["pantalla_id"])

    codigo_viva = f"RNFR04-VIVA-{generar_id() % 100_000}"
    r = client.post(
        "/fids/pantallas",
        headers=_auth(token),
        json={
            "terminal_id": str(terminal_canario),
            "codigo": codigo_viva,
            "plantilla_id": plantilla_id,
        },
    )
    assert r.status_code == 201
    pantalla_viva_id = int(r.json()["pantalla_id"])

    # Ambas pantallas laten una vez (estado -> 'en_linea').
    for pid in (pantalla_cortada_id, pantalla_viva_id):
        r = client.post(f"/fids/pantallas/{pid}/heartbeat", headers=_auth(token), json={})
        assert r.status_code == 204

    # Solo la "cortada" retrocede su ultimo heartbeat -- simula que dejo de
    # emitir hace mas tiempo del umbral que se va a evaluar.
    with admin_engine.begin() as conn:
        conn.execute(
            text("UPDATE ops.pantalla_fids SET ultima_senal_en = :t WHERE id = :id"),
            {"t": datetime.now(UTC) - timedelta(seconds=5), "id": pantalla_cortada_id},
        )

    resultado = ejecutar_ciclo_monitoreo(umbral_segundos=1)

    assert pantalla_cortada_id in resultado.marcadas_sin_senal
    assert pantalla_viva_id not in resultado.marcadas_sin_senal

    with admin_engine.connect() as conn:
        estado_cortada = conn.execute(
            text("SELECT estado FROM ops.pantalla_fids WHERE id = :id"), {"id": pantalla_cortada_id}
        ).scalar_one()
        estado_viva = conn.execute(
            text("SELECT estado FROM ops.pantalla_fids WHERE id = :id"), {"id": pantalla_viva_id}
        ).scalar_one()
    assert estado_cortada == "sin_senal"
    assert estado_viva == "en_linea"
