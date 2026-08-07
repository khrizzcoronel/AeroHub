# Plan — Dashboards operativos por rol (solo informes simples sobre MonetDB)

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-06 |
| **Estado** | **Implementado (2026-08-07)** con las decisiones recomendadas por defecto (D1(a), D2(a), D3(a), D4(a), D5(a)), pedidas sin especificar otra cosa. Detalle en `CLAUDE.md`. Pendiente de commit. |
| **Propósito** | Reemplazar el dashboard único actual (módulo-céntrico, con informes compuestos de ClickHouse) por un dashboard por rol de la **capa operativa**, alimentado exclusivamente por **informes simples sobre MonetDB**. |
| **Alcance** | Los 5 roles de la capa operativa según `docs/diseno/ROLES_POR_CAPA.md`. Las capas táctica / estratégica / plataforma quedan fuera hasta nuevo aviso. |
| **Fuente de verdad** | `packages/contracts/aerohub_contracts/roles_modulos.py` (scopes), los `@router.get("/informes/simple")` de cada servicio, `apps/web/src/app/informes/`. Este plan no inventa endpoints: lo que no existe está marcado como brecha. |

---

## 1. Por qué cambia

El dashboard actual (`apps/web/src/app/informes/dashboard-informes/`) arma sus secciones **por módulo visible según scope**, y cada sección muestra dos cosas: un informe **compuesto** (agregado por grupo, leído de ClickHouse vía `GET /analytics/tactico/{modulo}`) y un informe **simple** (consulta en vivo a MonetDB).

Eso mezcla dos capas que el propio proyecto separa a propósito:

- Un informe **compuesto** responde una pregunta de **horizonte táctico** — "¿cómo se reparte el total entre grupos?", "¿cómo viene la tendencia?". Es material de la capa táctica (RF-T\*, Fase 2, ClickHouse/`ah_tactico`).
- Un rol **operativo** (`role_operations_controller`, `role_ramp_agent`, …) no decide con eso. Decide con **qué tiene delante ahora**: qué vuelos hay hoy, qué turnaround está en curso, qué factura está vencida.

Poner subtotales por grupo en la pantalla de quien opera el turno es ruido: no cambia ninguna acción que esa persona pueda tomar en su jornada.

---

## 2. Principio de diseño

> **Un dashboard operativo muestra registros del período en curso, consultados en vivo contra MonetDB, filtrados por lo que ese rol puede accionar. Nada de agregaciones multi-grupo, nada de ClickHouse.**

Tres consecuencias directas:

1. **Fuente única: MonetDB.** Ninguna llamada a `/analytics/tactico/*` desde un dashboard operativo.
2. **Horizonte corto por defecto.** El período por defecto pasa de *últimos 30 días* a **hoy**, con atajos (Hoy / 24 h / Esta semana). Un controlador de operaciones no abre su pantalla para ver el mes pasado.
3. **Los KPI siguen existiendo, pero derivados del informe simple.** Una tarjeta "12 vuelos hoy" es `filas.length` de la consulta simple ya cargada, no una llamada a un endpoint de agregación. **Un conteo en el cliente sobre filas ya traídas no es un informe compuesto** — no agrupa en el servidor, no viaja por ClickHouse, y es exactamente lo que el rol necesita leer de un vistazo. Esta distinción es deliberada y hay que respetarla al implementar.

---

## 3. Inventario real de lo disponible (verificado 2026-08-06)

Informes simples existentes, todos `GET /<modulo>/informes/simple`, todos exigen `periodo_inicio` + `periodo_fin` obligatorios y devuelven `{parametros, generado_en, filas[]}`:

| Módulo | Ruta | Scope | Filtro extra | Columnas |
|:---|:---|:---|:---|:---|
| M1 AODB | `/vuelos/informes/simple` | `vuelos:leer` | `aerolinea_id` | vuelo, fecha, aerolínea, número, sentido |
| M3 Gates | `/puertas/informes/simple` | `puertas:leer` | `puerta_id` | asignación, vuelo, puerta, inicio, fin, estado |
| M4 Ground Ops | `/rampa/informes/simple` | `rampa:leer` | `estado` | turnaround, vuelo llegada, vuelo salida, inicio previsto, estado |
| M5 Billing | `/billing/informes/simple` | `billing:leer` | `aerolinea_id`, `estado` | factura, aerolínea, período, moneda, estado |

**Brechas confirmadas** (no hay endpoint de informe):

| Módulo | Situación | A quién afecta |
|:---|:---|:---|
| **M2 FIDS** | Sin `/informes/*`. Tiene listados propios (`/fids/plantillas`, `/fids/pantallas`). | `role_tenant_admin` |
| **M6 Passenger** | Sin `/informes/*`. Solo `GET /passenger/tiempos-espera`, que exige `terminal_id` + `fecha` (no acepta rango ni "todas las terminales"). | `role_tenant_admin`, `role_airline_coordinator` |

**Fuera de alcance por capa** (existen, pero no son operativos):

- **M9 Compliance** (`/compliance/informes/simple`) — capa estratégica. Además `role_tenant_admin` recibe `acceso denegado` por falta de `GRANT` de motor sobre `compliance.*` (hallazgo pre-existente de S1.7/S1.19). Sacarlo del dashboard operativo resuelve de paso ese error visible en pantalla, sin tocar permisos de base.
- **Tenancy** (`/tenants/informes/simple`) — capa de plataforma (`tenants:administrar`).

---

## 4. Diseño por rol

Cada dashboard responde una pregunta concreta de jornada. Los KPI son conteos derivados de las filas ya traídas (§2.3).

### 4.1 `role_operations_controller` — M1, M3, M4

*Pregunta: ¿cómo viene la operación del turno?*

| Bloque | Origen | Contenido |
|:---|:---|:---|
| KPI | derivado | Vuelos del período · Asignaciones del período · Turnarounds del período · Turnarounds no completados |
| Tabla 1 | M1 simple | Vuelos del período |
| Tabla 2 | M3 simple | Asignaciones de puerta del período |
| Tabla 3 | M4 simple | Turnarounds del período |

El rol con más superficie: los 3 informes que necesita existen.

### 4.2 `role_billing_officer` — M5

*Pregunta: ¿qué facturas requieren acción?*

| Bloque | Origen | Contenido |
|:---|:---|:---|
| KPI | derivado (por `estado`) | Emitidas · Pagadas · Vencidas · Disputadas |
| Tabla | M5 simple | Facturas del período, con filtro por estado y aerolínea |

El conteo por estado sale de agrupar en el cliente la columna `estado` que el informe simple ya devuelve.

### 4.3 `role_airline_coordinator` — M1 (+ M6 con brecha)

*Pregunta: ¿cómo van los vuelos de mi aerolínea?*

| Bloque | Origen | Contenido |
|:---|:---|:---|
| KPI | derivado | Vuelos del período · Llegadas · Salidas |
| Tabla | M1 simple | Vuelos del período, con el filtro `aerolinea_id` en primer plano |
| *(pendiente)* | M6 | Sin informe — ver §5, decisión abierta |

El filtro `aerolinea_id` del informe M1 encaja exactamente con este rol.

### 4.4 `role_ramp_agent` — M4

*Pregunta: ¿qué tengo que hacer ahora?*

| Bloque | Origen | Contenido |
|:---|:---|:---|
| KPI | derivado | Turnarounds del período · En curso · Interrumpidos |
| Tabla | M4 simple | Turnarounds del período, con filtro por estado |

**Punto a resolver antes de implementar** (§5): el informe simple de M4 lista **turnarounds del tenant**, sin filtrar por el usuario. El trabajo real de un agente son sus **tareas** (`GET /rampa/turnarounds/{id}/tareas`), donde sí aplica el mínimo privilegio de S1.5. Un dashboard fiel a este rol probablemente deba mostrar tareas, no turnarounds — pero no existe un endpoint "mis tareas del período" transversal a turnarounds.

### 4.5 `role_tenant_admin` — M1, M3, M4, M5 (operativos)

*Pregunta: ¿cómo va la operación de mi tenant hoy?*

| Bloque | Origen | Contenido |
|:---|:---|:---|
| KPI | derivado | Vuelos · Asignaciones · Turnarounds · Facturas del período |
| Tablas | M1, M3, M4, M5 simples | Una por módulo |

Es la unión de los 4 informes operativos. **No incluye M9** (capa estratégica) ni Tenancy (plataforma). M2/M6 quedan pendientes de la §5.

---

## 5. Decisiones abiertas (a resolver con el usuario antes de implementar)

| # | Decisión | Opciones |
|:---|:---|:---|
| **D1** | **Dashboard de `role_ramp_agent`**: ¿turnarounds del tenant (endpoint existente) o tareas propias (requiere endpoint nuevo `GET /rampa/tareas` con filtro de usuario y período)? | (a) Usar el informe M4 tal cual, aceptando que muestra el tenant completo · (b) Construir el endpoint de tareas propias — es trabajo de backend, no solo de UI |
| **D2** | **M6 Passenger** para `role_airline_coordinator` y `role_tenant_admin`: no hay informe y `tiempos-espera` exige `terminal_id` + `fecha` puntuales. | (a) Omitir M6 del dashboard por ahora · (b) Construir `/passenger/informes/simple` · (c) Mostrar tiempos de espera con un selector de terminal |
| **D3** | **M2 FIDS** para `role_tenant_admin`: tiene listados pero no informe. | (a) Omitir · (b) Consumir `/fids/pantallas` como tabla operativa (estado de pantallas / sin señal es dato operativo legítimo) · (c) Construir informe simple |
| **D4** | **Qué pasa con el compuesto/ClickHouse ya construido** (`aerohub_analytics_api`, `tools/sincronizar_analytics_demo.py`, contenedor ClickHouse). | (a) Se conserva intacto, sin consumidor operativo, reservado para el dashboard **táctico** que llegue con la Fase 2 · (b) Se retira ahora |
| **D5** | **Un componente o cinco.** | (a) **Sugerido**: un solo componente configurado por rol (extiende el patrón ya usado en S1.18: config declarativa + un componente) · (b) Cinco componentes independientes |

Recomendación por defecto si no se indica lo contrario: **D1(a), D2(a), D3(a), D4(a), D5(a)** — máximo valor sin abrir trabajo de backend nuevo, y sin tirar lo ya construido.

---

## 6. Tareas de implementación

### Fase 1 — Configuración por rol (frontend, sin backend)

1. `apps/web/src/app/informes/informes-config.ts`: separar la config actual en **configs de dashboard por rol** (`DASHBOARD_OPERATIONS_CONTROLLER`, `DASHBOARD_BILLING_OFFICER`, …), cada una declarando qué informes simples incluye y qué KPI derivar.
2. Quitar `moduloCodigo` / `endpointCompuesto` del camino operativo (no borrar del archivo si D4(a): el táctico los seguirá usando).
3. `dashboard-informes.ts`: resolver la config **por `rol_codigo` del perfil**, no por barrido de scopes por módulo. Mantener la carga secuencial (evita el `connection closed` de MonetDB bajo concurrencia, hallazgo de esta sesión).
4. Eliminar del componente la llamada a `obtenerInformeTactico` y el estado asociado.

### Fase 2 — Presentación

5. KPI derivados de `filas` (conteo total y conteo por columna de estado según rol).
6. Selector de período con atajos **Hoy / 24 h / Esta semana**, por defecto **Hoy**.
7. Quitar los badges de origen "Compuesto · ClickHouse" / "Simple · MonetDB": con una sola fuente pierden sentido. (Si D4(a), el badge vuelve en el dashboard táctico.)
8. Layout: KPIs arriba, tablas debajo — sin la columna de gráfico compuesto.

### Fase 3 — Menú y rutas

9. `shell.ts` / `shell.html`: el enlace "Dashboard" se muestra si el rol tiene **alguna** config operativa asignada (hoy: cualquier scope `vuelos|puertas|rampa|billing:leer`).
10. Ruta `informes/dashboard` sin cambios; solo cambia el contenido.

### Fase 4 — Verificación

11. Login real con **los 5 usuarios demo** (`controlador@`, `rampa@`, `aerolinea@`, `facturacion@`, `canario@` — todos en MEC, ver `tools/crear_usuarios_demo_roles.py`) y confirmar que cada uno ve **su** dashboard, sin errores de consola y sin `acceso denegado`.
12. `ruff` / `mypy` / `bandit` / `import-linter` en verde si se toca backend; `npx nx build web --configuration=production` en verde siempre.
13. Actualizar `CLAUDE.md` y `docs/diseno/WORKPANEL_Y_DASHBOARD_ROLES.md` (hoy describe el dashboard viejo).

---

## 7. Qué NO cubre este plan

- Dashboards de las capas táctica, estratégica y de plataforma (`role_tenant_analyst`, `role_sre`, `role_platform_admin`, …) — pendientes hasta que el usuario los pida.
- La ingesta medallion real hacia `ah_tactico` (Fase 2, S2.1-S2.4).
- El `GRANT` de motor faltante de `role_tenant_admin` sobre `compliance.*` — este plan lo **esquiva** (saca M9 del dashboard operativo), no lo arregla.
