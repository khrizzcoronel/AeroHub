# Patrón de workpanel y modal de detalle

| Campo | Contenido |
|:---|:---|
| **Estado** | Vigente — actualizado 2026-08-08 |
| **Alcance** | Toda vista de `apps/web` que administre una lista de registros (workpanel): tabla + búsqueda + paginación + modal de alta/detalle |
| **Referencia viva** | `apps/web/src/app/usuarios/usuario-list/` (`.ts`/`.html`/`.scss`) — ante cualquier duda, leer ese código antes que este documento |
| **Relacionado** | `docs/diseno/DIRECCION_VISUAL.md` (tokens, tipografía, principios generales — este documento no los repite) |

Este documento **no rediseña nada por su cuenta**: cataloga el patrón ya
construido y verificado en navegador real, para que la próxima vista
administrativa lo aplique directamente en vez de re-derivarlo. Reemplaza a
`PLAN_WORKPANELS_MODULOS.md` y absorbe su contenido vigente (el resto —
tareas ya ejecutadas, historial de iteración por vista— vive en `CLAUDE.md`
y en el propio código).

---

## 1. Estructura del workpanel (la lista)

### 1.1 Patrón base -- compartido hoy por todas las vistas administrativas

Presente en `tenants`, `api-keys`, `licencias`, `vuelos`, `puertas`,
`rampa`, `billing`, y en `usuarios/usuario-list` antes de la iteración de
cabecera de §1.2:

1. **Línea de apertura + KPI** (`.consola__resumen`): una oración que dice
   qué muestra la vista, con un resumen en vivo calculado en el cliente
   sobre los datos ya cargados (nunca una llamada nueva al backend). Ver §3.
2. **Panel de búsqueda separado de la tabla** (`.ah-panel`): card propia con
   título ("Buscar…") y campos de filtro lado a lado (`.ah-panel__campos`).
3. **Filtro en vivo, 100% client-side**: un `computed()` que combina todos
   los criterios activos sobre la lista ya cargada. Si el volumen real de
   datos crece, se mueve a query params del backend sin cambiar la
   interacción del usuario.
4. **Barra de acciones simple** (`.consola__acciones`): botones `.ah-btn`
   normales, radio estándar (`var(--ah-radius)`) — nunca el estilo píldora
   de `.ah-barra-acciones` (se probó y se descartó por inconsistente).
5. **Tabla de columnas** (`.ah-tabla`, `table-layout: auto`, distribución
   automática por contenido), envuelta en `.tabla-envoltorio`
   (`overflow-x: auto`) para que el scroll horizontal en móvil quede
   contenido ahí y nunca en la página completa.
6. **Estado como `.ah-pill`, con etiqueta legible**: nunca el valor crudo
   del enum (`en_onboarding`) — una función `etiquetaEstado*()` por vista
   que traduce cada valor real a texto natural, y una `claseEstado*()`
   separada y pura para el color (mismo semáforo de 4 tonos de
   `DIRECCION_VISUAL.md`).
7. **Una sola acción por fila**, que abre el modal — nunca 3 botones
   sueltos por fila. Ver §2.
8. **Paginación de 10 en 10** (`.ah-paginacion`), sobre la lista ya
   filtrada — mismo criterio client-side que el filtro (punto 3).
9. **Ancho fluido, sin `max-width`** en `.consola { width: 100%; }`. Un
   tope fijo siempre deja espacio libre en pantallas más anchas que ese
   número — se resuelve quitándolo, no subiendo el valor.
10. **Retroalimentación por Toast** (`ToastService`, `.ah-toast`) para
    confirmar operaciones exitosas — nunca un `alert()` ni un mensaje que
    reemplace el contenido de la vista.

### 1.2 Iteración de cabecera (2026-08-08) -- vigente en 6 de las 7 vistas administrativas de `role_tenant_admin`

Rediseño puntual de la cabecera y la barra de búsqueda, pedido con una
captura de referencia externa, nacido en `usuarios/usuario-list` y
propagado el mismo día (`docs/diseno/PLAN_PROPAGACION_WORKPANEL_MODAL.md`,
implementado) a **API Keys, Licencias, FIDS, Soporte y Compliance Hub**.
**No propagado a `tenants/tenant-list`** (es de `role_platform_admin`,
fuera de alcance de esa sesión) ni a las 4 vistas operativas densas
(`vuelos`, `puertas`, `rampa`, `billing/facturas` -- patrón distinto y
deliberado, ver el plan de propagación §0). Si se pide extenderlo a
cualquiera de esas, aplicar exactamente esto, no reinterpretarlo:

1. **Eyebrow** (`.consola__eyebrow`): texto pequeño en mayúsculas arriba
   del `<h1>`, mismo texto que la sección del menú lateral.
2. **Ícono de refresco inline** (`.consola__refrescar`, símbolo `↻`) junto
   al `<h1>`, en vez de un botón "Actualizar" separado en la barra de
   acciones.
3. **KPI como chips** (`.ah-chip`, `.ah-chip--critico`/`.ah-chip--atencion`)
   en vez de la oración de resumen de §1.1 punto 1 -- insignia de fondo
   tenue (`color-mix(in srgb, <color> 16-18%, #fff)`) + texto del color
   saturado, **nunca** relleno sólido (eso es lo que distingue a `.ah-chip`
   de `.ah-pill`: el pill marca el estado DE una fila, el chip resume un
   conteo agregado de toda la lista).
4. **Una sola fila** (`.consola__fila-busqueda`) con buscador con ícono
   (`.ah-buscador`, símbolo `⌕` a la izquierda dentro del input), filtro
   inline (`.ah-campo--inline`, etiqueta a la izquierda del control en vez
   de arriba) y el botón de acción principal ("Invitar Usuario") -- **en
   vez de** el panel de búsqueda separado + barra de acciones de §1.1
   puntos 2 y 4.
5. **Buscador y `<select>` del filtro con la misma altura exacta**
   (`height: 2.8rem` en ambos) -- igualar solo el padding no alcanza, un
   `<select>` nativo renderiza mas alto que un `<input>` con el mismo box
   model (la flecha del navegador ocupa espacio propio).
6. **Acción de fila con texto corto** ("Ver", no "Ver detalles") en vez de
   un ícono -- se probó un botón de solo ícono (👁) y se revirtió a pedido
   explícito del usuario.

**`.ah-chip` es primitivo global** (`_primitivos.scss`) desde el tercer
uso real (Usuarios/API Keys/Licencias) -- no copiarlo por vista, ya está
disponible en todo `apps/web`.

**Vistas multi-sección** (FIDS: 2, Soporte: 3, Compliance: 5): el eyebrow
y el ícono de refresco son de **página completa** (uno solo), los chips
de KPI también son de página completa, pero `.consola__fila-busqueda` se
repite **por sección** -- cada tabla mantiene su propio buscador/filtro y
su propio botón de alta. Cuando una sección tiene más de un filtro (ej.
tickets de Soporte: Estado + Severidad), ambos van como `.ah-campo--inline`
dentro de la misma fila, antes del botón de acción.

**Experimento probado y revertido (mismo día): reemplazar el `<select>`
nativo por un listbox propio.** El control cerrado se restyled primero
(flecha propia via `background-image`, sin librería) y funcionó bien. Para
la lista ABIERTA se construyó un componente `app-select-personalizado`
(botón + `<ul role="listbox">` posicionado, sin librería) porque un
`<select>` nativo no permite re-estilar su menú desplegable con CSS puro.
Funcionaba, pero trajo problemas reales en cadena: dentro de un modal la
lista quedaba recortada por el `overflow-y: auto` de `.ah-modal` (un
`overflow` de un ancestro recorta a sus descendientes sin importar su
`position`, incluido `fixed`); la solución --reubicar el nodo en
`document.body` con `getBoundingClientRect()`-- lo arregló, pero introdujo
un problema nuevo (la lista quedaba "flotando" desconectada del control si
se hacía scroll dentro del modal después de abrirla, porque las
coordenadas se calculaban una sola vez). Ese segundo problema también se
resolvió (cerrar el listbox al detectar cualquier scroll, vía un listener
en fase de captura sobre `document`). En ese punto, con el problema ya
resuelto, el usuario pidió explícitamente volver al `<select>` nativo sin
ninguna personalización -- **decisión final: `<select>` nativo, sin flecha
propia, sin listbox propio.** El componente `app-select-personalizado` se
eliminó del código. Si en el futuro se vuelve a pedir personalizar un
`<select>`, este historial ahorra las 2 vueltas de descubrimiento (recorte
por `overflow`, desincronización por scroll) -- pero **no** volver a
construirlo sin que el usuario lo pida de nuevo explícitamente.

---

## 2. Estructura del modal "Ver detalles"

Patrón fijado con `usuarios/usuario-list` (2026-08-07) tras varias rondas
de iteración directa con el usuario. Tres bloques, en este orden:

```
┌──────────────────────────────────────────────────────┐
│ {título/nombre del registro}      [PILL DE ESTADO]  ✕│
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ CORREO                                          │   │  <- tarjeta de
│ │ valor@dominio.test                              │   │     contexto
│ │ ─────────────────────────────────────────────── │   │
│ │ NOMBRE                                          │   │
│ │ Valor legible                                   │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│  Campo editable A (70%)      Campo editable B (30%)   │
│  [combobox.........]         [switch] Estado          │
│                                                        │
│                              [Guardar]   [Cancelar]   │
└──────────────────────────────────────────────────────┘
```

### 2.1 Cabecera

`.modal-titulo-grupo`: `<h2>` con el nombre/título del registro + `.ah-pill`
con su estado **actual y ya persistido** (nunca el valor que el usuario
esté editando sin guardar — ver §2.3). Botón de cierre `.ah-modal__cerrar`
a la derecha.

### 2.2 Tarjeta de contexto (`.modal-usuario-contexto`)

Antes de cualquier campo editable, una tarjeta con fondo `var(--ah-paper-100)`
y borde `var(--ah-line-200)` que identifica **sobre qué registro puntual
opera el modal** — pedido explícito del usuario (2026-08-07): mostrar el
dato solo, sin etiqueta ni contraste, no dejaba claro que todo el modal
opera sobre ese registro. Contiene los campos **no editables** que
identifican al registro (correo + nombre en el caso de usuarios), cada uno
como una `__fila` con etiqueta en mayúsculas pequeña
(`.modal-usuario-contexto__etiqueta`) y valor en negrita
(`.modal-usuario-contexto__valor`). Varias filas dentro de la misma tarjeta
se separan con un borde superior sutil, no tarjetas repetidas. Solo el
valor que es un identificador técnico (correo, código) usa tipografía
monoespaciada — un nombre de persona no es un "dato", es texto.

### 2.3 Formulario — campos editables, guardado diferido

Los campos que sí se pueden modificar (rol, estado, etc.) van **debajo** de
la tarjeta de contexto, nunca mezclados con ella. Regla fija (pedido
explícito, 2026-08-07): **ningún cambio se envía al backend hasta presionar
"Guardar"** — ni el combobox ni el switch disparan la petición al tocarlos,
solo actualizan un signal local (`rolIdEdit`, `estadoEdit`, mismo patrón
por campo). Al presionar "Guardar", solo se llama al endpoint de cada campo
que realmente cambió respecto al valor original (evita un `PATCH`/`POST`
innecesario si el usuario solo tocó un campo).

Cuando dos campos comparten fila, la proporción es **70/30** (`flex: 7` /
`flex: 3` sobre `flex-basis` mínimo), con `align-items: flex-end` para que
controles de distinta altura (un `<select>` y un switch) compartan la
misma línea base.

### 2.4 Switch para estados binarios (`.ah-switch`)

Para una transición de estado que cicla entre exactamente 2 valores
(activo↔suspendido), un switch reemplaza los botones "uno por transición"
usados antes — más compacto, y comunica el estado *resultante* con una sola
mirada. Checkbox nativo oculto + pista/thumb propios (sin librería):

- Pista (`.ah-switch__pista`): `var(--ah-estado-atencion)` cuando el
  destino es el estado "no ideal" (ej. suspendido), `var(--ah-estado-ok)`
  cuando está en el estado activo — mismos 4 tonos de semáforo del resto
  del sistema, nunca un color nuevo.
- Un estado **terminal** (sin transición válida, ej. `eliminado_logicamente`)
  no muestra switch — se omite el campo entero, no se deshabilita un
  control inútil.
- `aria-label` dinámico ("Cambiar estado a Suspendido") en el checkbox, no
  en el texto visible — el texto visible muestra el estado *actual* del
  edit local, el `aria-label` describe la *acción* del control.

### 2.5 Acciones

`.modal-acciones` con `justify-content: flex-end` — los botones van
**alineados a la derecha** del modal (pedido explícito, 2026-08-07), nunca
a la izquierda ni centrados. "Guardar" (`.ah-btn`, azul sólido) primero,
"Cancelar" (`.ah-btn--secundario`, blanco con borde) después.

### 2.6 Ancho del modal

`.ah-modal` (primitivo global, `_primitivos.scss`) usa `max-width: 560px`
(subido desde 480px el 2026-08-07, pedido explícito: con una fila de 70/30
más la tarjeta de contexto, 480px quedaba justo). Cualquier modal nuevo
hereda este ancho automáticamente — no declarar un `max-width` propio por
vista salvo que el contenido lo justifique explícitamente.

### 2.7 Componentes de creación embebidos -- sin título ni tarjeta propia

Un formulario de alta que se embebe dentro de un `.ah-modal` (ej.
`app-invitar` dentro del modal "Invitar Usuario" de
`usuarios/usuario-list`) **nunca** trae su propio `<h1>`/subtítulo ni su
propia tarjeta contenedora — el modal ya aporta la cabecera
(`.ah-modal__cabecera`, título + botón de cierre) y el marco visual
(`.ah-modal`, fondo blanco + sombra + borde). Hallazgo real (2026-08-08):
`app-invitar` venía de reusar `_auth-form.scss` (pensado para páginas de
auth **standalone**, con su propio `<h1>` + tarjeta con sombra), lo que al
embeberse dentro de `.ah-modal` producía un título duplicado y una
tarjeta-dentro-de-tarjeta visualmente rota. Corregido: el componente ahora
solo tiene un `<form class="formulario">` con `.ah-campo` por campo,
`.ah-alerta` para errores, y `.modal-acciones` con
`justify-content: flex-end` (mismo criterio que §2.5) para sus botones --
sin `<h1>`, sin `.card`, sin `box-shadow` propio. Cualquier otro formulario
de alta que se vaya a embeber en un modal (no navegar a él como página
aparte) sigue este mismo criterio.

---

## 3. KPI de apertura (línea de resumen)

Patrón fijado en la Fase 5 de la corrección transversal de módulos
(2026-08-07): cada vista de lista abre con una oración
(`.consola__resumen`) que dice qué muestra el módulo, más un conteo en
vivo sobre los datos ya cargados (nunca una llamada nueva al backend —
"un conteo en el cliente sobre filas ya traídas no es un informe
compuesto"). Cuando el resumen une 2+ cláusulas condicionales con coma, se
arma como un `computed<string>` en TypeScript, **nunca con `@if` anidados
en el template** — el whitespace de indentación entre bloques `@if` se
colapsa a un espacio real en el HTML renderizado y deja un espacio de más
antes de la coma (`"24 activas , 8 por expirar"`). Ver
`resumenUsuarios`/`resumenLlaves`/`resumenTenants`/`resumenLicencias`/
`resumenFids`/`resumenCompliance` en cada componente para el patrón exacto.

---

## 4. Excepciones documentadas (no son huecos, son decisiones)

- **`api-keys/api-key-list`** no adopta el modal "Ver detalles" para
  `Rotar`/`Revocar`: son operaciones irreversibles de un solo paso, no una
  edición de campos — forzarlas a un modal de detalle agregaría un clic sin
  beneficio. Sí usa el modal para mostrar el secreto recién generado (una
  sola vez) y para "Ver detalles" de una llave existente (sin edición).
- **`licencias/licencia-list`** es de solo lectura: las licencias se
  otorgan al aprovisionar/actualizar el tenant, no se editan desde este
  panel. Su modal "Ver detalles" no tiene formulario, solo datos.
- **`vuelos/estado-tiempo-real` (M1)** no pagina su historial de eventos
  (RF-O04, "glanceability" — ver 20 eventos recientes de un vistazo importa
  más que navegar páginas).
- **Eliminación física**: nunca se ofrece desde un workpanel de
  `role_tenant_admin`. Si el backend tiene un endpoint de baja física,
  queda sin consumidor de interfaz (decisión D2(b), documentada en el
  "Checklist de corrección de módulos" de `CLAUDE.md`) — no se construye
  un botón "Eliminar" salvo pedido explícito y acotado.
