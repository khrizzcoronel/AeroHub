"""Composicion de la API HTTP de AeroHub (Sprint S1.1, Plan §8.1).

Deliberadamente FUERA del paquete `aerohub_gateway` (sibling, no submodulo):
el contrato de independencia de modulos verificado por import-linter
(.importlinter, "sin-importacion-cruzada-entre-modulos") prohibe que
CUALQUIER modulo de services/ importe a otro, incluido aerohub_gateway
importando aerohub_tenancy/aerohub_aodb -- los modulos de negocio son
independientes entre si de verdad, no solo "por capas". La composicion de
un proceso HTTP que sirve varios modulos a la vez tiene que vivir en un
punto fuera de esa malla de independencia; este script es ese punto (mismo
principio que db/migrations/apply.py o db/seeds/generate.py: un script de
arranque, no un paquete de negocio con sus propias capas).

Uso (desarrollo):
    uv run uvicorn main:app --app-dir services/gateway --reload
"""

from __future__ import annotations

from aerohub_aodb.api import router as router_aodb
from aerohub_gateway.api import AutenticacionJWTMiddleware
from aerohub_tenancy.api import router as router_tenancy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Origen del servidor de desarrollo de Angular (apps/web, Plan §8.1) --
# permisivo solo para localhost:4200, no un comodin. Revisar antes de
# cualquier despliegue mas alla de desarrollo local.
_ORIGENES_DEV = ["http://localhost:4200"]


def crear_app() -> FastAPI:
    app = FastAPI(title="AeroHub API")
    # Orden importa: Starlette ejecuta el middleware añadido MAS TARDE
    # primero (es el mas externo) -- CORS debe envolver a la autenticacion,
    # no al reves, o un preflight OPTIONS (sin Authorization) se rechaza con
    # 401 antes de que el navegador siquiera vea las cabeceras CORS.
    app.add_middleware(AutenticacionJWTMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ORIGENES_DEV,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router_tenancy)
    app.include_router(router_aodb)
    return app


app = crear_app()
