# Implementation Plan: S1.7 -- Licenciamiento, credenciales y Compliance Hub

**Branch**: `main` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-compliance-licensing-hub/spec.md`

## Summary

Cierra el control de acceso por licencia (RF-O18/CU-O20) como middleware
transversal en `aerohub_gateway` -- mismo punto de intercepción que ya usa
el rate limiting -- y construye `aerohub_compliance` desde cero (hoy solo
scaffold vacío) con las 9 tablas nuevas del esquema `compliance` (8 de
ellas append-only, `post_mortem`/`post_mortem_accion` con la única
excepción de mutabilidad del esquema, exclusiva `role_sre`, ADR-009).
Extiende `aerohub_tenancy` con `rotar_api_key` (RF-O12, acotado a API
Keys). `compliance.log_auditoria` y `tenants.licencia`/`tenants.api_key`
ya existen desde S0.2/S1.2 -- este sprint no los recrea.

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22 (sin vista nueva
planificada -- ver Assumptions de spec.md, este sprint es
predominantemente backend/plataforma)

**Primary Dependencies**: FastAPI, SQLAlchemy Core -- sin dependencias
nuevas de negocio

**Storage**: MonetDB -- `db/ddl/monetdb/13_compliance_hub.sql` nuevo (9
tablas: `tipo_incidente`, `incidente_seguridad`,
`tipo_reporte_regulatorio`, `reporte_dgac`, `acceso_auditor`,
`post_mortem`, `post_mortem_accion`, `control_soc2`, `evidencia_soc2`) +
seeds de `catalogo.modulo` (sin filas hasta ahora) y catálogos de
`compliance`

**Testing**: `pytest` unit (dominio: transición de post-mortem, validación
de remediación completa) + integration (PN-09 vía `TestClient`, ciclo de
post-mortem con rol correcto/incorrecto, rotación de API Key auditada) +
análisis estático nuevo (PN-04 reforzada, mismo patrón que PN-15) -- ver
los 4 escenarios de [quickstart.md](./quickstart.md)

**Target Platform**: Docker Compose, sin servicios nuevos de
infraestructura

**Performance Goals**: SC-002 -- post-mortem publicable en < 72h desde
`iniciado_en`, medido explícitamente en la prueba de integración
(comparación de timestamps, no un límite de infraestructura)

**Constraints**: la excepción de mutabilidad de `post_mortem` es exclusiva
de `role_sre`, aplicada en `application/` (MonetDB no tiene RLS, mismo
patrón que el mínimo privilegio de `role_ramp_agent` en S1.5); el mapeo
endpoint→módulo licenciable es un diccionario estático en
`aerohub_gateway`, no metadata en cada router (ver research.md Decisión 2)

**Scale/Scope**: 1 módulo de negocio completado desde scaffold vacío
(`aerohub_compliance`), 1 módulo extendido (`aerohub_tenancy` +
`rotar_api_key`), 1 middleware nuevo en `aerohub_gateway`, 1 DDL nuevo,
seeds de `catalogo.modulo` (primera vez que se siembra)

## Constitution Check

*GATE: Debe cumplirse antes de Fase 0. Re-evaluado después de Fase 1.*

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE.
  `incidente_seguridad`/`reporte_dgac`/`acceso_auditor` son alcance
  `tenant`; `post_mortem`/`evidencia_soc2` son alcance `tenant` con
  `tenant_id` NULLABLE para incidentes/evidencia de plataforma sin tenant
  específico, vía `alcance_global()` (ADR-019 G3) -- mismo patrón ya
  usado por el monitor de señal FIDS (S1.3). Extiende el principio con un
  caso nuevo: verificación de licencia como control de PLATAFORMA (no de
  tenant ni de rol) aplicado antes de que la petición llegue a cualquier
  módulo de negocio.
- **Principio II (Arquitectura Modular por Capas e Independencia de
  Módulos)**: CUMPLE -- la verificación de licencia vive en
  `aerohub_gateway` precisamente para NO obligar a que importe
  `aerohub_compliance` (ver research.md Decisión 1); `aerohub_compliance`
  se construye con el mismo patrón de capas que todos los módulos
  anteriores.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- los 4
  escenarios de `quickstart.md` se verifican contra MonetDB real en
  Docker; la ausencia de métodos de mutación (PN-04 reforzada) se
  verifica por análisis estático real del código fuente, no se asume.
- **Principio IV (Calidad Continua en Verde)**: aplica sin excepción.
- **Principio V (Aprobación Explícita Antes de Acciones Irreversibles)**:
  aplica -- diff antes de commit, commit solo si el usuario lo pide.
- **Requisitos Tecnológicos y de Infraestructura**: CUMPLE -- todo
  servicio de verificación corre en Docker.

Sin violaciones -- no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/009-compliance-licensing-hub/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── compliance-api.md
    └── licensing-and-api-keys.md
```

### Source Code (repository root)

```text
db/ddl/monetdb/13_compliance_hub.sql       # 9 tablas nuevas de compliance
db/ddl/monetdb/99_grants_compliance_hub.sql # grants por rol
db/seeds/generate.py                        # catalogo.modulo (primera vez),
                                              # tipo_incidente, tipo_reporte_regulatorio,
                                              # control_soc2

services/compliance/aerohub_compliance/
├── domain/
│   ├── incidente_seguridad.py
│   ├── post_mortem.py            # validar_puede_publicar(), transiciones
│   └── reporte_dgac.py
├── infrastructure/
│   ├── tablas.py                  # Table() de las 9 tablas propias
│   ├── consultas.py
│   └── comandos.py                 # SOLO insertar_* salvo post_mortem
├── application/
│   ├── gestionar_incidentes.py
│   ├── gestionar_post_mortem.py    # exclusivo role_sre
│   ├── gestionar_reportes.py
│   └── gestionar_evidencia_soc2.py
└── api/router.py                   # prefix "/compliance"

services/tenancy/aerohub_tenancy/application/gestionar_api_key.py
                                     # + rotar_api_key() nuevo
services/tenancy/aerohub_tenancy/infrastructure/comandos_api_key.py
                                     # + rotar_api_key() (infra)
services/tenancy/aerohub_tenancy/api/router.py
                                     # + POST /tenants/api-keys/{id}/rotar

services/gateway/aerohub_gateway/
├── domain/licencia.py               # PREFIJO_A_CODIGO_MODULO, LicenciaInvalida
├── application/verificar_licencia.py
├── infrastructure/licencia.py        # Table() local de tenants.licencia
└── api/middleware.py                 # + verificacion de licencia tras autenticar

tests/negative/test_pn04_compliance_append_only.py  # analisis estatico, nuevo
tests/negative/test_pn09_licenciamiento.py            # nuevo
tests/unit/compliance/
tests/integration/test_compliance_post_mortem.py
tests/integration/test_licenciamiento.py
tests/integration/test_rotar_api_key.py
```

**Structure Decision**: `aerohub_compliance` sigue el mismo patrón de 4
capas que `aerohub_billing`/`aerohub_passenger` (S1.6) sin variación. La
verificación de licencia es la única pieza que vive fuera de un módulo de
negocio (en `aerohub_gateway`), justificado en research.md Decisión 1 --
no es una excepción al patrón, es la aplicación correcta de "controles
transversales de enrutamiento viven en el Gateway", ya establecida por el
rate limiting de S1.2.

## Complexity Tracking

Sin violaciones que justificar.
