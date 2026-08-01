# Implementation Plan: M4 Ground Operations -- turnaround, y dockerización completa del stack

**Branch**: `main` | **Date**: 2026-08-01 (retroactivo) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-ground-operations-turnaround/spec.md`

## Summary

Módulo `services/ramp` completo con detección SÍNCRONA de desviación de
estándar (sin ciclo de fondo, a diferencia de FIDS), mínimo privilegio de
`role_ramp_agent` aplicado en infraestructura, y panel Angular. Segunda
mitad del sprint: dockerización del gateway y ambos frontends
(`services/gateway/Dockerfile`, `apps/web/Dockerfile`,
`apps/fids-player/Dockerfile`), ampliación de `infra/docker-compose.yml`, y
corrección de `uv.lock` desactualizado. Cierra además con la creación de
`CLAUDE.md` (contexto persistente entre sesiones) y este mismo setup de
Spec Kit retroactivo.

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22

**Primary Dependencies**: FastAPI; sin dependencias nuevas de negocio (a
diferencia de S1.3/S1.4, que agregaron `prometheus-client`/`pulp`)

**Storage**: MonetDB -- `rampa.tipo_tarea`, `rampa.tipo_incidencia_rampa`
(catálogos), `rampa.turnaround`, `rampa.tarea_turnaround`,
`rampa.incidencia_rampa` (`db/ddl/monetdb/11_rampa.sql`, nuevo)

**Testing**: `pytest` unit (dominio: duración derivada, detección de
desviación) + integration (mínimo privilegio + medición de latencia de
incidencia, vía `TestClient`, sin necesidad de servidor real porque no hay WS)

**Target Platform**: DESDE este sprint, Docker Compose para gateway + web +
fids-player + toda la infraestructura -- ya no procesos sueltos en el host

**Performance Goals**: RF-O16 (< 60s desde superar el estándar hasta la
incidencia) -- trivialmente cumplido por ser síncrono, medido igual (~0.9s)

**Constraints**: `role_ramp_agent` es el único rol con `INSERT`/`UPDATE`
sobre `rampa` en la matriz de privilegios -- también crea el turnaround, no
solo sus tareas (deviación documentada de la matriz literal)

**Scale/Scope**: 1 módulo de negocio nuevo, 3 `Dockerfile` nuevos, `uv.lock`
regenerado, `CLAUDE.md` nuevo

## Constitution Check

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE, extendido
  -- primer módulo que aplica mínimo privilegio DENTRO de un mismo tenant
  (`role_ramp_agent` solo ve sus propias tareas), no solo entre tenants.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- la
  decisión de NO construir un ciclo de fondo (a diferencia de FIDS) se tomó
  releyendo el flujo de CU-O16 con cuidado (el evento "marca fin" YA es el
  momento en que se conoce la duración), evitando complejidad innecesaria
  que un ciclo periódico habría agregado sin necesidad.
- **Requisitos Tecnológicos y de Infraestructura** (constitución): este
  sprint es el que hace CIERTA la afirmación "todo servicio corre en
  Docker" -- antes de S1.5 era aspiracional para el gateway/frontends.

## Project Structure

### Documentation (this feature)

```text
specs/007-ground-operations-turnaround/
├── plan.md
└── spec.md
```

### Source Code (repository root)

```text
services/ramp/aerohub_ramp/
├── domain/
│   ├── turnaround.py, tarea_turnaround.py    # duracion_minutos(), excede_estandar()
│   └── incidencia_rampa.py                    # severidad_por_desviacion()
├── infrastructure/consultas.py                 # listar_tareas_de_turnaround() -- filtro
│                                                  por agente si rol_actor == role_ramp_agent
├── application/
│   ├── crear_turnaround.py, iniciar_tarea.py
│   └── finalizar_tarea.py                       # deteccion SINCRONICA de desviacion
└── api/router.py

db/ddl/monetdb/11_rampa.sql, 97_grants_rampa.sql
db/seeds/generate.py    # TIPOS_TAREA, TIPOS_INCIDENCIA_RAMPA sembrados

apps/web/src/app/rampa/panel-turnaround/

# Dockerizacion (segunda mitad del sprint)
services/gateway/Dockerfile      # workspace uv completo, uv sync --all-packages
apps/web/Dockerfile               # npx nx serve --host 0.0.0.0
apps/fids-player/Dockerfile        # idem, puerto 4300
infra/docker-compose.yml           # servicios gateway/web/fids-player nuevos
infra/prometheus/prometheus.yml    # scrape target del gateway
.dockerignore

CLAUDE.md                           # contexto persistente entre sesiones (nuevo)
.specify/                           # Spec Kit -- retroactivo para S0.1-S1.5
```

**Structure Decision**: `finalizar_tarea.py` NO dispara un evento asíncrono
ni encola nada -- la detección de desviación y la creación de la incidencia
ocurren en la MISMA función y la MISMA transacción que el `UPDATE` de la
tarea, deliberadamente más simple que el patrón de ciclo de fondo de FIDS
porque el problema real es distinto (evento explícito vs. ausencia de
evento).

## Complexity Tracking

Sin violaciones que justificar.
