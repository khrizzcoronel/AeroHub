# Workpanel y dashboard de informes — `role_platform_admin` y `role_tenant_admin`

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-05, actualizado 2026-08-07 dos veces: Fase 6 de `docs/diseno/PLAN_CORRECCION_MODULOS.md` (cierre de Fases 1-5), y la implementación de `docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md` (reemplaza §2-3 completas) |
| **Propósito** | Catalogar qué ve cada rol administrativo en `apps/web`, separado por naturaleza de vista: workpanel (CRUD sobre registros) vs. informe simple (listado con filtros) vs. informe compuesto (agrupado, con subtotales y total). |
| **Fuente de verdad** | `packages/contracts/aerohub_contracts/roles_modulos.py` (scopes reales), `apps/web/src/app/shell/shell.ts` (qué enlace se muestra y por qué), `apps/web/src/app/informes/informes-config.ts` (contrato de cada informe). Este documento no inventa nada — resume lo que el código ya decide. |
| **No cubre** | `role_sre`, `role_regulatory_auditor` y demás roles operativos/técnicos (`role_operations_controller`, `role_ramp_agent`, `role_airline_coordinator`, `role_billing_officer`, etc.) — cada uno ve un subconjunto de las **vistas** de `role_tenant_admin` según sus propios scopes, no una superficie nueva. Ojo: desde la Fase 1 (2026-08-06, D1(a)) esto ya no es un subconjunto estricto de **acciones** — los 5 roles operativos de la capa operativa (`docs/diseno/ROLES_POR_CAPA.md`) tienen los scopes de escritura de M1/M3/M4/M5 que `role_tenant_admin` perdió, así que ven botones de crear/editar que `role_tenant_admin` ya no ve en esas mismas pantallas. |

---

## Por qué estos dos roles ven cosas distintas

`role_platform_admin` **no tiene tenant propio** (`tenant_id` es `NULL`) ni scopes de negocio (`vuelos:*`, `billing:*`, etc.) — administra la plataforma completa (tenants, API Keys, usuarios), no opera el día a día de un aeropuerto. `role_tenant_admin` es lo opuesto: tiene un tenant y (casi) todos los scopes de negocio de ese tenant, pero no ve nada de administración de plataforma (no puede crear tenants nuevos).

Varias vistas que técnicamente podrían mostrarse a `role_platform_admin` por scope están **excluidas a propósito** en `shell.ts` porque el backend filtra por `contexto_tenant_id()` y ese rol no tiene uno — mostrarlas produciría un 500 al primer clic. Está documentado en cada `computed()` del shell y se repite aquí donde aplica.

---

## 1. Workpanel (CRUD)

### 1.1 `role_platform_admin`

| Vista | Ruta | Qué administra | Acciones |
|:---|:---|:---|:---|
| **Tenants** | `/tenants` | Alta, edición (razón social, plan, sandbox), cambio de estado (`en_onboarding`/`activo`/`suspendido`/`dado_de_baja`), baja física permanente | Modal "Nuevo tenant" (con validación de disponibilidad en tiempo real de código/email), modal "Ver detalles" con transiciones de estado válidas, zona de peligro con borrado físico irreversible (`DELETE /tenants/{id}`) |
| **Soporte — Base de conocimiento** | `/soporte/panel` (solo esta sección) | Artículos de KB, compartidos entre tenants | Alta de artículo, búsqueda por texto/etiqueta, paginación |
| **Soporte — Changelog** | `/soporte/panel` (solo esta sección) | Publicación de changelog a todos los tenants | Alta de entrada de changelog — **único rol autorizado** (`_ROL_AUTORIZADO` en `gestionar_changelog.py`) |

**Explícitamente NO visible**, aunque el rol tenga el scope técnico:
- **Usuarios** (`usuarios:administrar` sí está en su JWT) — excluido porque `GET /usuarios` filtra por tenant y este rol no tiene uno (`ContextoTenantAusente` → 500 sin capturar).
- **API Keys** (`api-keys:administrar` sí está en su JWT) — mismo motivo.
- **Licencias** — depende de `tenant_id` presente, este rol no tiene.
- **Tarifarios/conciliación** — no tiene `billing:escribir`.
- **Soporte — Tickets** — la sección de tickets se oculta dentro del propio panel (`listar_tickets_de_tenant` también exige tenant).
- Ningún módulo M1-M9 (AODB, FIDS, Gates, Ground Ops, Billing/facturas, Compliance) — `modulosConVista` queda vacío para este rol.

### 1.2 `role_tenant_admin`

Tiene (casi) todos los módulos M1-M9 excepto M7 (ETL/Analytics) y M8 (Observability). **Desde la Fase 1 de `docs/diseno/PLAN_CORRECCION_MODULOS.md` (2026-08-06, decisión D1(a)) este rol perdió los scopes de escritura de M1/M3/M4/M5** (`vuelos:escribir`, `puertas:escribir`, `rampa:escribir`, `billing:escribir`): la matriz de roles del Análisis v6.0 §4.3.1 los reserva a los roles operativos reales (`role_operations_controller`, `role_airline_coordinator`, `role_ramp_agent`, `role_billing_officer`) — `role_tenant_admin` es *configuración* del tenant, no *operación* del día a día. El motor de MonetDB nunca le había dado el `GRANT` correspondiente de todas formas; antes de la Fase 1 eso producía un 500 opaco al primer clic, ahora la propia interfaz oculta el botón. Workpanels visibles:

| Vista | Ruta | Qué administra | Acciones |
|:---|:---|:---|:---|
| **Usuarios y Equipo** | `/usuarios` | Rol, estado (`activo`/`suspendido`/`eliminado_logicamente`) de los usuarios del propio tenant | Invitar por correo, modal "Ver detalles" con editor de rol (`<select>`) y transiciones de estado válidas |
| **API Keys e Integraciones** | `/api-keys` | Claves de API del tenant | Generar (modal con secreto en claro copiable una sola vez); **Fase 4**: Rotar/Revocar se movieron de botones de fila a un modal "Ver detalles" (sin edición — una llave no se edita) |
| **Licencias y Módulos** | `/licencias` | Solo lectura — módulos M1-M9 contratados, vigencia | **Fase 4**: modal "Ver detalles" (código de módulo, vigencia, un origen textual explicando que la otorga el plan del tenant) — sigue sin edición posible |
| **AODB — Estado de vuelos** | `/vuelos/tiempo-real` | Consulta de vuelos y su estado en tiempo real | Sin "Nuevo vuelo"/"Cambiar estado" (perdió `vuelos:escribir` en Fase 1). **Fase 5**: la conexión WebSocket ya no tiene botones "Conectar"/"Desconectar" — se conecta y reconecta sola, con un indicador de solo lectura (`.ah-punto` verde/ámbar/rojo). El botón de fila pasó de "Cambiar estado" a "Ver detalles" (GET /vuelos/{id}, resuelve aerolínea/aeronave/aeropuertos a nombre real) |
| **FIDS Management** | `/fids/pantallas` | Plantillas de contenido, pantallas físicas registradas | Alta de plantilla, alta de pantalla. **Fase 4**: plantillas ganaron "Ver detalles" (muestra el `definicion_json` real, antes solo visible al crearla); el botón de pantalla pasó de "Asignar plantilla" a "Ver detalles" con la reasignación como acción nested |
| **Terminal & Gate Manager** | `/puertas/tablero` | Consulta de ocupación de puertas | Sin asignación manual/automática ni CRUD de terminal/puerta (perdió `puertas:escribir` en Fase 1 — incluye el botón "Cancelar" de una asignación, que sí funcionaba antes de esa decisión). **Fase 4**: el botón de fila es "Ver detalles" (terminal/tipo/envergadura/pasarela + asignaciones), con "Editar" nested solo si hay `puertas:escribir` |
| **Ground Operations** | `/rampa/turnaround` | Consulta de turnarounds, tareas, incidencias | Sin "Crear turnaround"/iniciar-finalizar tarea (perdió `rampa:escribir` en Fase 1). El modal "Ver detalles" con tareas/incidencias sigue disponible en solo lectura |
| **Revenue & Billing — Facturas** | `/billing/facturas` | Consulta de facturas | Sin "Calcular facturación"/Emitir/Disputar (perdió `billing:escribir` en Fase 1). El modal "Ver detalle" con líneas de factura sigue disponible en solo lectura |
| **Tarifarios y conciliación** | `/billing/tarifarios` | Consulta de tarifarios y conciliaciones | Sin altas ni conciliar (mismo motivo). **Fase 4**: "Ver conceptos"/"Agregar concepto"/"Activar" (3 botones de fila) se consolidaron en un solo "Ver detalles". **Fase 5**: moneda pasó de texto libre a `<select>` curado; el id de vuelo de "Nueva conciliación" pasó a `<select>` poblado por `GET /vuelos` (ninguno de los dos aplica a este rol sin `billing:escribir`, pero sí a `role_billing_officer`, que ganó `vuelos:leer` para esto) |
| **Compliance Hub** | `/compliance/panel` | Incidentes, post-mortems, reportes DGAC, accesos de auditor, evidencia SOC2 | Alta de incidente, ciclo completo de post-mortem (crear/editar causa raíz/agregar y completar acciones/publicar — solo `role_sre` puede escribir en post-mortems pese a que `role_tenant_admin` ve la sección), emitir reporte DGAC, otorgar acceso de auditor, registrar evidencia SOC2. **Hallazgo pre-existente sin cambios (S1.7/S1.19)**: este rol tiene los scopes de aplicación `compliance:leer`/`escribir` pero **ningún `GRANT` de motor** sobre `compliance.*` (salvo `log_auditoria`, ver fila de Soporte) — cualquier consulta real devuelve "acceso denegado"; usar `role_sre`/`role_regulatory_auditor` para probar este módulo |
| **Soporte** | `/soporte/panel` | Tickets (con SLA), KB, changelog | Alta de ticket, cambio de estado (solo `role_support` puede transicionar), nota interna, alta de artículo KB, ver changelog (no puede publicarlo — exclusivo `role_platform_admin`). **Fase 3**: ganó `GRANT SELECT` sobre `compliance.log_auditoria` (decisión explícita del usuario) para poder leer la trazabilidad de un ticket. **Fase 5**: el detalle de ticket fusiona mensajes + transiciones de estado en una sola línea de tiempo cronológica (antes 2 listas separadas), y sugiere artículos de KB relacionados por coincidencia de etiqueta con la categoría del ticket |

**No visible para este rol**: nada de administración de plataforma (no hay ruta para crear/administrar tenants ajenos).

---

## 2. Dashboard operativo por rol (reemplaza las secciones 2-3 anteriores, 2026-08-07)

**Cambio de mecanismo**, `docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md`, implementado con las
decisiones recomendadas por defecto (D1(a)-D5(a), sin que el usuario especificara otra cosa
al pedir el inicio de la implementación). El panel `/informes/dashboard` (`DashboardInformes`)
dejó de armar una sección **por módulo visible según scope** (barrido genérico) y ahora resuelve
**una config fija por `rol_codigo`** (`DASHBOARDS_POR_ROL` en `apps/web/src/app/informes/informes-config.ts`):
cada rol responde una pregunta de jornada concreta, con KPI derivados **en el cliente** sobre las
filas ya cargadas de uno o más informes simples (`GET /<módulo>/informes/simple`, MonetDB en
vivo) — nunca una llamada a `GET /analytics/tactico/*` (ClickHouse). Período por defecto: **hoy**,
con atajos Hoy/24h/Esta semana además del selector manual.

| Rol | Pregunta que responde | Secciones (informes simples) | KPI derivados |
|:---|:---|:---|:---|
| `role_operations_controller` | ¿Cómo viene la operación del turno? | AODB, Gates, Ground Ops | Vuelos · Asignaciones · Turnarounds · Turnarounds no completados |
| `role_billing_officer` | ¿Qué facturas requieren acción? | Revenue & Billing | Emitidas · Pagadas · Vencidas · Disputadas |
| `role_airline_coordinator` | ¿Cómo van los vuelos de mi aerolínea? | AODB | Vuelos · Llegadas · Salidas |
| `role_ramp_agent` | ¿Qué tengo que hacer ahora? | Ground Ops | Turnarounds · En curso · Interrumpidos |
| `role_tenant_admin` | ¿Cómo va la operación de mi tenant hoy? | AODB, Gates, Ground Ops, Billing | Vuelos · Asignaciones · Turnarounds · Facturas |
| `role_platform_admin` *(fuera del alcance formal del plan, preservado para no regresionar)* | ¿Cómo está la base de tenants? | Tenants | Tenants · Activos · Suspendidos |

**Decisiones tomadas** (recomendación por defecto del plan, D1-D5, opción "a" en las 5):
- **D1(a)** `role_ramp_agent` usa el informe de turnarounds del tenant tal cual (no se construyó
  el endpoint "mis tareas del período" que habría requerido backend nuevo).
- **D2(a)** M6 Passenger queda fuera de todos los dashboards (sin informe simple, y
  `GET /passenger/tiempos-espera` exige `terminal_id`+`fecha` puntuales, no rango).
- **D3(a)** M2 FIDS queda fuera del dashboard de `role_tenant_admin` (tiene listados pero no
  informe simple).
- **D4(a)** La infraestructura de ClickHouse (`aerohub_analytics_api`, `tools/sincronizar_analytics_demo.py`,
  `GET /<módulo>/informes/compuesto`, `GET /analytics/tactico/*`) **se conserva intacta y sin
  consumidor** en el dashboard operativo — reservada para el dashboard **táctico** real que
  llegue con la Fase 2/S2.4 (`ah_tactico`, ADR-016). Los badges "Compuesto · ClickHouse" /
  "Simple · MonetDB" y el gráfico de barras horizontales se retiraron del dashboard operativo
  (con una sola fuente de dato, distinguir el origen dejó de tener sentido).
- **D5(a)** Un solo componente (`DashboardInformes`) configurado por rol, no cinco componentes
  independientes.

**Regresión aceptada explícitamente por el propio plan** (tabla "Alcance" de
`PLAN_DASHBOARDS_OPERATIVOS.md`: *"Las capas táctica / estratégica / plataforma quedan fuera
hasta nuevo aviso"*): `role_business_viewer`, `role_tenant_analyst`, `role_regulatory_auditor` y
`role_sre` **ya no tienen entrada en `DASHBOARDS_POR_ROL`** — antes veían fragmentos del
dashboard viejo por scope (billing/vuelos-puertas-rampa-billing/compliance respectivamente), el
enlace "Dashboard" ahora no aparece para ellos (`shell.ts::puedeVerInformes` verifica
pertenencia a `DASHBOARDS_POR_ROL`, no scopes sueltos). `role_platform_admin` es la única
excepción de plataforma preservada, por decisión explícita de este pase (evitar que un cambio de
mecanismo le rompa silenciosamente lo único que ya tenía).

La regla no negociable de S1.18 (PLAN v3.0 §8-bis.0) se mantiene igual, adaptada a que ya no hay
lado compuesto en este dashboard: **ningún KPI se inventa una agregación de servidor** — es
`filas.length` o un `filter().length` sobre datos que el informe simple ya trajo, nunca una
llamada nueva.

---

## Resumen visual — quién ve qué

```text
role_platform_admin
├── Workpanel: Tenants, Soporte (KB + changelog, sin tickets)
└── Dashboard: "¿Cómo está la base de tenants?" -- Tenants (preservado
    fuera del alcance formal del plan de dashboards, ver §2)

role_tenant_admin
├── Workpanel: Usuarios, API Keys (ver detalles), Licencias (ver detalles),
│              AODB/FIDS/Gates/Ground Ops/Billing/Tarifarios en SOLO
│              LECTURA (perdió escritura en Fase 1, D1(a)), Compliance
│              Hub (bloqueado por falta de GRANT, hallazgo pre-existente),
│              Soporte (completo, incluye trazabilidad de ticket
│              ganada en Fase 3)
└── Dashboard: "¿Cómo va la operación de mi tenant hoy?" -- AODB, Gates,
    Ground Ops, Billing (union de los 4 informes operativos; M2/M6/M9/
    Tenancy quedan fuera, ver §2)

role_operations_controller / role_ramp_agent / role_airline_coordinator /
role_billing_officer (capa operativa, ver docs/diseno/ROLES_POR_CAPA.md)
├── Ven un subconjunto de las vistas de role_tenant_admin (M1/M3/M4/M5
│   según su propio scope de módulo), pero SÍ conservan la escritura que
│   role_tenant_admin perdió -- son los roles reales de operación diaria.
├── role_billing_officer ganó ademas vuelos:leer en Fase 5 (item 15) para
│   poblar el selector de vuelo de "Nueva conciliación".
└── Dashboard: cada uno con su propia pregunta de jornada (ver tabla de §2)
    -- controlador ve 3 secciones, los otros 3 ven 1 sola.

role_business_viewer / role_tenant_analyst / role_regulatory_auditor / role_sre
└── Sin Dashboard desde este pase (regresión aceptada explícitamente por
    el plan -- capas táctica/estratégica/técnica "quedan fuera hasta
    nuevo aviso", ver §2). Sus workpanels/vistas propias, si las tienen,
    no cambiaron.
```
