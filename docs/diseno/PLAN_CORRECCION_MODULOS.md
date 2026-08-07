# Plan — Corrección transversal de módulos (CRUD, errores de API, comprensibilidad)

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-06 |
| **Estado** | **Plan — no implementado.** Se implementa cuando el usuario lo indique. |
| **Origen** | Revisión funcional del usuario sobre la aplicación completa (2026-08-06). |
| **Método** | Cada hallazgo de este plan fue **verificado empíricamente** contra el stack en Docker (login real por rol, `curl` contra el gateway, lectura de trazas y del DDL). Lo que no se pudo verificar está marcado como *inferido*. |
| **Relacionado** | `docs/diseno/ROLES_POR_CAPA.md`, `docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md`, `docs/diseno/DIRECCION_VISUAL.md` |

---

## 0. Resumen ejecutivo

El usuario reporta, módulo por módulo, tres síntomas: **errores de servidor**, **CRUD incompleto** y **pantallas que no se entienden**. La investigación encontró que casi todo eso se explica por **cuatro causas raíz**, no por decenas de defectos independientes:

| # | Causa raíz | Efecto que ve el usuario |
|:---|:---|:---|
| **A** | El rol con el que se prueba (`role_tenant_admin`) tiene *scopes de aplicación* de escritura que el **motor no le concede**. | HTTP **500** al crear casi cualquier cosa, en 4 de los módulos. |
| **B** | El traductor de errores de permisos solo reconoce una de las dos frases que usa MonetDB. | El fallo llega como **500 "error interno"** en vez de **403 "acceso denegado"**. |
| **C** | Los seeds no siembran datos operativos (terminales, puertas, turnarounds, facturas, pantallas). | Pantallas **vacías** → "no se entiende para qué sirve". |
| **D** | **M1 AODB no tiene endpoint de listado de vuelos** (`GET /vuelos` → 405). | La vista núcleo arranca en blanco, con botones "conectar/desconectar" sin contexto. |

Corregir A + B elimina la mayoría de los errores de servidor. C + D son la mayor parte de la sensación de "esto no se entiende". El resto es trabajo de diseño de interfaz y de estandarización del CRUD, detallado en §5-§7.

---

## 1. Causa raíz A — Scopes de aplicación ≠ GRANT de motor

El sistema autoriza en **dos capas**: el scope del JWT (`packages/contracts/.../roles_modulos.py`) y el `GRANT` real de MonetDB aplicado bajo `SET ROLE` (`db/ddl/monetdb/9*_grants_*.sql`). Cuando la primera dice que sí y la segunda que no, la petición **pasa el control de la aplicación, llega a la base y muere ahí**.

`role_tenant_admin` —el rol con el que se ha probado toda la aplicación— está en esa situación en 4 módulos:

| Módulo | Scope de aplicación | GRANT real sobre sus tablas | Resultado |
|:---|:---|:---|:---|
| M1 AODB | `vuelos:escribir` | `ops.vuelo`: SELECT, UPDATE — **sin INSERT** | `POST /vuelos` → **500** ✗ *(verificado)* |
| M3 Gates | `puertas:escribir` | `ops.asignacion_puerta`: SELECT, UPDATE — **sin INSERT** | asignar puerta → falla *(inferido del GRANT)* |
| M4 Ground Ops | `rampa:escribir` | `rampa.turnaround` / `tarea_turnaround` / `incidencia_rampa`: **solo SELECT** | crear turnaround/tarea → falla *(inferido)* |
| M5 Billing | `billing:escribir` | `billing.*`: **solo SELECT** | `POST /billing/tarifarios` → **500** ✗ *(verificado)* |
| M9 Compliance | `compliance:escribir` | solo `log_auditoria` INSERT | **403** *(ya documentado en S1.7/S1.19)* |

**Contraprueba que confirma el diagnóstico** — los roles cuyo GRANT sí coincide funcionan perfectamente sobre el mismo endpoint:

```
ops_controller   POST /vuelos              201 ✓
tenant_admin     POST /vuelos              500 ✗
billing_officer  POST /billing/tarifarios  201 ✓
tenant_admin     POST /billing/tarifarios  500 ✗
tenant_admin     POST /support/tickets     201 ✓   (aquí el GRANT sí incluye INSERT)
```

**La decisión de fondo no es técnica sino de producto**: ¿qué debe poder hacer un `role_tenant_admin`? El DDL sigue la matriz de roles del Análisis v6.0 §4.3.1, donde crear vuelos es de `role_operations_controller` / `role_airline_coordinator`, y `role_tenant_admin` es *configuración*, no operación. Si esa matriz es la correcta, **sobra el scope en la aplicación**; si se quiere que el admin del tenant opere de todo, **faltan los GRANT**. Ver decisión **D1** en §8.

---

## 2. Causa raíz B — El error de permisos se traduce a 500 en vez de 403

`services/gateway/main.py::_manejador_acceso_denegado_motor` convierte un `OperationalError` de MonetDB en un 403 limpio, **pero solo si el mensaje contiene la cadena `"access denied"`**; en cualquier otro caso relanza y termina en 500 genérico.

MonetDB usa **dos frases distintas** según la operación:

| Operación denegada | Mensaje real del motor | ¿Lo reconoce el handler? |
|:---|:---|:---|
| `SELECT` | `42000!SELECT: access denied for aerohub_app to table ...` | **Sí** → 403 ✓ |
| `INSERT` | `42000!INSERT INTO: insufficient privileges for user 'aerohub_app' to insert into table 'vuelo'` | **No** → 500 ✗ |

Por eso una lectura sin permiso responde un 403 correcto (el caso de Compliance) y una escritura sin permiso responde un 500 opaco. **Es un defecto de una línea con impacto en toda la aplicación**: aunque se resuelva la causa A, cualquier permiso faltante futuro debe fallar de forma legible.

> Corrección: reconocer también `insufficient privileges` (y considerar el resto de variantes del motor). Es la única corrección de este plan que conviene aplicar **aunque no se haga nada más**.

---

## 3. Causa raíz C — Los seeds no siembran datos operativos

Conteo real tras el reset limpio de hoy:

| Tabla | Filas |
|:---|---:|
| `ops.terminal` | **0** |
| `ops.puerta` | **0** |
| `ops.plantilla_fids` | **0** |
| `ops.pantalla_fids` | **0** |
| `rampa.turnaround` | **0** |
| `billing.factura` | **0** |
| `support.articulo_kb` | **0** |
| `ops.vuelo` | 3 |

`db/seeds/generate.py` siembra tenants, usuarios, catálogos y 2 vuelos canario — **nada más**. Terminal & Gate Manager, FIDS, Ground Operations y el panel de facturas se abren **vacíos**, y una pantalla vacía no comunica para qué sirve el módulo.

Hasta hoy esto quedaba enmascarado porque las tablas acumulaban residuos de corridas de tests de integración (ya anotado para `ops.terminal` en S1.16). El reset limpio lo dejó a la vista.

---

## 4. Causa raíz D — M1 AODB no tiene listado de vuelos

Rutas reales del módulo núcleo (`services/aodb/.../api/router.py`):

```
POST      /vuelos                 alta
GET       /vuelos/{id}            detalle por id
POST      /vuelos/{id}/estados    registrar cambio de estado
GET       /vuelos/catalogo/*      4 catálogos
WEBSOCKET /vuelos/ws/estado       eventos en vivo
GET       /vuelos/informes/*      informes
GET       /vuelos                 →  405 Method Not Allowed   ← no existe
```

Consecuencia directa: la vista `vuelos/estado-tiempo-real` **no puede listar nada al entrar**. Solo muestra vuelos cuando llega un evento por WebSocket — de ahí los botones "conectar/desconectar" que el usuario no entiende: son el control de la suscripción en vivo, la única fuente de datos que la pantalla tiene.

Sin un `GET /vuelos` (con filtro de fecha/estado), el módulo núcleo no puede tener una vista comprensible por mucho que se rediseñe.

---

## 5. Estándar de CRUD unificado (requisito del usuario)

Aplica a **todos** los módulos:

| Acción | ¿Se ofrece? | Nota |
|:---|:---|:---|
| **Crear** | Sí | Modal de alta |
| **Ver detalles** | Sí | Modal de detalle — **es el contenedor de todas las acciones propias del registro** |
| **Editar información** | Sí | Dentro del detalle |
| **Suspender / Activar** | Sí | Cambio de estado, con las transiciones válidas del dominio |
| **Eliminación física** | **NO** | Se retira de la interfaz |

**Único punto donde hoy existe borrado físico**: `apps/web/src/app/tenants/tenant-list/tenant-list.html` ("Zona de peligro" → `DELETE /tenants/{id}`). Se retira de la interfaz. *(Decisión **D2** en §8: si el endpoint del backend también se retira o se deja sin consumidor.)*

Excepciones pedidas explícitamente:

- **API Keys**: mismo patrón, con sus acciones propias (rotar, revocar) dentro de "Ver detalles" — **sin edición de información** (una llave no se edita: se rota o se revoca).
- **Licencias**: hoy solo lista. Debe tener "Ver detalles" con módulo, vigencia, estado y origen, aunque no admita edición (las licencias las gobierna el plan del tenant).

---

## 6. Problemas por módulo

### 6.1 M1 AODB — "no se entiende qué dice"
- **Sin listado** (§4) → pantalla vacía al entrar.
- Botones "conectar/desconectar" sin explicación de qué es la conexión.
- CRUD incompleto: se puede crear vuelo y registrar estado, no editar ni cancelar.
- **Acciones**: crear `GET /vuelos`; cargar la lista al entrar; convertir el estado del WebSocket en un **indicador de estado de conexión** (no dos botones), con reconexión automática; llevar las acciones de fila a "Ver detalles".

### 6.2 M2 FIDS — "información ambigua, no se entiende para qué sirve"
- Muestra plantillas y pantallas sin explicar que una **plantilla** es el contenido que se dibuja y una **pantalla** es un monitor físico del terminal que reproduce una plantilla.
- Sin datos sembrados (§3) las dos tablas están vacías.
- Falta la señal más operativa del módulo: **qué pantallas están sin señal** (el monitor de `contar_pantalla_sin_senal` ya existe en backend).
- **Acciones**: encabezado que explique el modelo en una línea; KPI de pantallas activas / sin señal; CRUD completo sobre plantilla y pantalla; sembrar terminales y pantallas de ejemplo.

### 6.3 M3 Terminal & Gate Manager
- Tablero vacío (0 puertas, 0 terminales).
- CRUD: no existe alta/edición de **puerta** ni de **terminal** en la interfaz (solo asignaciones).
- **Acciones**: sembrar terminales y puertas; CRUD de puerta; asignación desde "Ver detalles" de la puerta.

### 6.4 M4 Ground Operations
- 0 turnarounds tras el reset.
- El detalle de turnaround (tareas, incidencias) está repartido entre modales y tablas sueltas.
- **Acciones**: sembrar turnarounds con tareas e incidencias; consolidar el detalle en un único modal.

### 6.5 M5 Revenue & Billing (facturas, tarifarios, conciliaciones)
- **"Limitación de 3 caracteres" en tarifas** → **no es un defecto**: el campo es la *moneda* ISO 4217 (`USD`, `EUR`), que son exactamente 3 letras, validado en `domain/tarifario.py`. El problema es que se presenta como **texto libre** junto al nombre del tarifario, y se confunde con el importe.
  **Acción**: convertirlo en un **selector de monedas**, y separar visualmente "datos del tarifario" de "conceptos y tarifas".
- **Conciliación**: pide `vuelo_id` como **texto libre** (hay que pegar un id de 18 dígitos a mano) y `periodo` como texto con formato implícito.
  **Acción**: selector de vuelo y selector de período.
- Errores 500 al crear con `role_tenant_admin` → causa raíz A.
- CRUD: falta "Ver detalles" de tarifario con sus conceptos editables.

### 6.6 D6 Soporte — tickets, KB y changelog
- **Tickets**: "no cambia de estado" → **es real y tiene explicación**: `cambiar_estado_ticket()` es **exclusivo de `role_support`** (regla de negocio de S1.8); la interfaz oculta esos controles para el resto de roles. Con `role_tenant_admin` el ticket es de solo escritura de mensajes.
  **Acción**: mostrar el estado y **por qué** no se puede cambiar ("solo el equipo de soporte cambia el estado") en vez de ocultar el control sin explicación; y decidir si `role_tenant_admin` debe poder cerrar sus propios tickets (**D3**).
- **Trazabilidad ausente**: el hilo muestra mensajes, pero no los **cambios de estado** ni quién los hizo. El dato existe (`compliance.log_auditoria` registra la transición), no está expuesto.
  **Acción**: línea de tiempo del ticket = mensajes + transiciones de estado, en orden cronológico.
- **KB y changelog "no se entiende su función"**: son legítimos pero están sin contexto y **vacíos** (0 artículos).
  - *Base de conocimientos*: respuestas reutilizables para no re-resolver el mismo ticket. Su valor aparece **enlazada al ticket** ("artículos relacionados"), no como una tabla suelta.
  - *Changelog*: novedades de producto publicadas a los tenants. Hoy solo `role_platform_admin` puede publicar.
  - **Acción**: encabezado que declare la función de cada sección; sembrar ejemplos; enlazar KB desde el detalle del ticket. **D4**: si aun así no aportan, retirarlos de la interfaz y dejarlos como API.

### 6.7 Tenants / Usuarios / API Keys / Licencias
- Retirar borrado físico (§5).
- API Keys: acciones dentro de "Ver detalles", sin edición.
- Licencias: agregar "Ver detalles".

---

## 7. Plan de corrección por fases

Ordenado por relación impacto/costo: primero lo que apaga los errores, después lo que llena las pantallas, al final el rediseño.

### Fase 1 — Apagar los errores de servidor *(backend, bajo costo, impacto inmediato)*
1. `services/gateway/main.py`: reconocer `insufficient privileges` además de `access denied` → **403 legible en vez de 500** (§2).
2. Resolver la divergencia de permisos según **D1** (§8): alinear `roles_modulos.py` con el DDL, o agregar los `GRANT` faltantes.
3. Test de regresión que recorra, por cada rol operativo, una escritura de cada módulo y **exija 201 o 403 — nunca 500**. Esta prueba es la que impide que la divergencia vuelva.

### Fase 2 — Que las pantallas tengan qué mostrar *(datos)*
4. Ampliar `db/seeds/generate.py`: terminales, puertas, plantillas y pantallas FIDS, turnarounds con tareas e incidencias, un tarifario vigente con conceptos, facturas en varios estados, artículos de KB y una entrada de changelog.
5. Verificar que tras `reset + migraciones + seeds` **ningún módulo se abre vacío**.

### Fase 3 — Cerrar los huecos de API *(backend)*
6. `GET /vuelos` con filtros de fecha y estado (§4).
7. CRUD de puerta y terminal (§6.3).
8. Trazabilidad del ticket: exponer las transiciones de estado junto al hilo (§6.6).
9. Regenerar `docs/api/openapi.yaml` (la compuerta de CI de S1.15 lo exige).

### Fase 4 — Estandarizar el CRUD *(frontend)*
10. Retirar el borrado físico de `tenant-list`.
11. Aplicar el patrón único **crear / ver detalles / editar / suspender-activar** en los 9 módulos, con las acciones propias siempre dentro de "Ver detalles".
12. "Ver detalles" en Licencias; acciones de API Key dentro de su detalle, sin edición.

### Fase 5 — Comprensibilidad *(frontend, con `frontend-design` y `DIRECCION_VISUAL.md`)*
13. Cada módulo abre con **una línea que dice qué resuelve** y KPI del estado actual.
14. AODB: indicador de conexión en vivo en lugar de botones conectar/desconectar.
15. Billing: selector de moneda y de vuelo en lugar de texto libre.
16. Soporte: línea de tiempo del ticket y KB enlazada desde el ticket.
17. Estados vacíos que **inviten a la acción** ("Todavía no hay puertas registradas — Crear la primera") en vez de una tabla en blanco.

### Fase 6 — Verificación
18. Recorrido con **los 5 usuarios operativos** (`controlador@`, `rampa@`, `aerolinea@`, `facturacion@`, `canario@`), módulo por módulo, sin 500 ni pantallas vacías.
19. `ruff` / `mypy` / `bandit` / `import-linter` + `pytest` en verde; build de producción de `apps/web` en verde.
20. Actualizar `CLAUDE.md` y `docs/diseno/WORKPANEL_Y_DASHBOARD_ROLES.md`.

---

## 8. Decisiones abiertas

| # | Decisión | Opciones |
|:---|:---|:---|
| **D1** | **Permisos de `role_tenant_admin`** (la de mayor alcance). | (a) **Respetar la matriz 4.3.1**: quitarle los scopes de escritura de M1/M3/M4/M5 — es *configuración*, no operación; el usuario prueba con los roles operativos. (b) **Ampliar los GRANT** del motor para que pueda operar de todo en su tenant. (c) Mixto por módulo. |
| **D2** | **`DELETE /tenants/{id}`** tras retirar el botón. | (a) Se retira también del backend. (b) Se conserva sin consumidor de interfaz. |
| **D3** | ¿`role_tenant_admin` puede **cerrar sus propios tickets**? | (a) No — solo `role_support` (regla actual). (b) Sí, limitado a resolver/cerrar los que él creó. |
| **D4** | **KB y changelog en la interfaz.** | (a) Se quedan, con contexto y datos de ejemplo. (b) Se retiran de la interfaz. |
| **D5** | **Alcance de esta corrección.** | (a) Solo los módulos de la **capa operativa** (consistente con lo acordado). (b) Los 9 módulos, incluidos tenants/usuarios/API keys/licencias — que es lo que el pedido menciona explícitamente. |

Recomendación por defecto: **D1(a)** — es la que respeta la separación de capas ya acordada y no debilita el modelo de permisos; **D2(b)**, **D3(b)**, **D4(a)**, **D5(b)**.

---

## 9. Lo que este plan NO cubre

- Dashboards por rol → `docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md`.
- La ingesta analítica real hacia `ah_tactico` (Fase 2, S2.1-S2.4).
- El `GRANT` de `role_tenant_admin` sobre `compliance.*` — queda subsumido en **D1**.
