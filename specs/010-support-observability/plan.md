# Implementation Plan: S1.8 -- Soporte D6 y observabilidad

**Branch**: `main` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-support-observability/spec.md`

## Summary

Construye `aerohub_support` desde cero (hoy scaffold vacío) con el
esquema `support` completo del SDD §11 (tickets con SLA, hilo de
mensajes, base de conocimientos global, changelog) y cierra la vertical
de observabilidad (RF-E03/RNF-R02, RF-O10/RNF-R03) SIN persistencia
nueva: uptime y error budget se calculan a demanda contra Prometheus
(ya desplegado desde S0.1), y el bloqueo automático de despliegues se
implementa como un script de compuerta (`tools/verificar_error_budget.py`)
invocable desde CI, auditando cualquier override en
`compliance.log_auditoria` (mismo mecanismo reutilizado en S1.7 para la
denegación de licencia).

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22 (sin vista
Angular nueva planificada para el MVP de este sprint -- ver Assumptions
de spec.md; el consumo de `/support/observabilidad/uptime` es vía
Grafana, no requiere UI propia)

**Primary Dependencies**: FastAPI, SQLAlchemy Core, `prometheus_client`
(ya usado desde S1.3), cliente HTTP para consultar la API de Prometheus
(`httpx`, ya presente como dependencia transitiva de FastAPI/TestClient)
-- sin dependencias nuevas de negocio

**Storage**: MonetDB -- `db/ddl/monetdb/14_support.sql` nuevo (8 tablas:
`categoria_ticket`, `ticket`, `ticket_mensaje`, `articulo_kb`,
`etiqueta`, `articulo_kb_etiqueta`, `changelog`, `changelog_item`) +
grants. Observabilidad NO agrega tablas (research.md Decisión 1/2).

**Testing**: `pytest` unit (dominio: transición de estado de ticket,
cálculo de `sla_objetivo_min`, lógica de error budget pura) +
integration (ciclo de vida de ticket vía `TestClient`, PN-01 cross
tenant, KB y changelog, escenario simulado de bloqueo de despliegue) +
script de compuerta probado como proceso (`subprocess`/función pura con
Prometheus mockeado) -- ver los 4 escenarios de
[quickstart.md](./quickstart.md)

**Target Platform**: Docker Compose (`prometheus`/`loki`/`grafana` ya
declarados desde S0.1); sin servicios nuevos de infraestructura

**Performance Goals**: SC-001/SC-002 -- 95 % de tickets de
severidad alta/crítica con primera respuesta dentro de SLA (< 2h
AODB/FIDS, < 4h rampa), medido en la prueba de integración por
comparación de timestamps

**Constraints**: el cálculo de uptime/error budget es *derivado*, no
persistido (research.md Decisión 1); el bloqueo de despliegue es una
compuerta de CI/script reusable, no un middleware de tráfico
(research.md Decisión 2); `role_support` lee/escribe tickets
cross-tenant vía `alcance_global()` (research.md Decisión 5),
auditado igual que cualquier otro uso de esa excepción desde S0.2

**Scale/Scope**: 1 módulo de negocio completado desde scaffold vacío
(`aerohub_support`), 1 script de compuerta nuevo (`tools/`), reglas de
alerta Prometheus nuevas (`infra/prometheus/alertas.yml`), 1 DDL nuevo,
sin cambios en `aerohub_gateway` (research.md Decisión 7 -- las rutas
de soporte no requieren licencia, ya funciona sin tocar el middleware)

## Constitution Check

*GATE: Debe cumplirse antes de Fase 0. Re-evaluado después de Fase 1.*

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE.
  `ticket` es alcance `tenant`; `ticket_mensaje` es alcance `interno`
  heredando el tenant vía `ticket_id` (mismo patrón que
  `post_mortem_accion`, S1.7); `articulo_kb`/`etiqueta`/
  `articulo_kb_etiqueta`/`changelog`/`changelog_item` son alcance
  `global` (sin `tenant_id`, igual que `catalogo.modulo`). El acceso
  cross-tenant de `role_support` usa `alcance_global()` con
  `motivo`+`rol` explícitos y auditados -- ninguna excepción implícita.
- **Principio II (Arquitectura Modular por Capas e Independencia de
  Módulos)**: CUMPLE -- `aerohub_support` sigue el mismo patrón de 4
  capas que todos los módulos anteriores; `changelog_item` redeclara
  localmente `catalogo.modulo` (patrón ya usado 4 veces desde S1.4). El
  script de compuerta de error budget vive en `tools/`, fuera de
  `services/`, porque no es lógica de negocio de ningún módulo -- es
  tooling de plataforma, misma categoría que
  `tools/lint_ddl_nomenclature.py` ya existente.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- los
  4 escenarios de `quickstart.md` se verifican contra MonetDB real en
  Docker; el escenario de bloqueo de despliegue se verifica de forma
  simulada (fixture de métricas), tal como exige explícitamente la
  compuerta de pruebas de S1.8 en el plan de implementación (no hay CD
  real contra el cual verificar un despliegue bloqueado de verdad).
- **Principio IV (Calidad Continua en Verde)**: aplica sin excepción.
- **Principio V (Aprobación Explícita Antes de Acciones Irreversibles)**:
  aplica -- diff antes de commit, commit solo si el usuario lo pide.
- **Requisitos Tecnológicos y de Infraestructura**: CUMPLE -- Prometheus/
  Loki/Grafana ya corren en Docker desde S0.1; no se agrega ningún
  servicio nuevo a `docker-compose.yml`.

Sin violaciones -- no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/010-support-observability/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── support-api.md
    └── error-budget-gate.md
```

### Source Code (repository root)

```text
db/ddl/monetdb/14_support.sql                # 8 tablas nuevas de support
db/ddl/monetdb/99_grants_support.sql          # grants por rol
db/seeds/generate.py                          # categoria_ticket (seed)

services/support/aerohub_support/
├── domain/
│   ├── ticket.py                   # transiciones de estado, sla_objetivo_min
│   └── articulo_kb.py              # invariantes de versión/estado
├── infrastructure/
│   ├── tablas.py                   # Table() de las 8 tablas propias
│   ├── alcances.py                 # registrar_alcance G1 por tabla
│   ├── consultas.py
│   └── comandos.py
├── application/
│   ├── gestionar_tickets.py        # crear, responder, cambiar estado
│   ├── gestionar_kb.py             # publicar/buscar articulo_kb
│   └── gestionar_changelog.py
└── api/router.py                   # prefix "/support"

infra/prometheus/alertas.yml         # reglas Sev1-Sev3 nuevas
infra/prometheus/prometheus.yml      # + rule_files apuntando a alertas.yml

tools/verificar_error_budget.py      # compuerta de bloqueo de despliegue

services/gateway/main.py             # + include_router(router_support)

tests/unit/support/
tests/integration/test_ticket_sla.py
tests/integration/test_kb_changelog.py
tests/integration/test_error_budget_gate.py
tests/negative/test_pn01_tickets_cross_tenant.py
```

**Structure Decision**: `aerohub_support` sigue el mismo patrón de 4
capas que `aerohub_billing`/`aerohub_compliance` (S1.6/S1.7) sin
variación. La observabilidad es la única pieza que vive fuera de un
módulo de negocio (`tools/` + configuración de Prometheus), justificado
en research.md Decisiones 1-3 -- no hay lógica de negocio ni datos de
tenant involucrados, por lo que forzarla dentro de `services/support/`
sería un falso acoplamiento.

## Complexity Tracking

Sin violaciones que justificar.
