# Implementation Plan: Contrato de API y superficie del AODB

**Branch**: `main` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-contrato-api-superficie-aodb/spec.md`

## Summary

Primer sprint de la Fase 1.5 (`docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.1). Regenera `docs/api/openapi.yaml` con la herramienta ya existente (`tools/generar_openapi.py`, construida en S1.2 pero nunca vuelta a correr desde el workpanel de tenants/usuarios) y agrega una compuerta de CI que falla si el archivo comiteado difiere del generado. Construye en `apps/web` la superficie de M1 AODB que hoy no existe: alta de vuelo, consulta puntual y registro de cambio de estado, consumiendo los 3 endpoints REST ya construidos en `services/aodb`. Cierra dos endpoints huérfanos de bajo costo: cancelar asignación de puerta (`puertas/tablero-puertas`, vista existente) y reenviar verificación de correo (ubicado en el shell, no en la vista pública de verificación -- ver research.md Decisión 4).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy Core (backend ya existentes); `tools/generar_openapi.py` (ya existe, se re-ejecuta); ningún paquete nuevo.

**Storage**: MonetDB -- `ops.vuelo`/`ops.vuelo_estado` (ya existen, S1.1); **tablas nuevas a redeclarar localmente en `aerohub_aodb/infrastructure/` (solo lectura, sin DDL nuevo)**: `catalogo.aerolinea`, `catalogo.aeronave`, `catalogo.modelo_aeronave`, `catalogo.tipo_vuelo` -- necesarias para que el formulario de alta de vuelo ofrezca selects en vez de pedir ids Snowflake a mano (spec.md FR-010).

**Testing**: `pytest` (unit/integration/negative/cross_tenant) contra MonetDB real en Docker; verificación en navegador real contra el gateway en Docker (Principio III); `spectral lint` sobre el contrato regenerado.

**Target Platform**: contenedores Docker (`gateway`, `web`) -- todo servicio que se verifica corre en Docker (regla de trabajo del proyecto).

**Performance Goals**: sin objetivo nuevo -- el WebSocket de tiempo real ya cumple RNF-P01 (< 1 s) desde S1.2, este sprint solo agrega los emisores que faltaban.

**Constraints**: cero cambios al contrato de los 3 endpoints REST de vuelos ni de los 2 endpoints huérfanos -- ya existen y ya están probados; todo id Snowflake nuevo viaja como string en JSON (mismo hallazgo de S1.1); `aerohub_aodb` no importa `aerohub_tenancy` ni ningún otro módulo de negocio (Principio II) -- las tablas de catálogo se redeclaran localmente, mismo patrón que `consultas_catalogo.py` de tenancy sobre `catalogo.aeropuerto`.

**Scale/Scope**: 1 módulo de negocio con backend nuevo (`aodb`, solo lectura de catálogo), 3 vistas/ampliaciones de frontend (vuelos, puertas, shell), 1 herramienta re-ejecutada + 1 paso de CI nuevo.

## Constitution Check

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE -- las consultas de catálogo son globales (sin `tenant_id`, mismo criterio que `catalogo.aeropuerto` en tenancy) y no requieren `alcance_global()`; el alta/consulta/cambio de estado de vuelo ya filtra por `contexto_tenant_id()` desde S1.1, sin tocarse en este sprint.
- **Principio II (Arquitectura Modular por Capas e Independencia de Módulos)**: CUMPLE -- las tablas de catálogo se redeclaran en `aerohub_aodb/infrastructure/`, no se importan desde `aerohub_tenancy`; verificado por `import-linter` en CI.
- **Principio III (Verificación Empírica Obligatoria)**: se aplica -- alta de vuelo real, cambio de estado real reflejado en el WebSocket, contrato regenerado y verificado contra el backend real en Docker, todo antes de reportar el sprint como cerrado.
- **Principio IV (Calidad Continua en Verde)**: ruff/mypy/bandit/import-linter/pytest en verde; el nuevo paso de CI de contrato se agrega al job `contrato-api` ya existente.
- **Principio V (Aprobación Explícita)**: diff presentado antes de cualquier commit; commit solo si se pide.
- **Infraestructura**: verificación en `gateway`/`web` en Docker, no sueltos en el host.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/017-contrato-api-superficie-aodb/
├── plan.md
├── research.md
└── quickstart.md
```

Sin `data-model.md` ni `contracts/` -- mismo criterio que los sprints sustantivos previos del proyecto (specs/003, specs/004): las entidades y el contrato HTTP ya están descritos en `spec.md` §Key Entities y en el propio backend (`services/aodb/aerohub_aodb/api/router.py`), que no cambia de forma en este sprint -- documentarlo aparte sería duplicar, no aportar.

### Source Code (repository root)

```text
tools/
└── generar_openapi.py               # ya existe (S1.2) -- se re-ejecuta, sin cambios de codigo

.github/workflows/
└── ci.yml                            # job contrato-api gana un paso: generar a un archivo temporal y diff contra el comiteado

services/aodb/aerohub_aodb/
├── infrastructure/
│   ├── consultas_catalogo.py         # NUEVO -- redeclara catalogo.aerolinea/aeronave/modelo_aeronave/tipo_vuelo (solo lectura), mismo patron que tenancy/consultas_catalogo.py
│   └── __init__.py                   # + exporta las nuevas consultas
├── application/
│   └── consultar_catalogos.py        # NUEVO -- casos de uso listar_aerolineas/listar_aeronaves/listar_tipos_vuelo
└── api/
    └── router.py                     # + GET /vuelos/catalogo/aerolineas, /aeronaves, /tipos-vuelo

apps/web/src/app/vuelos/
├── vuelo.service.ts                  # NUEVO -- altaVuelo, obtenerVuelo, cambiarEstadoVuelo, listarAerolineas/Aeronaves/TiposVuelo/Aeropuertos
└── estado-tiempo-real/
    ├── estado-tiempo-real.html       # + boton "Nuevo vuelo" -> modal de alta; accion "Cambiar estado" por fila -> modal
    └── estado-tiempo-real.ts         # + estado de los 2 modales, wiring a vuelo.service.ts

apps/web/src/app/puertas/
├── puertas.service.ts                # + cancelarAsignacion(id)
└── tablero-puertas/
    ├── tablero-puertas.html          # + boton "Cancelar" en el modal "Ver asignaciones"
    └── tablero-puertas.ts            # + metodo cancelar()

apps/web/src/app/auth/
└── auth.service.ts                   # + solicitarVerificacion()

apps/web/src/app/shell/
├── shell.html                        # + banner condicional (perfil().email_verificado === false)
└── shell.ts                          # + accion reenviarVerificacion()
```

**Structure Decision**: mismo patrón por componente que los sprints previos (frontend) y mismo patrón de capas `domain/application/infrastructure/api` que el resto de `services/` (backend). El único módulo de backend tocado es `aodb`, y solo en su capa `infrastructure/`+`application/`+`api/` para catálogos de solo lectura -- `domain/` no cambia (sin regla de negocio nueva).

## Complexity Tracking

Sin violaciones que justificar.
