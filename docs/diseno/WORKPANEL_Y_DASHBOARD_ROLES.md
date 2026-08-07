# Workpanel y dashboard de informes — `role_platform_admin` y `role_tenant_admin`

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-05 |
| **Propósito** | Catalogar qué ve cada rol administrativo en `apps/web`, separado por naturaleza de vista: workpanel (CRUD sobre registros) vs. informe simple (listado con filtros) vs. informe compuesto (agrupado, con subtotales y total). |
| **Fuente de verdad** | `packages/contracts/aerohub_contracts/roles_modulos.py` (scopes reales), `apps/web/src/app/shell/shell.ts` (qué enlace se muestra y por qué), `apps/web/src/app/informes/informes-config.ts` (contrato de cada informe). Este documento no inventa nada — resume lo que el código ya decide. |
| **No cubre** | `role_sre`, `role_regulatory_auditor` y demás roles operativos/técnicos (`role_operations_controller`, `role_ramp_agent`, etc.) — cada uno ve un subconjunto de los workpanels de `role_tenant_admin` según sus propios scopes, no una superficie nueva. |

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

Tiene (casi) todos los módulos M1-M9 excepto M7 (ETL/Analytics) y M8 (Observability), y los scopes de escritura de cada uno. Workpanels visibles:

| Vista | Ruta | Qué administra | Acciones |
|:---|:---|:---|:---|
| **Usuarios y Equipo** | `/usuarios` | Rol, estado (`activo`/`suspendido`/`eliminado_logicamente`) de los usuarios del propio tenant | Invitar por correo, modal "Ver detalles" con editor de rol (`<select>`) y transiciones de estado válidas |
| **API Keys e Integraciones** | `/api-keys` | Claves de API del tenant | Generar (modal con secreto en claro copiable una sola vez), Rotar, Revocar — ambas inline por fila, sin modal de detalle (son operaciones de un paso, no edición de campos) |
| **Licencias y Módulos** | `/licencias` | Solo lectura — módulos M1-M9 contratados, vigencia | Ninguna (las licencias se otorgan al aprovisionar/actualizar el tenant, no desde aquí) |
| **AODB — Estado de vuelos** | `/vuelos/tiempo-real` | Alta de vuelo, registro de cambio de estado | Modal "Nuevo vuelo", modal "Cambiar estado" por fila, tabla en tiempo real vía WebSocket |
| **FIDS Management** | `/fids/pantallas` | Plantillas de contenido, pantallas físicas registradas | Alta de plantilla, alta de pantalla (con selects de terminal/plantilla), "Asignar plantilla" por fila |
| **Terminal & Gate Manager** | `/puertas/tablero` | Asignaciones de puerta | Asignación manual o automática (PuLP), modal "Ver asignaciones" con cancelación |
| **Ground Operations** | `/rampa/turnaround` | Turnarounds, tareas, incidencias | Modal "Crear turnaround", modal "Ver detalles" con iniciar/finalizar tarea (select de tipo de tarea desde catálogo) |
| **Revenue & Billing — Facturas** | `/billing/facturas` | Cálculo de facturación, emisión, disputa | Modal "Calcular facturación", modal "Ver detalle" con Emitir/Disputar |
| **Tarifarios y conciliación** | `/billing/tarifarios` | Tarifarios (alta, conceptos, activación), conciliación de pax | Modal "Nuevo tarifario", "Agregar concepto", "Activar" (con aviso de inmutabilidad), "Nueva conciliación", "Conciliar" |
| **Compliance Hub** | `/compliance/panel` | Incidentes, post-mortems, reportes DGAC, accesos de auditor, evidencia SOC2 | Alta de incidente, ciclo completo de post-mortem (crear/editar causa raíz/agregar y completar acciones/publicar — solo `role_sre` puede escribir en post-mortems pese a que `role_tenant_admin` ve la sección), emitir reporte DGAC, otorgar acceso de auditor, registrar evidencia SOC2 |
| **Soporte** | `/soporte/panel` | Tickets (con SLA), KB, changelog | Alta de ticket, cambio de estado (solo `role_support` puede transicionar), nota interna, alta de artículo KB, ver changelog (no puede publicarlo — exclusivo `role_platform_admin`) |

**No visible para este rol**: nada de administración de plataforma (no hay ruta para crear/administrar tenants ajenos).

---

## 2. Informes simples

Todos viven en el mismo panel `/informes/dashboard` (`DashboardInformes`) — una sección por módulo, mostrada solo si el perfil tiene el scope correspondiente. El lado **simple** consulta en vivo `GET /<módulo>/informes/simple` (MonetDB), respeta el filtro de período global del dashboard, y exporta a CSV desde el mismo endpoint.

### 2.1 `role_platform_admin`

Solo tiene el scope `tenants:administrar` de los seis que habilitan una sección — ve **únicamente**:

| Sección | Filtro | Columnas |
|:---|:---|:---|
| **Tenants** | Estado | Tenant, Código, Razón social, Plan, Estado |

### 2.2 `role_tenant_admin`

Tiene los seis scopes (`vuelos:leer`, `puertas:leer`, `rampa:leer`, `billing:leer`, `tenants:administrar`, `compliance:leer`) — ve las **seis** secciones:

| Sección | Filtros | Columnas |
|:---|:---|:---|
| **AODB** | Desde/Hasta, Aerolínea (id) | Vuelo, Fecha, Aerolínea, Número, Sentido |
| **Terminal & Gate Manager** | Desde/Hasta, Puerta (id) | Asignación, Vuelo, Puerta, Inicio, Fin, Estado |
| **Ground Operations** | Desde/Hasta, Estado | Turnaround, Vuelo llegada, Vuelo salida, Inicio previsto, Estado |
| **Revenue & Billing** | Desde/Hasta, Aerolínea (id), Estado | Factura, Aerolínea, Período desde/hasta, Moneda, Estado |
| **Tenants** | Estado | Tenant, Código, Razón social, Plan, Estado |
| **Compliance Hub** | Desde/Hasta | Evento, Esquema, Tabla, Operación, Rol, Ocurrido |

---

## 3. Informes compuestos

Mismo panel, mismas secciones — el lado **compuesto** del dashboard (gráfico de barras horizontales, badge "Compuesto · ClickHouse") NO consulta MonetDB en vivo: lee un snapshot pre-calculado en ClickHouse (`ah_tactico_demo.compuesto_informe`, sincronizado con `tools/sincronizar_analytics_demo.py`) — es una demo temporal, no reacciona al filtro de período del dashboard, y se retira cuando la Fase 2/S2.4 construya la capa analítica real (`ah_tactico`, ADR-016). El endpoint `GET /<módulo>/informes/compuesto` (MonetDB, con totales calculados en el servidor) sigue existiendo y es lo que ese script usa para poblar el snapshot.

### 3.1 `role_platform_admin`

| Sección | Agrupado por | Métricas | Subtotal / Total |
|:---|:---|:---|:---|
| **Tenants** | Plan × Estado | Usuarios activos, Licencias vigentes | Cantidad de tenants por grupo / total general |

### 3.2 `role_tenant_admin`

| Sección | Agrupado por | Métricas | Subtotal / Total |
|:---|:---|:---|:---|
| **AODB** | Aerolínea | Con llegada registrada, % Puntualidad | Cantidad de vuelos / total del período |
| **Terminal & Gate Manager** | Puerta | Con conflicto (solapamiento de intervalos) | Cantidad de asignaciones / total |
| **Ground Operations** | Tipo de tarea | Completadas, Con incidencia | Cantidad de tareas / total |
| **Revenue & Billing** | Concepto de cargo | Líneas | Suma de monto facturado / total general — cierra RF-E02 |
| **Tenants** | Plan × Estado | Usuarios activos, Licencias vigentes | Cantidad de tenants / total |
| **Compliance Hub** | Tipo de reporte DGAC | *(sin métricas adicionales)* | Cantidad de reportes emitidos / total |

En todos los casos, la regla no negociable del sprint que los creó (S1.18, PLAN v3.0 §8-bis.0) sigue vigente: **ningún total se calcula en el navegador** — el subtotal y el total general vienen ya resueltos del backend (o del snapshot de ClickHouse), el frontend solo los muestra.

---

## Resumen visual — quién ve qué

```text
role_platform_admin
├── Workpanel: Tenants, Soporte (KB + changelog, sin tickets)
├── Informes simples: Tenants
└── Informes compuestos: Tenants

role_tenant_admin
├── Workpanel: Usuarios, API Keys, Licencias (solo lectura), AODB, FIDS,
│              Gates, Ground Ops, Billing/Facturas, Tarifarios,
│              Compliance Hub, Soporte (completo)
├── Informes simples: AODB, Gates, Ground Ops, Billing, Tenants, Compliance
└── Informes compuestos: AODB, Gates, Ground Ops, Billing, Tenants, Compliance
```
