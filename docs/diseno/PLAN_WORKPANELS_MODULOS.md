# Plan: llevar el patrón de workpanel de `tenants` al resto de vistas

| Campo | Contenido |
|:---|:---|
| **Estado** | **Implementado (2026-08-04, pendiente de commit)** — `usuarios/usuario-list` (§4.1) y las 4 vistas operativas (§3.0/§4) ya tienen el patrón completo aplicado en código. |
| **Origen** | `tenants/tenant-list` (post S1.13, commit `44457f4`), iterado en 4 rondas directas con el usuario; la novena iteración (workpanels de `role_tenant_admin`: `usuarios`, `api-keys`, `licencias`) reusó los primitivos pero NO el patrón completo de modal de detalle/edición |
| **Alcance** | Vistas operativas: `vuelos/estado-tiempo-real`, `puertas/tablero-puertas`, `rampa/panel-turnaround`, `billing/panel-facturas`. Workpanels administrativos: `usuarios/usuario-list`, `apiKeys/api-key-list`, `licencias/licencia-list` |
| **Depende de** | Para las 4 vistas operativas y `api-keys`/`licencias`: nada nuevo, todos los primitivos ya existen en `apps/web/src/app/_primitivos.scss`. Para `usuarios/usuario-list`: SÍ requiere backend nuevo — ver §2.1 |

Este documento no rediseña nada por su cuenta: **cataloga** las características
que `tenants/tenant-list` terminó teniendo tras 4 iteraciones directas con el
usuario, y las traduce en tareas concretas por vista. Sirve de referencia para
cuando se retome el rediseño de estas 4 pantallas — no re-derivar el patrón
desde cero, aplicarlo.

---

## 1. El patrón de referencia (`tenants/tenant-list`)

Ocho características, cada una ya resuelta y verificada en navegador real:

1. **Panel de búsqueda separado de la tabla** (`.ah-panel`): card propia con
   título ("Buscar…") y campos de filtro lado a lado (`.ah-panel__campos`).
2. **Filtro en vivo, 100% client-side**: sobre la lista ya cargada, sin pedir
   nada nuevo al backend — un `computed()` que combina todos los criterios
   activos. Si el volumen real de datos crece, se mueve a query params del
   backend sin cambiar la interacción.
3. **Barra de acciones simple**: `.consola__acciones` con botones `.ah-btn`
   normales (radio estándar, no píldora — la píldora de `.ah-barra-acciones`
   se probó y se descartó por inconsistente con el resto del sistema).
4. **Tabla de columnas, no lista de tiras**: `.ah-tabla` con
   `table-layout: auto` (ya global en `_primitivos.scss`, distribución de
   ancho automática según contenido — no hace falta declarar nada por vista).
   Envuelta en `.tabla-envoltorio` (`overflow-x: auto`) para que el scroll
   horizontal en móvil quede contenido ahí y nunca en la página completa.
5. **Estado como `.ah-pill`, con etiqueta legible**: nunca el valor crudo del
   enum (`en_onboarding`) — una función `etiquetaEstado*()` por vista que
   traduce cada valor real a texto natural, mapeo exhaustivo sobre el
   catálogo cerrado de esa entidad. La clase de color (`claseEstado*()`) y la
   etiqueta son funciones separadas y puras, mismo criterio que ya usa cada
   vista para el color.
6. **Una sola acción por fila: "Ver detalles"**, que abre un modal
   (`.ah-modal-fondo`/`.ah-modal`) con: la pill de estado actual en la
   cabecera, el formulario de edición, y — solo si aplican — los botones de
   transición de estado válidos para ese registro puntual. Nunca 3 botones
   sueltos por fila.
7. **Modal de creación**, no navegación a una ruta aparte — el formulario de
   alta se vuelve un componente embebible (`@Output() cerrar`) que
   `tenant-list` monta condicionalmente, sin cambiar la URL.
8. **Paginación de 10 en 10** (`.ah-paginacion`), sobre la lista ya
   filtrada — mismo criterio client-side que el filtro (punto 2).
9. **Ancho fluido, sin `max-width`**: `.consola { width: 100%; }`. Se probó
   con topes fijos (960px → 1200px → 1500px) y todos dejan espacio libre en
   pantallas más anchas que ese número — se resolvió de raíz quitando el
   tope, no subiendo el valor otra vez.
10. **Validación en tiempo real de disponibilidad**: Debounce client-side sobre
    campos de catálogo o identidad (`código`, `email`) contra `GET /tenants/validar`
    para deshabilitar el botón de envío y alertar inline antes de presionar Crear.
11. **Borrado Físico permanente en Zona de Peligro**: Endpoint `DELETE /tenants/{tenant_id}`
    con botón destructivo (`.ah-btn--peligro`) y modal de confirmación con advertencia
    irreversible para administradores de plataforma.
12. **Retroalimentación mediante Toast**: Notificaciones flotantes en esquina
    superior derecha (`ToastService`, `.ah-toast`) para confirmar operaciones
    exitosas (aprovisionar, actualizar, cambiar estado, eliminar, copiar al portapapeles).

Primitivos que este patrón dejó en `_primitivos.scss`, ya disponibles sin
que haga falta crear nada nuevo: `.ah-panel`, `.ah-barra-acciones` (opcional,
ver punto 3), `.ah-pill`, `.ah-modal-fondo`/`.ah-modal`, `.ah-paginacion`,
`.ah-btn--sm`, `.ah-toast-container`/`.ah-toast`, `.ah-btn--peligro`.

---

## 2. Qué tenía cada vista antes de §3.0/§4 (estado histórico, ya resuelto)

Estado ANTES de la implementación del 2026-08-04 — se conserva como
referencia de "de dónde venía cada vista", no como estado actual (ver §2.2
para el estado actual):

| Vista | Tira | Tabla anidada | Búsqueda | Paginación | Modal crear/detalle | Etiqueta de estado |
|:---|:---|:---|:---|:---|:---|:---|
| `vuelos/estado-tiempo-real` | ✅ `.ah-tira` por evento | — (no aplica, es un log de eventos, no un CRUD) | ❌ | ❌ | ❌ (no tiene creación, es de solo lectura) | ❌ texto crudo (`codigo_estado`) |
| `puertas/tablero-puertas` | ✅ `.ah-tira` por puerta | ✅ `.ah-tabla` de asignaciones | ❌ | ❌ | ❌ (formulario de asignación es inline) | N/A (no hay pill de estado de puerta, solo semáforo de ocupación) |
| `rampa/panel-turnaround` | ✅ `.ah-tira` por turnaround | ✅ `.ah-tabla` de tareas e incidencias | ❌ | ❌ | ❌ (creación y detalle de tareas son inline) | ❌ texto crudo (`t.estado`, `tarea.estado`) |
| `billing/panel-facturas` | ✅ `.ah-tira` por factura | ✅ `.ah-tabla` de líneas de cargo | ❌ | ❌ | ❌ (cálculo/emitir/disputar son inline) | ❌ texto crudo (`factura.estado`) |

Ninguna de las 4 tenía panel de búsqueda, paginación, ni modal — las 4
heredaban el patrón de "todo inline en la misma página" de S1.11/S1.12/S1.13,
anterior a que el workpanel de tenants lo iterara.

### 2.2 Estado actual (post 2026-08-04) — las 4 vistas ya tienen el patrón completo

| Vista | Estructura | Búsqueda | Paginación | Modal crear/detalle | Etiqueta de estado |
|:---|:---|:---|:---|:---|:---|
| `vuelos/estado-tiempo-real` | ✅ `.ah-tabla` por evento | ✅ por vuelo id | ✅ 10 en 10 | N/A (sigue de solo lectura, sin creación) | ✅ `etiquetaEstado()`, 6 valores |
| `puertas/tablero-puertas` | ✅ `.ah-tabla` por puerta | ✅ por código/tipo | ✅ 10 en 10 | ✅ modal "Asignar puerta" + modal "Ver asignaciones" por fila | `.ah-pill` de ocupación (libre/ok/crítico) |
| `rampa/panel-turnaround` | ✅ `.ah-tabla` por turnaround | ✅ por número de vuelo | ✅ 10 en 10 | ✅ modal "Crear turnaround" + modal "Ver detalles" (tareas) por fila | `.ah-pill` de estado (reusa `claseEstadoTurnaround`) |
| `billing/panel-facturas` | ✅ `.ah-tabla` por factura | ✅ por aerolínea + estado | ✅ 10 en 10 | ✅ modal "Calcular facturación" + modal "Ver detalle" (líneas, emitir/disputar) por fila | `.ah-pill` de estado (reusa `claseEstadoFactura`) |

Incidencias (subtabla de `rampa`) se deja igual que estaba — ya era
`.ah-tabla`, nunca fue tira, y no tiene mutación propia desde este panel
(mismo criterio que `licencias` en §2.1).

### 2.1 Workpanels administrativos de `role_tenant_admin` (novena iteración, mismo día que `tenant-list`)

Estos tres SÍ construyeron panel de búsqueda + paginación (puntos 1-2, 8) desde
el principio — la brecha real es el modal de "Ver detalles" (puntos 6-7):

| Vista | Tabla | Búsqueda | Paginación | Modal ver/editar | Acciones por fila |
|:---|:---|:---|:---|:---|:---|
| `usuarios/usuario-list` | ✅ `.ah-tabla` | ✅ texto + rol | ✅ 10 en 10 | ❌ **falta — pedido directo del usuario, 2026-08-04** | ninguna (solo lectura hoy) |
| `api-keys/api-key-list` | ✅ `.ah-tabla` | ✅ por prefijo | ✅ 10 en 10 | ❌ (deliberado, ver nota abajo) | `Rotar` / `Revocar` inline, solo si `estado === 'activa'` |
| `licencias/licencia-list` | ✅ `.ah-tabla` | ❌ (catálogo M1-M9 cerrado, no justifica filtro) | ❌ (nunca son más de 9 filas) | ❌ (no aplica — solo lectura, sin mutación posible desde este panel) | ninguna |

**`api-keys` NO adopta el modal "Ver detalles" a propósito**: sus acciones
(`Rotar`, `Revocar`) son operaciones irreversibles de un solo paso, no una
edición de campos — forzarlas a un modal de detalle sería agregar un clic sin
beneficio. Esto es la misma lógica que ya distingue tenants (registro con
campos editables + transiciones de estado) de billing/facturas (acciones de
flujo, no edición). No se traslada el patrón aquí — es una diferencia real de
naturaleza de la vista, no un gap.

**`licencias` no tiene mutación posible desde este panel** (las licencias se
otorgan al aprovisionar/actualizar el tenant, no desde la vista del propio
tenant admin) — correctamente de solo lectura, sin acciones. Nada que agregar.

**`usuarios` SÍ es el mismo tipo de entidad que `tenants`** (registro
administrable con campos editables — rol — y transiciones de estado
`activo`/`suspendido`/`eliminado_logicamente`) y hoy es puramente de lectura:
sin acción de fila, sin forma de editar el rol de un usuario ni de
suspenderlo/reactivarlo desde la UI. Esta es la brecha que este plan cierra
en §4.1.

---

## 3.0 Decisión final confirmada (2026-08-04)

El usuario confirmó explícitamente, reabriendo la decisión estética de
S1.11/S1.12:

- **Tira → tabla en las 4 vistas** (`vuelos`, `puertas`, `rampa`, `billing`):
  se reemplaza `.ah-tira` por `.ah-tabla` de columnas, mismo criterio visual
  que `tenants`/`usuarios`. Esto SÍ reabre y reemplaza la decisión de
  "densidad, no aire" de `DIRECCION_VISUAL.md` §2.2 para estas 4 vistas —
  documentar el cambio ahí también al cerrar.
- **Panel de búsqueda en las 4**, incluyendo `vuelos` (el usuario pidió
  explícitamente "todas", no solo las 3 previstas en el plan original).
- **Paginación (10 en 10) en las 4**, incluyendo `vuelos` — se retira la
  excepción que este plan proponía por RF-O04 (historial de 20 eventos);
  el usuario prefirió aplicar el mismo patrón sin excepción.
- **Formularios inline → modal** en `puertas`/`rampa`/`billing`, mismo
  patrón que `TenantCreation` (componente embebible con `@Output() cerrar`,
  sin cambiar la URL).

Esto deja las 4 vistas operativas con el mismo patrón completo que
`tenants`/`usuarios`: tabla + panel de búsqueda + paginación + modal. Las
tareas de §4 (abajo) se actualizan para reflejar esto — ya no hay tareas
condicionadas a "evaluar con el usuario", todas están confirmadas.

---

## 3. Decisión que hay que tomar antes de tocar código

**`tenants` es un panel administrativo de registros (CRUD clásico). Las otras
4 son tableros operativos densos, pensados para monitoreo — la decisión de
diseño original de S1.11 (`DIRECCION_VISUAL.md` §2.2) fue explícitamente
"densidad, no aire" y el componente "tira" como unidad estructural
reutilizada.** Adoptar el patrón de tabla completo (punto 4) en las 4 vistas
operativas sería revertir esa decisión, no solo trasladar un estilo.

Por eso este plan separa lo que se traslada **sin reabrir la decisión de
tira vs. tabla** de lo que sí la reabre:

### 3.1 Se traslada tal cual a las 4 vistas (no reabre nada)

- Etiquetas legibles de estado (punto 5) — esto es correcto para
  `.ah-tira__estado` igual que para una `.ah-pill`, es independiente de si
  la unidad estructural es tira o fila de tabla.
- Modal para crear/detalle (puntos 6-7) — sacar los formularios inline de
  asignación/creación/cálculo a un modal no depende de si la lista de
  arriba es de tiras o de tabla.
- Ancho fluido sin `max-width` (punto 9) — ya se hizo en `tenant-list`, las
  otras 4 vistas también usan `.consola { max-width: 960px; }` heredado, se
  puede quitar igual.
- `table-layout: auto` para las tablas anidadas que ya existen (puertas,
  rampa, billing) — es un cambio de una línea ya global en
  `_primitivos.scss`, no requiere nada por vista.

### 3.2 Requiere confirmación explícita antes de implementar

- **Panel de búsqueda + filtro** (puntos 1-2): tiene sentido en las 4 —
  filtrar vuelos por código, puertas por código, turnarounds por vuelo,
  facturas por aerolínea/estado son búsquedas reales. Pero cambia el layout
  de cada vista (agrega un bloque nuevo arriba) y hay que decidir, vista por
  vista, cuáles campos filtrar.
- **Paginación** (punto 8): `vuelos/estado-tiempo-real` ya limita su
  historial a 20 eventos por diseño (RF-O04, "glanceability") — paginar ahí
  no aplica igual que en una lista de registros. Puertas/rampa/billing sí
  podrían crecer lo suficiente como para justificarla.
- **Tira vs. tabla** (punto 4): explícitamente NO se traslada sin
  preguntar — es la decisión estética central de S1.11/S1.12, reabrirla
  necesita acuerdo directo, no una inferencia de este plan.

---

## 4. Tareas concretas por vista — todas implementadas (2026-08-04, pendiente de commit)

### 4.1 `usuarios/usuario-list` — cerrado

Backend (`services/tenancy/aerohub_tenancy`):
- [x] `GET /usuarios/{usuario_id}` — `obtener_usuario_endpoint`, PN-01 (404).
- [x] `PATCH /usuarios/{usuario_id}` — solo `rol_codigo` (único campo
  administrable decidido; `nombre` lo fija la invitación, no se edita).
  Nuevo `application/actualizar_usuario.py`.
- [x] `POST /usuarios/{usuario_id}/estado` — `domain/usuario.py` nuevo, con
  `ESTADOS_VALIDOS_USUARIO` y `validar_transicion_estado_usuario` (sí
  ameritó función de dominio propia, misma máquina de estados que tenant).
- [x] Los 3 bajo `requiere_scope("usuarios:administrar")`.

Frontend (`apps/web/src/app/usuarios`):
- [x] `UsuarioService`: `obtenerUsuario`, `actualizarRolUsuario`, `cambiarEstadoUsuario`.
- [x] Columna "Acciones" con botón único "Ver detalles".
- [x] Modal con pill de estado, editor de rol (`<select>`), transiciones de
  estado disponibles (`transicionesDisponibles`, espejo de tenants).
- [x] Sin zona de peligro/borrado físico (confirmado, no pedido).
- [x] Toast de confirmación al guardar/cambiar estado.
- Extra no listado originalmente: se corrigió `claseEstado()` para que
  `eliminado_logicamente` sea crítico/rojo (terminal) en vez de ámbar —
  inconsistencia notada al implementar las transiciones reales.

### `vuelos/estado-tiempo-real` — cerrado

- [x] `etiquetaEstado(codigo)` — mapeo sobre los 6 valores reales de
  `catalogo.estado_vuelo_catalogo` (`db/seeds/generate.py::ESTADOS_VUELO`).
- [x] Quitado `max-width` de `.consola`.
- [x] **Paginación SÍ agregada** (10 en 10) — el usuario, al confirmar §3.0,
  pidió explícitamente "todas" incluyendo vuelos, retirando la excepción
  RF-O04 que este plan proponía originalmente. El historial sigue capado a
  20 eventos por el WebSocket (`eventos.update(...).slice(0, 20)`), así que
  en la práctica son máximo 2 páginas.
- [x] Panel de búsqueda por vuelo id (nuevo, también fuera del alcance
  original de este plan, mismo pedido explícito).
- [x] Migrado de `.ah-tira` a `.ah-tabla` — decisión reabierta y confirmada
  en §3.0 (no aplica solo a puertas/rampa/billing como preveía este plan).
- N/A modal: sigue de solo lectura, sin creación ni edición.

### `puertas/tablero-puertas` — cerrado

- [x] Formulario de "Asignar puerta manualmente" pasado a modal (bloque
  inline dentro del mismo componente, no un componente embebible aparte
  como `TenantCreation` — se evaluó que no ameritaba esa separación para un
  formulario de 4 campos sin lógica propia de validación compleja).
- [x] Nuevo modal "Ver asignaciones" por puerta (reemplaza la tabla anidada
  dentro de la tira).
- [x] Migrado de `.ah-tira` a `.ah-tabla`.
- [x] Quitado `max-width` de `.consola`.
- [x] Panel de búsqueda por código/tipo de puerta.
- [x] Paginación (10 en 10).

### `rampa/panel-turnaround` — cerrado

- [x] `puntoEstadoTarea`/`puntoSeveridadIncidencia` se mantienen sin cambio
  (siguen siendo `.ah-punto` dentro de la tabla de tareas/incidencias, que
  ya era tabla desde S1.12 — no aplicaba el mismo `etiqueta*()` que a
  `claseEstadoTurnaround`, que sí pasó a alimentar un `.ah-pill`).
- [x] Formulario de "Crear turnaround" pasado a modal.
- [x] Selección de turnaround ("Ver tareas") pasada a modal "Ver detalles"
  (incluye el formulario de iniciar/finalizar tarea, que se queda inline
  DENTRO de ese modal, no en un tercer nivel de modal).
- [x] Migrado de `.ah-tira` a `.ah-tabla` para turnarounds. La subtabla de
  incidencias no cambió (ya era `.ah-tabla`, sin mutación propia).
- [x] Quitado `max-width` de `.consola`.
- [x] Panel de búsqueda por número de vuelo (llegada o salida).
- [x] Paginación de turnarounds (10 en 10).

### `billing/panel-facturas` — cerrado

- [x] `etiquetaEstadoFactura` no se creó como función aparte — el pill
  reusa directamente el valor crudo del backend (`borrador`/`emitida`/
  `pagada`/`vencida`/`disputada`), ya son palabras legibles en español, a
  diferencia de `en_onboarding`/`eliminado_logicamente` que sí necesitaban
  traducción.
- [x] Formulario de "Calcular facturación" pasado a modal.
- [x] "Ver detalle" (líneas + emitir/disputar) pasado a modal, decisión
  tomada: SÍ se llevó al mismo modal (no quedó separado).
- [x] Migrado de `.ah-tira` a `.ah-tabla`.
- [x] Quitado `max-width` de `.consola`.
- [x] Panel de búsqueda por aerolínea + `<select>` de estado.
- [x] Paginación (10 en 10).

---

## 5. Orden ejecutado (2026-08-04)

Completado en este orden: (0) `usuarios/usuario-list` primero, sin depender
de nada más; luego se preguntó §3.2 con `AskUserQuestion` (tira→tabla en las
4, búsqueda+paginación en las 4 incluyendo vuelos, modal confirmado en
puertas/rampa/billing) y se implementó de una vez, sin dividir por vista.

**Pendiente, no ejecutado en esta ronda**:
- Verificación en navegador real (Principio III) — el usuario pidió el
  2026-08-04 dejar de verificar automáticamente en el navegador; se
  verificó en su lugar que el backend pasa ruff/mypy/bandit y que el
  frontend compila sin errores (`nx serve` en Docker, sin errores TS), pero
  NO se probó clic a clic contra datos reales. Coordinar con el usuario
  antes de darlo por cerrado end-to-end.
- Commit — todo el trabajo de este plan (usuarios + las 4 vistas
  operativas) sigue sin commitear a la fecha de este documento.
- Documentar el cierre en `CLAUDE.md` (tabla de sprints + sección de
  rediseño), mismo formato usado para las iteraciones del workpanel de
  tenants — pendiente hasta confirmar que el usuario da esto por cerrado.

## 6. Auditoría completa por rol (2026-08-04)

Las 9 vistas de `apps/web` (ver `app.routes.ts`) son todo el universo posible
— no hay ninguna vista fuera de este documento. Tabla de qué rol opera cada
una y el veredicto final del patrón:

| Vista | Rol(es) que la usan | Naturaleza | Veredicto |
|:---|:---|:---|:---|
| `tenants/tenant-list` | `role_platform_admin` | Registro administrable (CRUD) | ✅ Referencia — patrón completo desde antes |
| `usuarios/usuario-list` | `role_tenant_admin` | Registro administrable (CRUD) | ✅ Cerrado (§4.1) — backend nuevo + modal implementados |
| `api-keys/api-key-list` | `role_tenant_admin` | Operaciones de un paso (rotar/revocar) | ✔️ No aplica el modal — decisión de diseño, no gap (§2.1) |
| `licencias/licencia-list` | `role_tenant_admin` | Solo lectura, sin mutación posible | ✔️ No aplica — nada que agregar (§2.1) |
| `vuelos/estado-tiempo-real` | `role_operations_controller`, `role_airline_coordinator`, `role_tenant_analyst`, `role_implementation` | Antes: log de solo lectura. Ahora: tabla + búsqueda + paginación (decisión del usuario, §3.0) | ✅ Cerrado |
| `puertas/tablero-puertas` | `role_operations_controller`, `role_implementation`, `role_tenant_analyst` | Tablero operativo, ahora tabla administrable | ✅ Cerrado (§3.0/§4) |
| `rampa/panel-turnaround` | `role_ramp_agent`, `role_operations_controller`, `role_implementation`, `role_tenant_analyst` | Tablero operativo, ahora tabla administrable | ✅ Cerrado (§3.0/§4) |
| `billing/panel-facturas` | `role_billing_officer`, `role_implementation`, `role_tenant_analyst`, `role_business_viewer` (solo lectura) | Tablero operativo, ahora tabla administrable | ✅ Cerrado (§3.0/§4) |

**Roles sin ninguna vista propia** (confirmado ya en CLAUDE.md, no es un
hallazgo nuevo de esta auditoría): `role_sre`, `role_support`,
`role_data_engineer`, `role_ml_engineer`, `role_elt_reader`,
`role_people_viewer`, `role_regulatory_auditor` — todos mapean a M6/M7/M8/M9,
que tienen backend pero ningún panel Angular (decisión ya tomada, fuera de
alcance).

### 6.1 Priorización — ejecutada en este orden

1. **`usuarios/usuario-list`** (§4.1) — hecho.
2. **Confirmación de §3.2** vía `AskUserQuestion` — el usuario reabrió la
   decisión tira/tabla y pidió aplicar el patrón completo sin excepciones.
3. **Las 4 vistas operativas** (§3.0/§4) — hecho, todas de una vez.
4. `api-keys` y `licencias` siguen sin tareas pendientes de este patrón.

Pendiente real: commit, verificación en navegador (coordinar con el
usuario) y documentar el cierre en `CLAUDE.md` — ver §5.

---

## 7. Fuera de alcance de este plan

- M6/M8/M9 sin vista Angular — decisión ya tomada, sigue sin tocarse.
- `fids-player/pantalla-player` (S1.14) — otra aplicación, otras
  restricciones, no es un workpanel administrativo.
- Backend nuevo — todo lo de §3.1 y la mayoría de §3.2 es 100% frontend
  sobre datos que cada vista ya recibe; si algún filtro necesitara un
  endpoint nuevo, se decide puntualmente en esa tarea, no aquí.
