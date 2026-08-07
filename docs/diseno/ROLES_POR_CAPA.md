# Roles por capa (operativa / táctica / estratégica / plataforma)

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-06 |
| **Propósito** | Clasificar los 16 roles del sistema según la capa de negocio que operan, usando la misma taxonomía que ya define `docs/PLAN_IMPLEMENTACION_v3.0.md` (Fase 1 = capa operativa RF-O\*, Fase 2 = capa táctica RF-T\*, Fase 3 = capa estratégica RF-E\*), más una capa de plataforma para los roles que administran el sistema mismo en vez de el negocio de un tenant. |
| **Fuente de verdad** | `packages/contracts/aerohub_contracts/roles_modulos.py` -- este documento no inventa nada, resume el mapeo rol→módulos→scopes que el código ya decide. |
| **Relacionado** | `docs/diseno/WORKPANEL_Y_DASHBOARD_ROLES.md` (qué ve cada rol en `apps/web`, con el detalle de `role_platform_admin`/`role_tenant_admin`). |

---

## Por qué esta clasificación, no otra

El propio plan del proyecto ya divide el trabajo en tres capas de requisitos funcionales -- operativa (RF-O, Fase 1), táctica (RF-T, Fase 2) y estratégica (RF-E, Fase 3) -- según el horizonte de la pregunta que resuelven, no según la complejidad de la consulta (`docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.0). Los roles se alinean naturalmente a esa misma división: un rol que **opera** el día a día vive en la capa operativa; uno que **analiza tendencias** vive en la táctica; uno que **audita/gobierna** el sistema como un todo vive en la estratégica. Los roles que administran la plataforma misma (tenants, usuarios, soporte) no encajan en ninguna de las tres -- son meta-nivel, se agrupan aparte.

---

## Capa operativa (día a día, MonetDB, tenant-scoped -- RF-O\*)

Ejecutan o registran la operación del momento, dentro de un tenant.

| Rol | Alcance | Módulos | Qué opera |
|:---|:---|:---|:---|
| `role_tenant_admin` | tenant | M1-M9 excepto M7/M8 | Administra (casi) todo el negocio operativo de su tenant |
| `role_operations_controller` | tenant | M1 AODB, M3 Gates, M4 Rampa | Vuelos, asignación de puertas, turnaround |
| `role_ramp_agent` | tenant | M4 Rampa | Solo sus propias tareas de rampa (mínimo privilegio) |
| `role_airline_coordinator` | tenant | M1 AODB, M6 Pasajeros | Coordina una aerolínea puntual |
| `role_billing_officer` | tenant | M5 Billing | Facturación y cargos |

---

## Capa táctica (análisis, tendencias, M7/ClickHouse -- RF-T\*)

Leen o construyen la capa analítica; no operan el día a día.

| Rol | Alcance | Módulos | Qué analiza |
|:---|:---|:---|:---|
| `role_tenant_analyst` | tenant | M1, M3, M4, M5, M6 (solo lectura) | Vista analítica del propio tenant |
| `role_business_viewer` | plataforma | M5, M6, **M7** | Negocio cross-tenant |
| `role_data_engineer` | plataforma | M7 | Pipeline ETL (bronce→plata→oro) |
| `role_ml_engineer` | plataforma | M7 | Modelos predictivos |
| `role_elt_reader` | plataforma | M7 | Identidad técnica de solo lectura para el pipeline |

**Nota de estado real (2026-08-05)**: esta capa es hoy casi enteramente aspiracional. Los 4 roles de plataforma ya tienen M7 en su mapa de módulos, pero M7 recién tiene un endpoint real (`GET /analytics/tactico/{modulo}`, demo mínima sobre ClickHouse -- ver `services/analytics_api/`) construido fuera de sprint para un dashboard puntual. La ingesta medallion completa que le daría contenido de verdad a estos 4 roles llega en la Fase 2 (S2.1-S2.4), todavía no arrancada -- ver `docs/PLAN_IMPLEMENTACION_v3.0.md` §9.

---

## Capa estratégica / gobierno (cumplimiento, auditoría, confiabilidad -- RF-E\*)

Supervisan el sistema como un todo, no un tenant operando.

| Rol | Alcance | Módulos | Qué gobierna |
|:---|:---|:---|:---|
| `role_regulatory_auditor` | tenant | M9 Compliance (solo lectura) | Auditoría regulatoria de un tenant |
| `role_sre` | plataforma | M7, M8, M9 | Observabilidad + compliance cross-tenant |

---

## Capa de plataforma (meta-nivel -- no son capas RF, administran el sistema mismo)

Sin scopes de negocio de un tenant; operan sobre tenants/usuarios/soporte, no sobre vuelos/puertas/facturas.

| Rol | Alcance | Módulos | Qué administra |
|:---|:---|:---|:---|
| `role_platform_admin` | plataforma | ninguno (`tenants:*`, `api-keys:*`, `usuarios:*`) | Tenants, API Keys, usuarios -- sin tenant propio |
| `role_support` | plataforma | M8, M9 | D6 Soporte/DevRel (tickets, KB, changelog) |
| `role_implementation` | plataforma | M1, M3, M4, M5, M6 | Onboarding de tenants nuevos |
| `role_people_viewer` | plataforma | ninguno | Talento/RRHH (sin scopes de negocio) |

---

## Tabla resumen (los 16 roles, un vistazo)

| Rol | Capa | Alcance |
|:---|:---|:---|
| `role_tenant_admin` | Operativa | tenant |
| `role_operations_controller` | Operativa | tenant |
| `role_ramp_agent` | Operativa | tenant |
| `role_airline_coordinator` | Operativa | tenant |
| `role_billing_officer` | Operativa | tenant |
| `role_tenant_analyst` | Táctica | tenant |
| `role_business_viewer` | Táctica | plataforma |
| `role_data_engineer` | Táctica | plataforma |
| `role_ml_engineer` | Táctica | plataforma |
| `role_elt_reader` | Táctica | plataforma |
| `role_regulatory_auditor` | Estratégica | tenant |
| `role_sre` | Estratégica | plataforma |
| `role_platform_admin` | Plataforma | plataforma |
| `role_support` | Plataforma | plataforma |
| `role_implementation` | Plataforma | plataforma |
| `role_people_viewer` | Plataforma | plataforma |
