# Implementation Plan: M2 FIDS -- plantillas y pantallas en tiempo real, detección de sin-señal

**Branch**: `main` | **Date**: 2026-07-31 (retroactivo) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-fids-plantillas-pantallas/spec.md`

## Summary

Módulo `services/fids` completo (dominio/aplicación/infraestructura/api),
montado en el Gateway junto a `aodb`/`tenancy`: publicación versionada de
plantillas con guardia de PII, WS de propagación por pantalla,
ciclo de fondo de detección de sin-señal, métricas Prometheus, y
`apps/fids-player` como reproductor de referencia.

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22

**Primary Dependencies**: FastAPI, `prometheus-client` (nueva dependencia de
`services/fids`)

**Storage**: MonetDB -- `ops.plantilla_fids`, `ops.pantalla_fids`
(`db/ddl/monetdb/10_ops.sql`, ampliado)

**Testing**: `pytest` unit (dominio) + integration (HTTP + WS contra
servidor real, mismo patrón de `servidor_real` que S1.2)

**Target Platform**: backend suelto en el host; `apps/fids-player` vía
`npx nx serve --port 4300`

**Performance Goals**: RNF-P02 (propagación < 1s), RNF-R04 (detección de
sin-señal < 60s)

**Constraints**: `aerohub_repository.contexto` no se puebla para el scope
ASGI `"websocket"` -- cualquier handler WS que necesite tocar la base debe
poblarlo a mano

**Scale/Scope**: 1 módulo de negocio nuevo completo, 1 app Angular nueva
(`apps/fids-player`), 1 ciclo de fondo nuevo en `services/gateway/main.py`

## Constitution Check

- **Principio II (Arquitectura Modular por Capas)**: CUMPLE -- primer módulo
  que necesita re-declarar localmente el patrón de `contexto_ws` porque
  `aerohub_gateway.infrastructure.contexto_gateway` no puede importarse
  (independencia de módulos) -- reimplementado, no importado.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- RNF-P02 y
  RNF-R04 medidos contra MonetDB y WS reales, no estimados; el bug de
  `ContextoTenantAusente` en el WS se encontró ejecutando una conexión WS
  real, no en revisión de código.

## Project Structure

### Documentation (this feature)

```text
specs/005-fids-plantillas-pantallas/
├── plan.md
└── spec.md
```

### Source Code (repository root)

```text
services/fids/aerohub_fids/
├── domain/plantilla.py         # CLAVES_PII_PROHIBIDAS, _ruta_pii() recursivo
├── domain/pantalla.py           # esta_sin_senal(ahora, umbral_segundos)
├── application/
│   ├── publicar_plantilla.py, registrar_pantalla.py, asignar_plantilla.py
│   ├── registrar_heartbeat.py, consultar_pantalla.py, tiempo_real.py
│   ├── monitorear_senal.py       # ejecutar_ciclo_monitoreo (alcance_global)
│   └── contexto_ws.py            # contexto_de_pantalla_ws (contextmanager)
├── infrastructure/
│   ├── contexto_ws.py             # poblar/limpiar contexto para el WS
│   └── eventos.py                  # BroadcasterFids
├── api/router.py                   # POST/PATCH/GET + WS /fids/ws/pantalla/{codigo}
└── metricas.py                     # Prometheus Histogram/Counter (fuera de las 4 capas, observabilidad pura)

services/gateway/main.py            # ciclo de fondo _ciclo_monitor_senal_fids (10s)

apps/fids-player/                   # app Angular nueva, puerto 4300
```

**Structure Decision**: `metricas.py` vive fuera de la partición
`domain/application/infrastructure/api` deliberadamente -- es un módulo de
observabilidad transversal, no una capa de negocio.

## Complexity Tracking

Sin violaciones que justificar.
