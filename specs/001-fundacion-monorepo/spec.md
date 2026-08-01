# Feature Specification: Fundación del monorepo

**Feature Branch**: `main` (sin branch dedicado -- desarrollado directo en `main`, práctica de todo el proyecto)

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commit `181b610`

**Input**: Sprint S0.1 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §7.1. Re-derivar el proyecto
íntegramente de `docs/srs/AEROHUB-SRS-001-v2.0.md`, ambos SDD (`docs/sdd/`) y
`docs/estrategia/AEROHUB-ANALISIS-ESTRATEGICO-v6.0.md`, eliminando todo artefacto de una
versión anterior basada en PostgreSQL/RLS que la SRS v2.0 invalida explícitamente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Arrancar el entorno de desarrollo completo (Priority: P1)

Como desarrollador que se incorpora al proyecto, necesito poder levantar toda la
infraestructura de datos y observabilidad con un solo comando, y confirmar que
cada pieza responde sana, antes de escribir la primera línea de código de negocio.

**Why this priority**: sin esto, ningún sprint posterior tiene dónde correr. Es la
base literal de todo lo que sigue.

**Independent Test**: `docker compose -f infra/docker-compose.yml up` levanta los
8 servicios (MonetDB primario, MonetDB standby, ClickHouse, MinIO, Airflow,
Prometheus, Loki, Grafana) y cada uno responde a su healthcheck.

**Acceptance Scenarios**:

1. **Given** el repo recién clonado, **When** se ejecuta `docker compose up`,
   **Then** los 8 servicios llegan a estado `healthy` sin intervención manual.
2. **Given** el contenedor de Airflow se recrea sobre un volumen ya inicializado,
   **When** arranca, **Then** no debe colgarse (hallazgo real corregido en este
   sprint, documentado en `docs/runbooks/airflow.md`).

---

### User Story 2 - Verificar las reglas de dependencia entre módulos (Priority: P1)

Como arquitecto del proyecto, necesito que la independencia de módulos de negocio
(ADR-017) sea un contrato verificado automáticamente, no solo una convención
documentada, para que una violación futura falle el build en vez de acumularse
como deuda invisible.

**Why this priority**: la arquitectura modular es la decisión estructural de la
que depende todo el resto del plan de 24 sprints -- sin verificación automática,
se degrada sprint a sprint.

**Independent Test**: `lint-imports` (import-linter) corre contra el workspace
completo y falla ante una importación cruzada deliberada entre dos módulos de
negocio (probado con una violación real introducida y revertida durante el
sprint, no solo configurado en teoría).

**Acceptance Scenarios**:

1. **Given** el archivo `.importlinter` con los 15+ contratos de capas e
   independencia, **When** se ejecuta `lint-imports`, **Then** el workspace
   completo pasa sin violaciones.
2. **Given** una importación cruzada deliberada entre dos módulos de negocio,
   **When** se ejecuta `lint-imports`, **Then** el contrato
   `sin-importacion-cruzada-entre-modulos` la detecta y falla.

---

### User Story 3 - Tener paquetes transversales con código real y testeado (Priority: P2)

Como desarrollador de cualquier módulo de negocio futuro, necesito que
`aerohub_kernel` (Dinero, CódigoIATA/ICAO, tiempo UTC, generación de IDs) y el
contexto de tenant de `aerohub_repository` (ContextVar + `alcance_global`) ya
existan, probados, para no reinventarlos en cada sprint.

**Why this priority**: son la base que TODOS los módulos de negocio van a
importar; su ausencia bloquea cualquier sprint de Fase 1 en adelante.

**Independent Test**: `pytest` sobre `packages/kernel` y el contexto de
`packages/repository` pasa con cobertura ≥ 90%.

**Acceptance Scenarios**:

1. **Given** `aerohub_kernel.generar_id()`, **When** se invoca repetidamente en
   sucesión rápida, **Then** cada ID es único y monotónicamente creciente.
2. **Given** `alcance_global(motivo=..., rol=...)` sin uno de los dos argumentos,
   **When** se invoca, **Then** lanza `ValueError` (sin defaults implícitos).

---

### User Story 4 - Tener los dos frontends Angular arrancando (Priority: P3)

Como desarrollador de UI, necesito que `apps/web` y `apps/fids-player` ya
compilen sobre Angular 22 vía Nx, aunque todavía no tengan pantallas de negocio,
para que los sprints de Fase 1 solo agreguen componentes, no infraestructura de
build.

**Why this priority**: menor urgencia que el backend -- ningún sprint de Fase 1
depende de UI hasta S1.1.

**Independent Test**: `npx nx build web` y `npx nx build fids-player` compilan
sin errores.

**Acceptance Scenarios**:

1. **Given** el monorepo Nx recién scaffoldeado, **When** se corre
   `npx nx build web`, **Then** genera un bundle sin errores de TypeScript.

### Edge Cases

- ¿Qué pasa si `docker compose up` se ejecuta dos veces seguidas (contenedores ya
  creados)? Debe ser idempotente -- reutiliza los volúmenes existentes.
- ¿Qué pasa si el CI corre `lint-imports` sobre un PR que solo toca
  documentación? Debe seguir pasando (no debe fallar por archivos no-Python).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El repositorio DEBE organizarse como monorepo `uv` workspace con
  paquetes transversales (`packages/kernel`, `packages/contracts`,
  `packages/repository`) y un directorio `services/<modulo>` por módulo de
  negocio de la SRS (12 módulos, aunque en S0.1 solo 3 tienen código real:
  el resto queda scaffoldeado vacío para sprints futuros).
- **FR-002**: Cada módulo de negocio DEBE seguir la estructura de capas
  `domain/application/infrastructure/api` (ADR-017 §5.4), verificada por
  `import-linter`.
- **FR-003**: El sistema DEBE proveer 8 servicios de infraestructura vía Docker
  Compose: MonetDB primario y standby (ADR-013, ADR-018), ClickHouse (ADR-012),
  MinIO, Airflow, Prometheus, Loki, Grafana.
- **FR-004**: `aerohub_kernel` DEBE proveer generación de IDs únicos
  (Snowflake-like), un tipo `Dinero`, validación de `CodigoIATA`/`CodigoICAO`, y
  utilidades de tiempo UTC-aware.
- **FR-005**: `aerohub_repository` DEBE proveer el contexto de tenant
  (`ContextVar` para `tenant_id`/`rol_actor`/`usuario_id`) y `alcance_global()`
  como excepción nominal auditable para procesos de plataforma.
- **FR-006**: El CI (`.github/workflows/ci.yml`) DEBE correr `ruff`, `mypy`,
  `import-linter` y `pytest` en cada push/PR.
- **FR-007**: Los frontends `apps/web` y `apps/fids-player` DEBEN scaffoldearse
  sobre Angular 22 vía Nx y compilar sin errores.
- **FR-008**: Todo artefacto de una versión anterior del proyecto basada en
  PostgreSQL/RLS (invalidada explícitamente por la SRS v2.0) DEBE eliminarse,
  no coexistir como código muerto.

### Key Entities

- **Workspace `uv`**: 17 miembros (`kernel`, `contracts`, `repository`, 12
  servicios de negocio, `pipelines`, `ml`), cada uno con su propio
  `pyproject.toml` y dependencias declaradas explícitamente.
- **`ContextVar` de tenant**: `tenant_id`, `rol_actor`, `usuario_id`,
  `alcance_global_activo` -- el mecanismo por el que TODO el resto del sistema
  sabrá, en cada petición, de qué tenant y con qué rol se está actuando.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los 8 servicios de `docker-compose.yml` alcanzan estado
  `healthy` sin intervención manual, verificado en vivo (no solo configurado).
- **SC-002**: `import-linter` detecta el 100% de las violaciones de
  independencia de módulos probadas deliberadamente durante el sprint.
- **SC-003**: `pytest` sobre `packages/kernel` y el contexto de
  `packages/repository` alcanza ≥ 90% de cobertura (97% real, 27 tests).
- **SC-004**: Ambos frontends Angular compilan sin errores de TypeScript.
- **SC-005**: Cero artefactos del proyecto PostgreSQL/RLS anterior permanecen
  en el repositorio tras el sprint.

## Assumptions

- El proyecto parte de una reformulación completa de arquitectura (v5.1 →
  v6.0/v2.0 de los documentos fuente); no hay compatibilidad hacia atrás que
  preservar con la versión PostgreSQL/RLS anterior.
- MonetDB (no PostgreSQL) es el motor operacional decidido en ADR-013,
  aceptado como restricción de este sprint en adelante, no una elección
  abierta.
- El mecanismo de continuidad completo (ADR-018: journal + snapshot + standby
  + failover) se diseña en S0.1 pero su demostración sostenida queda
  condicionada a un sprint dedicado posterior (S1.9) antes de declarar RNF-R01
  cerrado.
