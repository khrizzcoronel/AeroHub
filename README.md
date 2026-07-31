# AeroHub

Plataforma SaaS multi-tenant de gestión operativa, comercial y analítica para aeropuertos medianos y grandes en Latinoamérica.

## Documentación normativa vigente

| Documento | Identificador | Descripción |
|:---|:---|:---|
| [SRS v2.0](docs/srs/AEROHUB-SRS-001-v2.0.md) | AEROHUB-SRS-001 | Especificación de Requisitos (ISO/IEC/IEEE 29148:2018) |
| [SDD — Modelo operacional](docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md) | AEROHUB-SDD-DATA-001 | Diseño de la base MonetDB (IEEE 1016) |
| [SDD — Modelo analítico](docs/sdd/AEROHUB-SDD-DATA-002-ClickHouse-v1.0.md) | AEROHUB-SDD-DATA-002 | Diseño de `ah_tactico` y `ah_estrategico` |
| [Análisis Estratégico v6.0](docs/estrategia/AEROHUB-ANALISIS-ESTRATEGICO-v6.0.md) | — | Objetivos, BSC, RBAC, ADR y plan de acción |
| [Plan de Implementación v2.0](docs/PLAN_IMPLEMENTACION_v2.0.md) | AEROHUB-PLAN-002 | 5 fases · 24 sprints · trazabilidad requisito → sprint |
| [Decisiones arquitectónicas](docs/adr/) | ADR-017…019 | Arquitectura, continuidad y guardián de tenant |

> Toda versión anterior de estos documentos y todo artefacto de código derivado de ellas fue **eliminado** del repositorio el 2026-07-30. La SRS v2.0 invalida expresamente cualquier diseño basado en PostgreSQL/RLS; conservarlos como referencia histórica solo habilitaba que una consulta futura tomara por vigente una premisa caída.

## Arquitectura

Módulos de dominio con capas internas ([ADR-017](docs/adr/ADR-017-arquitectura-modular-por-capas.md)):

```
apps/       presentación    Angular 20+ (portal, tableros Z y F, FIDS players)
services/   backend         Gateway + un módulo por bounded context
                            (api/ application/ domain/ infrastructure/)
packages/   transversal     repository (ÚNICO emisor de SQL), contracts, kernel
pipelines/  ETL             Airflow: bronce → plata → oro → ClickHouse
ml/         modelos         XGBoost + SHAP, MLflow, Evidently
db/         datos           DDL MonetDB y ClickHouse, migraciones, seeds
infra/      infraestructura docker-compose, Prometheus, Loki, Grafana, MinIO
tests/      verificación    unit · integration · e2e · negative (PN-01…PN-15) · cross_tenant
```

**No hay capa BFF**: fue retirada en v4.0 (Next.js → API Gateway FastAPI + Angular único, SRS §6.4). Reintroducirla exigiría un ADR que revierta esa decisión y duplicaría el punto de inyección de `tenant_id`, que es justamente el control que sustituye al RLS perdido.

## Principios rectores

| # | Principio |
|:---|:---|
| P1 | Ningún componente fuera de `packages/repository` emite SQL hacia MonetDB (PN-15) |
| P2 | El `tenant_id` proviene del token JWT; toda consulta sin filtro se **aborta en ejecución** ([ADR-019](docs/adr/ADR-019-guardian-de-tenant-fail-closed.md)) |
| P3 | `ah_estrategico` solo se deriva de `ah_tactico`, con reconciliación de tolerancia cero |
| P4 | Capa (bronce/plata/oro) y estado de ejecución son dimensiones ortogonales |
| P5 | Sin `DELETE` físico; `compliance` append-only salvo la excepción de `post_mortem` |
| P6 | Cero PII de pasajeros en cualquier capa (PN-11) |
| P7 | Toda decisión estructural exige ADR aprobado antes de implementarse |
| P8 | Toda mutación se registra en el journal de continuidad en la misma transacción ([ADR-018](docs/adr/ADR-018-continuidad-operacional-monetdb.md)) |

## Verificación

Cada sprint reserva sus dos últimos días a la **compuerta de pruebas** (Plan §6.4): unitarias, integración, pruebas negativas nuevas, **regresión de todas las PN anteriores**, contrato de API, reglas de arquitectura y suite cruzada por tenant. La evidencia se archiva en `docs/evidencia/<sprint>/`. Un módulo entregado sin su prueba no cuenta como entregado.

## Estado

Fase 0 — Fundación y aislamiento verificable (Sprint S0.1).

## Riesgos declarados

Dos riesgos tienen mecanismo asignado pero **no se declaran cerrados**, por mandato explícito de las fuentes:

- **RNF-R01 (continuidad):** MonetDB carece de PITR nativo. ADR-018 define el mecanismo (journal transaccional, snapshot, standby caliente, failover por DSN); el cierre exige 4 semanas consecutivas de prueba de restauración en verde más un game day con failover real.
- **Riesgo residual de aislamiento (SRS §9.4):** ADR-019 lo convierte en *fail-closed* y reduce su superficie a tres causas enumerables, pero la SRS exige que permanezca visible en toda revisión de seguridad y **no se presente como mitigado**.
