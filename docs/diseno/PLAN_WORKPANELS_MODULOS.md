# Plan: llevar el patrón de workpanel de `tenants` al resto de vistas

| Campo | Contenido |
|:---|:---|
| **Estado** | Plan — sin empezar |
| **Origen** | `tenants/tenant-list` (post S1.13, commit `44457f4`), iterado en 4 rondas directas con el usuario |
| **Alcance** | `vuelos/estado-tiempo-real`, `puertas/tablero-puertas`, `rampa/panel-turnaround`, `billing/panel-facturas` |
| **Depende de** | Nada nuevo — todos los primitivos que este plan usa ya existen en `apps/web/src/app/_primitivos.scss` |

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

## 2. Qué tiene hoy cada vista, y qué le falta

Verificado por lectura directa del código actual (no supuesto):

| Vista | Tira | Tabla anidada | Búsqueda | Paginación | Modal crear/detalle | Etiqueta de estado |
|:---|:---|:---|:---|:---|:---|:---|
| `vuelos/estado-tiempo-real` | ✅ `.ah-tira` por evento | — (no aplica, es un log de eventos, no un CRUD) | ❌ | ❌ | ❌ (no tiene creación, es de solo lectura) | ❌ texto crudo (`codigo_estado`) |
| `puertas/tablero-puertas` | ✅ `.ah-tira` por puerta | ✅ `.ah-tabla` de asignaciones | ❌ | ❌ | ❌ (formulario de asignación es inline) | N/A (no hay pill de estado de puerta, solo semáforo de ocupación) |
| `rampa/panel-turnaround` | ✅ `.ah-tira` por turnaround | ✅ `.ah-tabla` de tareas e incidencias | ❌ | ❌ | ❌ (creación y detalle de tareas son inline) | ❌ texto crudo (`t.estado`, `tarea.estado`) |
| `billing/panel-facturas` | ✅ `.ah-tira` por factura | ✅ `.ah-tabla` de líneas de cargo | ❌ | ❌ | ❌ (cálculo/emitir/disputar son inline) | ❌ texto crudo (`factura.estado`) |

Ninguna de las 4 tiene panel de búsqueda, paginación, ni modal — las 4 heredan
el patrón de "todo inline en la misma página" de S1.11/S1.12/S1.13, anterior
a que el workpanel de tenants lo iterara.

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

## 4. Tareas concretas por vista (una vez confirmado el alcance de §3.2)

### `vuelos/estado-tiempo-real`

- [ ] `claseDeEstado` (ya existe) gana un vecino `etiquetaEstado(codigo)` —
  mapeo sobre `catalogo.estado_vuelo_catalogo` (6 valores reales, ver
  `services/aodb`).
- [ ] Quitar `max-width` de `.consola`.
- [ ] Sin paginación (RF-O04 ya limita el historial a 20).
- [ ] Sin modal (vista de solo lectura, sin creación ni edición).

### `puertas/tablero-puertas`

- [ ] Formulario de "Asignar puerta manualmente" pasa de inline a modal
  (mismo patrón que `TenantCreation`: componente embebible con
  `@Output() cerrar`).
- [ ] `table-layout: auto` ya global, sin cambio de código en esta vista.
- [ ] Quitar `max-width` de `.consola`.
- [ ] Evaluar con el usuario: ¿panel de búsqueda por código de puerta o
  tipo? ¿paginación si hay muchas puertas?

### `rampa/panel-turnaround`

- [ ] `claseEstadoTurnaround`/`puntoEstadoTarea`/`puntoSeveridadIncidencia`
  (ya existen) ganan sus `etiqueta*()` correspondientes — 3 catálogos
  distintos (`estado` de turnaround, `estado` de tarea, `severidad` de
  incidencia), 3 mapeos separados.
- [ ] Formulario de "Crear turnaround" e "Iniciar/finalizar tarea" pasan de
  inline a modal.
- [ ] Quitar `max-width` de `.consola`.
- [ ] Evaluar con el usuario: panel de búsqueda por vuelo/aeronave,
  paginación de turnarounds si la lista crece.

### `billing/panel-facturas`

- [ ] `claseEstadoFactura` (ya existe) gana `etiquetaEstadoFactura()` — 5
  valores reales (`borrador`/`emitida`/`pagada`/`vencida`/`disputada`).
- [ ] Formulario de "Calcular facturación" y las acciones de
  emitir/disputar pasan de inline a modal (el detalle de factura con sus
  líneas se queda como está, o se lleva al mismo modal — a decidir).
- [ ] Quitar `max-width` de `.consola`.
- [ ] Evaluar con el usuario: panel de búsqueda por aerolínea/estado,
  paginación si el volumen de facturas lo justifica.

---

## 5. Orden sugerido

1. **Confirmar §3.2** con el usuario, vista por vista (puede ser una sola
   conversación, no 4 separadas).
2. Aplicar primero lo de §3.1 a las 4 vistas — es mecánico, de bajo riesgo,
   y dejaría las 4 ya mejoradas aunque §3.2 tarde en confirmarse.
3. Aplicar §3.2 vista por vista, empezando por la que el usuario use con más
   frecuencia (a determinar).
4. Verificación en navegador real contra el backend en Docker en cada vista
   (Principio III), igual que en cada iteración de `tenant-list`.
5. Documentar en `CLAUDE.md` al cerrar, mismo formato usado para las 4
   iteraciones del workpanel de tenants.

## 6. Fuera de alcance de este plan

- M6/M8/M9 sin vista Angular — decisión ya tomada, sigue sin tocarse.
- `fids-player/pantalla-player` (S1.14) — otra aplicación, otras
  restricciones, no es un workpanel administrativo.
- Backend nuevo — todo lo de §3.1 y la mayoría de §3.2 es 100% frontend
  sobre datos que cada vista ya recibe; si algún filtro necesitara un
  endpoint nuevo, se decide puntualmente en esa tarea, no aquí.
