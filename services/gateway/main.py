"""Composicion de la API HTTP de AeroHub (Sprint S1.1, Plan §8.1; FIDS y
metricas agregados en S1.3, Plan §8.3).

Deliberadamente FUERA del paquete `aerohub_gateway` (sibling, no submodulo):
el contrato de independencia de modulos verificado por import-linter
(.importlinter, "sin-importacion-cruzada-entre-modulos") prohibe que
CUALQUIER modulo de services/ importe a otro, incluido aerohub_gateway
importando aerohub_tenancy/aerohub_aodb/aerohub_fids -- los modulos de
negocio son independientes entre si de verdad, no solo "por capas". La
composicion de un proceso HTTP que sirve varios modulos a la vez tiene que
vivir en un punto fuera de esa malla de independencia; este script es ese
punto (mismo principio que db/migrations/apply.py o db/seeds/generate.py:
un script de arranque, no un paquete de negocio con sus propias capas).

Uso (desarrollo):
    uv run uvicorn main:app --app-dir services/gateway --reload
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aerohub_aodb.api import router as router_aodb
from aerohub_billing.api import router as router_billing
from aerohub_compliance.api import router as router_compliance
from aerohub_fids.api import router as router_fids
from aerohub_fids.application import ejecutar_ciclo_monitoreo
from aerohub_fids.metricas import contar_pantalla_sin_senal
from aerohub_gates.api import router as router_gates
from aerohub_gateway.api import AutenticacionJWTMiddleware
from aerohub_passenger.api import router as router_passenger
from aerohub_ramp.api import router as router_ramp
from aerohub_support.api import router as router_support
from aerohub_tenancy.api import router as router_tenancy
from aerohub_tenancy.api import router_auth
from aerohub_tenancy.infrastructure import (
    configurar_adaptador_correo,
    crear_adaptador_smtp_desde_entorno,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import OperationalError

_registro = logging.getLogger("aerohub.gateway")

# Origenes de los servidores de desarrollo de Angular (apps/web S1.1,
# apps/fids-player S1.3) -- permisivo solo para localhost, no un comodin.
# Revisar antes de cualquier despliegue mas alla de desarrollo local.
_ORIGENES_DEV = [
    "http://localhost:4200",
    "http://localhost:4300",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:4300",
]

# Intervalo del ciclo del monitor de senal (RNF-R04): sensiblemente menor
# al umbral de 60s (ver aerohub_fids.application.monitorear_senal) para
# que la deteccion tenga margen real, no solo en el caso promedio.
_INTERVALO_MONITOR_SENAL_S = 10.0

_TAGS = [
    {
        "name": "auth",
        "description": (
            "Login, sesion, perfil de acceso, invitaciones y ciclo de vida de la credencial."
        ),
    },
    {"name": "tenants", "description": "Aprovisionamiento de tenants y gestion de API Keys."},
    {"name": "vuelos", "description": "Alta, consulta y cambio de estado de vuelos (AODB)."},
    {"name": "fids", "description": "Plantillas y pantallas FIDS, publicacion en tiempo real."},
    {"name": "puertas", "description": "Asignacion de puertas, manual y automatica (PuLP)."},
    {"name": "rampa", "description": "Turnaround, tareas de rampa e incidencias por desviacion."},
    {
        "name": "facturacion",
        "description": "Tarifarios, motor de facturacion, facturas y conciliacion de pasajeros.",
    },
    {
        "name": "experiencia-pasajero",
        "description": "Estimacion agregada de tiempos de espera por terminal, sin PII.",
    },
    {
        "name": "compliance",
        "description": (
            "Incidentes de seguridad, post-mortems, reportes regulatorios y evidencia SOC 2."
        ),
    },
    {
        "name": "soporte",
        "description": (
            "Tickets con SLA, base de conocimientos, changelog y uptime/error budget."
        ),
    },
]


async def _ciclo_monitor_senal_fids() -> None:
    """Tarea de fondo (RNF-R04): reevalua todas las pantallas cada
    `_INTERVALO_MONITOR_SENAL_S` segundos. `ejecutar_ciclo_monitoreo` es
    sincrona (SQLAlchemy sync) -- se ejecuta en un hilo aparte via
    `asyncio.to_thread` para no bloquear el event loop mientras dura la
    consulta a MonetDB.
    """
    while True:
        try:
            resultado = await asyncio.to_thread(ejecutar_ciclo_monitoreo)
            contar_pantalla_sin_senal(cantidad=len(resultado.marcadas_sin_senal))
        except Exception:
            # Un fallo de un ciclo (p. ej. MonetDB momentaneamente
            # inalcanzable) no debe matar la tarea de fondo -- se reintenta
            # en el siguiente ciclo.
            _registro.exception("fallo un ciclo del monitor de senal FIDS")
        await asyncio.sleep(_INTERVALO_MONITOR_SENAL_S)


def _manejador_acceso_denegado_motor(request: Request, exc: Exception) -> JSONResponse:
    """Sprint S1.6: primer caso de un rol con CERO grants sobre un esquema
    completo (role_support sobre `billing`, matriz 4.3.1 celda '-',
    98_grants_billing.sql). A diferencia del minimo privilegio DENTRO de
    un mismo modulo (role_ramp_agent, S1.5 -- resuelto en
    infrastructure/ con un 404 por fila ajena), esto es un rechazo del
    motor mismo via `SET ROLE` + GRANT ausente (packages/repository/base.py):
    "42000!... access denied for aerohub_app to table ...". Sin este
    handler, MonetDB filtra un OperationalError de SQLAlchemy sin traducir
    -- 500 generico, sin PN-07 (401/403 legible, sin fuga de informacion).
    Se distingue por el mensaje ("access denied") para no enmascarar otros
    OperationalError legitimos (p. ej. MonetDB caido) -- Starlette exige la
    firma generica (request, Exception), el registro por tipo en
    add_exception_handler ya garantiza que solo llega un OperationalError --
    RuntimeError, no assert (bandit B101: un assert desaparece bajo
    bytecode optimizado)."""
    if not isinstance(exc, OperationalError):
        raise RuntimeError(
            f"_manejador_acceso_denegado_motor recibio {type(exc).__name__}, "
            "esperaba OperationalError"
        )
    causa_raiz = str(exc.orig) if exc.orig is not None else str(exc)
    if "access denied" not in causa_raiz:
        raise exc
    return JSONResponse(status_code=403, content={"detail": "acceso denegado"})


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    tarea = asyncio.create_task(_ciclo_monitor_senal_fids())
    try:
        yield
    finally:
        tarea.cancel()


def crear_app() -> FastAPI:
    app = FastAPI(
        title="AeroHub API",
        description=(
            "API operacional de AeroHub: aprovisionamiento de tenants, "
            "seguimiento de vuelos y distribucion de FIDS en tiempo real "
            "(RF-T02, OpenAPI 3.1)."
        ),
        contact={"name": "AeroHub Platform Team"},
        servers=[{"url": "http://localhost:8000", "description": "Desarrollo local"}],
        openapi_tags=_TAGS,
        lifespan=_ciclo_de_vida,
    )
    # S1.10: adaptador SMTP inyectado desde el borde (contracts/correo-puerto.md)
    # -- aerohub_tenancy/application/ depende solo del puerto EnviarCorreo,
    # nunca de este adaptador concreto.
    configurar_adaptador_correo(crear_adaptador_smtp_desde_entorno())
    # Orden importa: Starlette ejecuta el middleware añadido MAS TARDE
    # primero (es el mas externo) -- CORS debe envolver a la autenticacion,
    # no al reves, o un preflight OPTIONS (sin Authorization) se rechaza con
    # 401 antes de que el navegador siquiera vea las cabeceras CORS.
    app.add_middleware(AutenticacionJWTMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ORIGENES_DEV,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router_tenancy)
    app.include_router(router_auth)
    app.include_router(router_aodb)
    app.include_router(router_fids)
    app.include_router(router_gates)
    app.include_router(router_ramp)
    app.include_router(router_billing)
    app.include_router(router_passenger)
    app.include_router(router_compliance)
    app.include_router(router_support)
    app.add_exception_handler(OperationalError, _manejador_acceso_denegado_motor)

    @app.exception_handler(Exception)
    async def manejador_excepciones_generales(request: Request, exc: Exception) -> JSONResponse:
        _registro.exception("Excepción no capturada en la petición %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor"},
        )

    @app.get("/metrics", include_in_schema=False)
    def metricas() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = crear_app()
