# Implementation Plan: Fundación del monorepo

**Branch**: `main` | **Date**: 2026-07-30 (retroactivo, documentado 2026-08-01) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-fundacion-monorepo/spec.md`

**Nota**: plan retroactivo -- describe la implementación tal como se construyó
(commit `181b610`), no una planificación previa a construir.

## Summary

Reconstrucción completa del monorepo desde los documentos fuente v2.0/v6.0
(SRS, ambos SDD, Análisis Estratégico), descartando toda la base PostgreSQL/RLS
anterior. Workspace `uv` con 17 miembros, arquitectura modular por capas
verificada por `import-linter`, infraestructura de datos y observabilidad
completa vía Docker Compose, y los dos frontends Angular scaffoldeados.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy Core (nunca el ORM), `uv`
(gestor de workspace Python), Nx 22 (monorepo Angular)

**Storage**: MonetDB (motor operacional, ADR-013) + ClickHouse (analítica
dual, ADR-012); MinIO para capas medallion en Parquet

**Testing**: `pytest` (Python), `import-linter` (contrato de arquitectura),
Angular's builder de test por defecto (frontend, aún sin specs de negocio)

**Target Platform**: contenedores Docker para infraestructura; el backend y
los frontends corrían sueltos en el host en S0.1 (dockerizados recién en
S1.5, ver `specs/007-ground-operations-turnaround/`)

**Project Type**: monorepo -- workspace `uv` (Python) + monorepo Nx
(Angular), en el mismo repositorio Git

**Performance Goals**: N/A para este sprint (sin código de negocio corriendo
todavía)

**Constraints**: ningún artefacto de la arquitectura PostgreSQL/RLS anterior
puede persistir; toda decisión debe trazarse a la SRS v2.0/SDD/Análisis v6.0

**Scale/Scope**: 17 miembros de workspace, 8 servicios de infraestructura, 2
apps Angular

## Constitution Check

*Nota: la constitución (`.specify/memory/constitution.md`) se ratificó en
S1.5, posterior a este sprint -- este chequeo es retroactivo, evaluando S0.1
contra principios que en ese momento no estaban escritos pero SÍ se estaban
siguiendo de hecho (de ahí que la constitución los formalizara sin
inventarlos).*

- **Principio II (Arquitectura Modular por Capas)**: CUMPLE -- este sprint es
  precisamente el que establece ADR-017 y lo hace verificable con
  `import-linter` desde el primer commit.
- **Principio IV (Calidad Continua en Verde)**: CUMPLE -- CI corre
  ruff/mypy/import-linter/pytest desde este sprint.
- Principios I, III y V (aislamiento de tenant, verificación empírica,
  aprobación antes de commit) no aplican todavía de forma plena: no hay
  datos de tenant ni sesiones de MonetDB con lógica de negocio hasta S0.2/S1.1.

## Project Structure

### Documentation (this feature)

```text
specs/001-fundacion-monorepo/
├── plan.md              # Este archivo
└── spec.md              # Especificación retroactiva
```

Sin `research.md`/`data-model.md`/`contracts/` -- no aplican a un sprint de
fundación de infraestructura sin entidades de negocio propias. La
documentación de diseño real vive en `docs/adr/ADR-017-*.md`,
`docs/srs/`, `docs/sdd/`.

### Source Code (repository root)

```text
packages/
├── kernel/                # aerohub_kernel -- Dinero, CodigoIATA/ICAO, tiempo UTC, generar_id
├── contracts/             # aerohub_contracts -- vacío en S0.1, poblado en S1.2
└── repository/            # aerohub_repository -- contexto de tenant, alcance_global

services/
├── gateway/                # scaffold vacío en S0.1
├── aodb/ fids/ gates/ ramp/ billing/ passenger/ compliance/
├── tenancy/ support/ people/ analytics_api/   # todos scaffold vacío en S0.1

pipelines/                  # scaffold vacío
ml/                         # scaffold vacío

apps/
├── web/                    # Angular 22, sin pantallas de negocio
└── fids-player/            # Angular 22, sin pantallas de negocio

infra/
├── docker-compose.yml      # 8 servicios
└── prometheus/prometheus.yml

.importlinter                # contratos de capas + independencia de módulos
.github/workflows/ci.yml     # ruff, mypy, import-linter, pytest
```

**Structure Decision**: monorepo único con dos gestores de dependencias
paralelos (`uv` para Python, `npm`/Nx para TypeScript), sin intentar
unificarlos -- son ecosistemas distintos y la separación es más simple que
cualquier puente artificial.

## Complexity Tracking

Sin violaciones de constitución que justificar (la constitución no existía
todavía; este sprint es coherente con los principios que después se
formalizaron).
