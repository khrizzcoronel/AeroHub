# Implementation Plan: API del AODB -- API Keys, scopes, rate limiting y WebSocket en tiempo real

**Branch**: `main` | **Date**: 2026-07-31 (retroactivo) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-api-keys-scopes-tiempo-real/spec.md`

## Summary

Sobre el Gateway JWT de S1.1, agrega autenticación dual (JWT corto + API
Key), scopes de grano fino verificados vía `aerohub_contracts.requiere_scope`,
rate limiting por tenant+rol, un canal WebSocket de estado de vuelo en
tiempo real con propagación < 1s bajo carga concurrente, y la primera
especificación OpenAPI 3.1 formal del proyecto.

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22

**Primary Dependencies**: FastAPI (WebSocket nativo), PyJWT, Spectral (linter
de OpenAPI, vía npm)

**Storage**: MonetDB -- `tenants.api_key` (nueva), `ops.vuelo_estado`
(reutilizada de S1.1)

**Testing**: `pytest` contra un servidor uvicorn REAL (subproceso) para medir
RNF-P01 -- `TestClient` in-process produce deadlock entre el hilo de
`BaseHTTPMiddleware` y el portal async de WebSocket, hallazgo empírico de
este sprint

**Target Platform**: backend suelto en el host (dockerización llega en S1.5)

**Performance Goals**: RNF-P01 -- propagación de cambio de estado < 1s, medido
con 100 cambios concurrentes

**Constraints**: la API WebSocket del navegador no admite cabeceras
personalizadas -- el JWT viaja por query string en la conexión WS, no por
`Authorization`

**Scale/Scope**: `aerohub_contracts` deja de estar vacío (primer código real
del paquete), `aerohub_repository.reintentar_en_conflicto` nuevo

## Constitution Check

- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- RNF-P01
  se mide contra un servidor uvicorn real con 100 cambios concurrentes
  reales, no una estimación teórica; el hallazgo de concurrencia optimista
  de MonetDB (SQLSTATE 40001) se descubrió MIDIENDO, no leyendo
  documentación del motor.
- **Principio II (Arquitectura Modular por Capas)**: CUMPLE -- `ws_auth` y
  `requiere_scope` viven en `aerohub_contracts` precisamente para que cada
  módulo de negocio proteja sus propios endpoints sin importar
  `aerohub_gateway` (el contrato de independencia de módulos lo prohibiría).
- **Principio IV (Calidad Continua en Verde)**: CUMPLE -- 211/211 tests,
  ruff/mypy/bandit/import-linter y Spectral (0 errores) en verde.

## Project Structure

### Documentation (this feature)

```text
specs/004-api-keys-scopes-tiempo-real/
├── plan.md
└── spec.md
```

Contrato HTTP formal en `docs/api/openapi.yaml` (generado, no escrito a mano).

### Source Code (repository root)

```text
packages/contracts/aerohub_contracts/
├── scopes.py         # requiere_scope() -- dependencia FastAPI reutilizable
└── ws_auth.py         # autenticar_websocket() -- JWT por query string

packages/repository/aerohub_repository/
└── reintentos.py       # reintentar_en_conflicto() -- retry con backoff+jitter

services/gateway/aerohub_gateway/
├── infrastructure/api_key.py    # validacion de X-Api-Key
├── infrastructure/limitador.py  # rate limiting (cubo de fichas en memoria)
└── application/limitar_tasa.py

services/tenancy/aerohub_tenancy/
├── domain/api_key.py
├── application/gestionar_api_key.py   # crear/revocar
└── infrastructure/comandos_api_key.py

services/aodb/aerohub_aodb/
├── application/tiempo_real.py    # suscribir/desuscribir al broadcaster
├── infrastructure/eventos.py     # BroadcasterEstadoVuelo en proceso
└── api/router.py                 # WS /vuelos/ws/estado

apps/web/src/app/vuelos/estado-tiempo-real/   # vista Angular minima con WS

tools/generar_openapi.py    # genera docs/api/openapi.yaml desde la app FastAPI
.spectral.yaml               # reglas de lint sobre el OpenAPI generado
```

**Structure Decision**: el broadcaster de eventos vive DENTRO del proceso
(cola en memoria, `queue.Queue`), no en un bus externo -- adecuado para un
solo proceso gateway; si el sistema escala a múltiples réplicas, este
patrón necesitaría revisarse (no es el alcance de este sprint).

## Complexity Tracking

Sin violaciones que justificar.
