# Plan — Corrección de módulos y dashboard operativo para los roles restantes

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-07 |
| **Estado** | **§2.1 (dashboard `role_sre`/`role_regulatory_auditor`) y §2.3 (comprensibilidad, 4 vistas) implementados y verificados (2026-08-07).** §2.2 (`role_tenant_analyst`/`role_business_viewer`) sigue en pausa, pendiente de que el usuario elija (a) o (b). Detalle completo del pase en `CLAUDE.md`. |
| **Origen** | Pedido directo del usuario: aplicar lo hecho en `PLAN_CORRECCION_MODULOS.md` (comprensibilidad) y `PLAN_DASHBOARDS_OPERATIVOS.md` (dashboard con gráfico) a los módulos/roles que ambos planes dejaron fuera, **respetando los permisos reales de cada rol** -- no solo el scope de aplicación, también el `GRANT` de motor (causa raíz A del checklist de `CLAUDE.md`). |
| **Relacionado** | `docs/diseno/ROLES_POR_CAPA.md`, `docs/diseno/PLAN_CORRECCION_MODULOS.md` (cerrado, Fases 1-6), `docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md` (implementado), `docs/diseno/WORKPANEL_Y_DASHBOARD_ROLES.md` |

---

## 0. Por qué queda trabajo pendiente

Ambos planes anteriores se acotaron **a propósito** a la capa operativa (5 roles: `role_tenant_admin`, `role_operations_controller`, `role_ramp_agent`, `role_airline_coordinator`, `role_billing_officer`) más una extensión puntual de `role_platform_admin` (para no dejarlo sin dashboard de la nada). Eso deja **2 huecos reales**, no uno:

1. **Comprensibilidad (items 13/17 de `PLAN_CORRECCION_MODULOS.md`)** nunca se aplicó a M2 FIDS, M9 Compliance, ni a las 4 vistas de plataforma (Tenants/Usuarios/API-Keys/Licencias) -- documentado como pendiente explícito en `CLAUDE.md` y en el propio plan.
2. **Dashboard operativo** solo cubre 6 de los 16 roles del sistema. Los otros 10 quedaron fuera por decisión explícita del plan (§7, "capas táctica/estratégica/plataforma quedan fuera hasta nuevo aviso"), pero **no todos por la misma razón** -- algunos tienen acceso real y otros no, y eso hay que verificarlo rol por rol antes de prometerles un dashboard que va a devolver 403 en cada sección.

Este plan hace exactamente esa verificación (igual método que el resto de la sesión: `grep` de `roles_modulos.py` para el scope de aplicación, `grep` de `db/ddl/monetdb/9*_grants_*.sql` para el `GRANT` real de motor) antes de proponer nada.

---

## 1. Matriz de permisos reales de los 10 roles restantes

| Rol | Capa (`ROLES_POR_CAPA.md`) | Scope de aplicación relevante | `GRANT` de motor verificado | ¿Puede tener un dashboard/vista que funcione hoy? |
|:---|:---|:---|:---|:---:|
| `role_sre` | Estratégica | `compliance:leer/escribir`, `support:leer/escribir` | `GRANT SELECT ON compliance.log_auditoria TO role_sre` (`93_grants_compliance.sql:25`) -- **sí tiene** | ✅ Sí (Compliance) |
| `role_regulatory_auditor` | Estratégica | `compliance:leer` | `GRANT SELECT ON compliance.log_auditoria TO role_regulatory_auditor` (`93_grants_compliance.sql:27`) -- **sí tiene** | ✅ Sí (Compliance) |
| `role_tenant_analyst` | Táctica | `vuelos:leer`, `puertas:leer`, `rampa:leer`, `billing:leer`, `passenger:leer` | **Sin GRANT** sobre `ops.*`, `rampa.*` ni `billing.*` -- la matriz 4.3.1 lo marca `'-'` explícitamente (`96_grants_ops.sql:26-27`, `97_grants_rampa.sql:8-9`); tampoco hay grant de `billing.*` a este rol | ❌ No -- cualquier sección devolvería 403 |
| `role_business_viewer` | Táctica | `billing:leer` | Mismo hallazgo: sin `GRANT` sobre `billing.*` (solo tiene `tenants.okr`/`okr_resultado_clave` y `support.*`, sin informe que los use) | ❌ No |
| `role_data_engineer` | Táctica | ninguno de negocio (solo M7) | -- | ❌ No aplica (sin scope de negocio) |
| `role_ml_engineer` | Táctica | ninguno de negocio (solo M7) | -- | ❌ No aplica |
| `role_elt_reader` | Táctica | ninguno de negocio (solo M7) | -- | ❌ No aplica |
| `role_support` | Plataforma | `support:leer/escribir` | Ya tiene vista propia (`soporte/panel-soporte`, no el mecanismo de dashboard) | N/A -- ya resuelto, ver §3 |
| `role_implementation` | Plataforma | `tenants:crear` (herramienta de onboarding, sin vista propia) | -- | ❌ No aplica (rol técnico/temporal, sin UI) |
| `role_people_viewer` | Plataforma | ninguno | -- | ❌ No aplica |

**Hallazgo central**: `role_tenant_analyst` y `role_business_viewer` tienen scope de **aplicación** de lectura sobre varios módulos, pero **cero `GRANT` de motor** real -- es la causa raíz A del checklist, pero aquí **no es un bug a corregir**, es una decisión de la matriz 4.3.1 documentada explícitamente en los propios archivos de grants ("sin acceso a ops", "sin acceso a rampa"). Construirles un dashboard hoy sería repetir el error que ese mismo checklist existe para evitar: prometer una pantalla que el motor va a rechazar.

---

## 2. Qué se propone

### 2.1 Dashboard operativo -- 2 roles nuevos, mecanismo ya existente

`role_sre` y `role_regulatory_auditor` son los únicos 2 de los 10 con acceso de motor real y verificado (Compliance Hub, `compliance.log_auditoria`). Se les agrega una entrada en `DASHBOARDS_POR_ROL` (`apps/web/src/app/informes/informes-config.ts`), reusando `CONFIG_INFORME_COMPLIANCE` (que ya tiene `campoAgrupacion: 'tabla'` agregado en el pase anterior) y el mismo mecanismo de gráfico + "Ver detalle" que el resto de roles:

| Rol | Pregunta de jornada | Sección | KPI propuestos |
|:---|:---|:---|:---|
| `role_sre` | "¿Qué actividad de auditoría requiere atención?" | Compliance Hub | Eventos del período, Inserciones, Actualizaciones |
| `role_regulatory_auditor` | "¿Qué eventos de auditoría se registraron?" | Compliance Hub | Eventos del período, Inserciones, Actualizaciones |

Sin cambio de backend, sin cambio de `GRANT` -- ambos ya pueden leer `GET /compliance/informes/simple` hoy. `shell.ts::puedeVerInformes` ya deriva el enlace de `DASHBOARDS_POR_ROL`, así que agregar la entrada alcanza para que el enlace "Dashboard" les aparezca solo.

### 2.2 `role_tenant_analyst` / `role_business_viewer` -- decisión explícita, no implementación silenciosa

No se les construye dashboard en este pase. Dos caminos posibles, mutuamente excluyentes:

- **(a) Dejarlos fuera, documentado** (recomendado): son roles de la capa táctica, que el propio `PLAN_DASHBOARDS_OPERATIVOS.md` ya declaró fuera de alcance hasta que exista contenido real (Fase 2/S2.4, `ah_tactico`). Abrirles `GRANT`s de motor ahora sería adelantar esa fase por la puerta de atrás, sin la capa analítica que le da sentido a su rol.
- **(b) Otorgarles el `GRANT` de motor que la matriz 4.3.1 ya les niega a propósito** -- esto es un cambio de modelo de seguridad, no un bug, y no se toma sin aprobación explícita.

Se recomienda (a). Si el usuario prefiere (b), hace falta decidir primero *qué* tablas exactamente (¿todo `ops`/`rampa`/`billing` en modo solo-lectura, o un subconjunto?) antes de tocar los archivos de grants.

### 2.3 Comprensibilidad (items 13/17) -- 4 vistas pendientes

Mismo patrón ya aplicado en Fase 5 (`CLAUDE.md`, "Item 13/17"): una oración de apertura + KPI en vivo sobre datos ya cargados, y estados vacíos con CTA condicionado a `puedeEscribir()`/scope real. Se aplica a las 4 vistas que quedaron fuera:

| Vista | Rol(es) que la usan | KPI propuesto |
|:---|:---|:---|
| `compliance/panel-compliance` (M9) | `role_tenant_admin`, `role_sre` | Incidentes abiertos, post-mortems sin publicar |
| `fids/pantalla-list` (M2) | `role_tenant_admin` | Pantallas sin señal, plantillas sin pantalla asignada |
| `tenants/tenant-list` | `role_platform_admin` | Tenants en onboarding, tenants suspendidos |
| `usuarios/usuario-list` + `api-keys/api-key-list` + `licencias/licencia-list` | `role_tenant_admin` | Usuarios sin verificar, llaves por expirar, licencias por vencer |

Estas 4 vistas **no** entran al mecanismo de `DASHBOARDS_POR_ROL` (no son "una pregunta de jornada" resuelta con informes simples con filtro de período -- son catálogos de administración, mismo criterio ya usado para excluir Tenants/Usuarios/API-Keys/Licencias del dashboard). El KPI vive dentro de la propia vista, igual que ya se hizo en M1/M3/M4/M5(facturas)/D6.

### 2.4 M6 Passenger -- confirmado fuera, sin cambio

Ya excluido explícitamente por decisión D2(a) del plan anterior (sin informe simple hoy, y el endpoint de tiempos de espera no acepta rango de fechas). Este plan no lo reabre.

---

## 3. Orden de implementación propuesto

1. **§2.1 (dashboard `role_sre`/`role_regulatory_auditor`)** -- el más barato, mecanismo ya construido, cero backend nuevo, cero decisión de seguridad pendiente. Se completa lo que quedó a medias en esta misma sesión (`CONFIG_INFORME_COMPLIANCE.campoAgrupacion` ya está en el código).
2. **§2.3 (comprensibilidad, 4 vistas)** -- mismo patrón ya probado 5 veces en Fase 5, sin decisiones abiertas.
3. **§2.2 (`role_tenant_analyst`/`role_business_viewer`)** -- no se implementa hasta que el usuario elija (a) o (b).

---

## 4. Verificación planificada (antes de reportar cerrado)

Mismo checklist de `CLAUDE.md` ("Antes de reportar un módulo como corregido"): `ruff`/`mypy`/`bandit`/`import-linter` sobre el repo completo, build de producción de `apps/web`, y verificación en navegador real con **login real** de `role_sre`/`role_regulatory_auditor` (no hay credencial demo sembrada todavía para estos 2 -- hay que crearla con `tools/crear_usuarios_demo_roles.py`, que hoy solo cubre los 5 roles operativos + `role_tenant_admin`).
