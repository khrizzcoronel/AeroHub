# Implementation Plan: M5 Revenue & Billing + M6 Passenger Experience

**Branch**: `main` | **Date**: 2026-08-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-billing-passenger-experience/spec.md`

## Summary

Dos módulos de negocio nuevos, `services/billing` (M5) y
`services/passenger` (M6), sobre el esquema SQL `billing` ya especificado
en `docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md` §9. El motor de
facturación (CU-O17) calcula `cargo_aeronautico` como instantánea
inmutable a partir del `tarifario` vigente y los agrupa en `factura`;
`role_billing_officer` solo revisa/disputa, nunca crea cargos a mano
(segregación de funciones, `role_support` sin acceso). La estimación de
tiempos de espera (CU-O19, M6) agrega `ops.asignacion_puerta` +
`rampa.turnaround` en `billing.tiempo_espera_agregado`, sin ningún campo
de PII (PN-11), con frescura <= 15 min (RF-O17). Ambos módulos siguen el
patrón `domain/application/infrastructure/api` ya establecido en
S1.4/S1.5, con independencia verificada por `.importlinter` a pesar de
compartir el esquema SQL `billing` (ver research.md Decisión 3).

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22

**Primary Dependencies**: FastAPI, SQLAlchemy Core -- sin dependencias
nuevas de negocio (a diferencia de S1.3/S1.4 que agregaron
`prometheus-client`/`pulp`; este sprint no requiere solver ni
instrumentación adicional)

**Storage**: MonetDB -- esquema `billing` completo (`concepto_cargo`,
`tarifario`, `tarifario_concepto`, `cargo_aeronautico`, `factura`,
`factura_linea`, `conciliacion_pax`, `tiempo_espera_agregado`),
`db/ddl/monetdb/12_billing.sql` nuevo, transcrito fielmente del SDD §9

**Testing**: `pytest` unit (dominio: cálculo de cargos, derivación de
`total`/`diferencia`, validación de `tarifario` vigente único) +
integration (inmutabilidad tras cambio de tarifa, conciliación
diferencia-cero, PN-11 sobre `tiempo_espera_agregado`, segregación de
funciones `role_support`, frescura <= 15 min) vía `TestClient` contra
MonetDB real en Docker -- ver los 5 escenarios de
[quickstart.md](./quickstart.md)

**Target Platform**: Docker Compose (gateway + web + fids-player +
MonetDB), sin servicios nuevos de infraestructura -- no se introduce
scheduler/cron (ver research.md Decisión 1/2)

**Performance Goals**: RF-O17 -- frescura de `tiempo_espera_agregado` <=
15 minutos desde el recálculo hasta la lectura

**Constraints**: `tarifa_aplicada`/`monto_calculado` en
`cargo_aeronautico` y `precio_unitario`/`monto` en `factura_linea` son
denormalizaciones deliberadas que NUNCA se recalculan (integridad
financiera, ISO/IEC 27002 8.15); `role_support` sin ningún alcance sobre
`billing` (matriz de privilegios, celda `—`); 0 columnas de PII en
`tiempo_espera_agregado` (PN-11/RNF-S05)

**Scale/Scope**: 2 módulos de negocio nuevos (`services/billing`,
`services/passenger`), 1 DDL nuevo (`12_billing.sql` + grants), 2
routers HTTP montados en el Gateway, 1 vista Angular nueva
(revisión/disputa de facturas para `role_billing_officer`, diseñada con
el skill `frontend-design` per `CLAUDE.md`)

## Constitution Check

*GATE: Debe cumplirse antes de Fase 0. Re-evaluado después de Fase 1.*

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE.
  `tarifario`/`cargo_aeronautico`/`factura`/`conciliacion_pax`/
  `tiempo_espera_agregado` son alcance `tenant`, con `tenant_id` siempre
  de `contexto_tenant_id()`. `concepto_cargo` es alcance `global`
  (catálogo, sin `tenant_id`) -- única excepción nominal, coherente con
  el patrón ya usado para catálogos (`TIPOS_TAREA` en S1.5). Extiende el
  principio con una prueba negativa explícita nueva: `role_support` sin
  ningún alcance registrado sobre `billing` (segregación de funciones,
  no solo aislamiento entre tenants).
- **Principio II (Arquitectura Modular por Capas e Independencia de
  Módulos)**: CUMPLE, con un caso nuevo -- `aerohub_passenger` escribe en
  una tabla (`billing.tiempo_espera_agregado`) cuyo esquema SQL lleva el
  nombre de OTRO módulo (`aerohub_billing`). Resuelto con el mismo patrón
  ya usado para `ops.vuelo` desde `aerohub_gates`/`aerohub_ramp`:
  `aerohub_passenger` redeclara localmente su propia `Table()` para
  `billing.tiempo_espera_agregado` (nunca importa `aerohub_billing`), y
  `aerohub_billing` nunca importa ni expone esta tabla. Verificado por
  `.importlinter`.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- los 5
  escenarios de `quickstart.md` (inmutabilidad, conciliación
  diferencia-cero, PN-11, segregación de funciones, frescura) se
  verifican contra MonetDB real en Docker antes de cerrar el sprint, no
  solo con mocks/tests unitarios.
- **Principio IV (Calidad Continua en Verde)**: aplica sin excepción --
  ruff/mypy/bandit/import-linter/pytest en verde antes de reportar
  cualquier tarea completa.
- **Principio V (Aprobación Explícita Antes de Acciones Irreversibles)**:
  aplica -- diff presentado antes de cualquier commit, commit solo si el
  usuario lo pide explícitamente.
- **Requisitos Tecnológicos y de Infraestructura**: CUMPLE -- todo
  servicio de verificación corre en Docker (`infra/docker-compose.yml`),
  sin excepciones nuevas.

Sin violaciones -- no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-billing-passenger-experience/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   ├── billing-api.md    # Fase 1
│   └── passenger-api.md  # Fase 1
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por /speckit-plan)
```

### Source Code (repository root)

```text
db/ddl/monetdb/12_billing.sql          # concepto_cargo, tarifario, tarifario_concepto,
                                         # cargo_aeronautico, factura, factura_linea,
                                         # conciliacion_pax, tiempo_espera_agregado
db/ddl/monetdb/98_grants_billing.sql    # role_billing_officer, role_tenant_admin,
                                         # role_airline_coordinator, role_operations_controller,
                                         # role_platform_admin -- NUNCA role_support
db/seeds/generate.py                    # CONCEPTOS_CARGO sembrados (catálogo global)

services/billing/aerohub_billing/
├── domain/
│   ├── tarifario.py          # vigente_en(fecha), validar_unico_vigente()
│   ├── cargo_aeronautico.py  # calcular_monto(cantidad, tarifario_concepto)
│   └── factura.py            # total() derivado, transiciones de estado
├── infrastructure/
│   ├── tablas.py              # Table() de las 6 tablas de billing propias
│   └── consultas.py           # total/diferencia derivados en SELECT, filtro por rol
├── application/
│   ├── gestionar_tarifario.py
│   ├── calcular_facturacion.py  # CU-O17
│   ├── emitir_factura.py
│   ├── disputar_factura.py
│   └── conciliar_pax.py
└── api/router.py                # prefix "/billing"

services/passenger/aerohub_passenger/
├── domain/
│   └── tiempo_espera.py         # agregacion_por_franja(), descarta_por_muestra_insuficiente()
├── infrastructure/
│   └── tablas.py                 # Table() propia de billing.tiempo_espera_agregado
│                                  # (redeclarada localmente, NO importa aerohub_billing)
├── application/
│   └── recalcular_tiempos_espera.py  # CU-O19 -- lee ops.asignacion_puerta + rampa.turnaround
└── api/router.py                 # prefix "/passenger"

apps/web/src/app/billing/panel-facturas/   # revision/disputa, role_billing_officer
                                             # (skill frontend-design aplicado)
```

**Structure Decision**: dos módulos independientes en lugar de uno solo
porque M5 y M6 tienen actores, ciclos de vida y sensibilidad de datos
distintos (M5 tiene dinero real y disputas humanas; M6 es agregados
anónimos de solo-sistema) -- forzarlos a un único `services/billing` haría
más difícil verificar PN-11 y la segregación de funciones de forma
aislada. `aerohub_passenger` redeclara `Table()` para
`billing.tiempo_espera_agregado` en vez de importar `aerohub_billing`,
exactamente como `aerohub_gates`/`aerohub_ramp` redeclaran `ops.vuelo` --
mismo patrón ya verificado por `.importlinter`, sin caso nuevo real.

## Complexity Tracking

Sin violaciones que justificar.
