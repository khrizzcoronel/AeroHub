# Research: Rediseño de fids-player/pantalla-player (S1.14)

## Decisión 1 — Tres modos mutuamente excluyentes, un solo signal de "vista actual"

**Decisión**: `PantallaPlayer` expone un `modoActual` computado con 3
valores posibles: `'configuracion'` (nunca se conectó, o la conexión
falló), `'reproduccion'` (conectado, con contenido vigente), `'sin_senal'`
(estuvo conectado, la señal se perdió). Cada modo es una plantilla/bloque
`@if` completamente distinto en el HTML — no hay superposición de un
formulario sobre el contenido, ni un mensaje de error flotando encima.

**Razón**: spec.md US2/US3 exigen explícitamente que los tres estados
sean "claramente distintos" entre sí. Un solo signal derivado evita que
la plantilla combine banderas booleanas (`conectado && !error`, etc.) de
forma inconsistente.

**Alternativas consideradas**: mantener `conectado`/`error` como hoy y
superponer visualmente el estado de error — rechazado, es exactamente el
problema que spec.md FR-005 pide corregir (el error hoy es "un texto
genérico", no un modo propio).

## Decisión 2 — "Sin señal" se infiere de dos señales del cliente, con un pequeño debounce

**Decisión**: se pasa a `sin_senal` cuando ocurre cualquiera de:
(a) el WebSocket se cierra con `evento.code >= 4000` (mismo código de
rechazo ya usado hoy) sin que se haya iniciado un cierre manual
(`desconectar()`), o (b) el heartbeat falla (`enviarHeartbeat` responde
error) dos veces consecutivas (30s, el doble del intervalo de heartbeat
de 15s) — evita que un solo fallo transitorio de red dispare el modo
antes de que un heartbeat exitoso lo desmienta.

**Razón**: spec.md Edge Cases pide explícitamente que un corte "menor a
la duración de un ciclo de heartbeat" no se muestre; spec.md SC-003 pide
que se detecte en ≤ 15s. Dos fallos consecutivos (30s en el peor caso)
es el balance entre ambos: nunca parpadea por un solo paquete perdido,
y detecta dentro de una ventana razonable. Un solo fallo ya se
consideró (detección más rápida) pero se descartó por el riesgo de
falso positivo que spec.md pide evitar explícitamente.

**Alternativas consideradas**: usar solo el cierre del WebSocket (sin
mirar heartbeat) — rechazado, un WS puede quedar en estado
"medio abierto" (el navegador no siempre detecta la caída de inmediato)
mientras el heartbeat HTTP sí falla antes; usar solo heartbeat sin mirar
el WS — rechazado, pierde la señal de rechazo explícito del backend
(código ≥ 4000, ej. sesión inválida) que hoy ya se maneja.

## Decisión 3 — Recuperación automática sin intervención

**Decisión**: al recibir una plantilla nueva por WebSocket (evento
`onmessage`) o un heartbeat exitoso mientras se está en `sin_senal`, se
vuelve a `reproduccion` de inmediato, sin botón ni confirmación.

**Razón**: spec.md FR-006 lo exige explícitamente — es una pantalla sin
usuario humano de por vida, cualquier paso manual de recuperación la
deja rota indefinidamente ante un corte real.

## Decisión 4 — Tokens de color/tipografía se copian, no se comparten como paquete

**Decisión**: se copian las variables `:root` de `apps/web/src/styles.scss`
(navy/semáforo/fuentes) a `apps/fids-player/src/styles.scss`, sin
`@use 'app/primitivos'` (esa hoja tiene `.ah-btn`/`.ah-tabla`/etc., que
no aplican aquí por FR-002 — cero elementos de consola). Se agregan los
mismos `<link>` de Google Fonts (IBM Plex Sans/Mono) al `index.html` de
`fids-player`, replicando la corrección de S1.11 en `apps/web` (las
fuentes nunca se enlazaron ahí hasta ese sprint).

**Razón**: no existe hoy un paquete de diseño compartido entre las dos
apps Angular (son proyectos Nx independientes sin librería de UI común)
— crear uno sería infraestructura nueva, fuera de alcance de un sprint
de presentación (spec.md FR-009). Copiar los tokens es la forma más
simple de cumplir FR-008 sin esa infraestructura.

**Alternativas consideradas**: extraer un `libs/design-tokens` Nx nuevo
— rechazado por alcance (requiere reconfigurar ambos `project.json` y
las rutas de build, riesgo desproporcionado para 4 sprints de rediseño
puramente visual).

## Decisión 5 — Tamaños de tipografía propios de esta app, no una extensión de la escala de `apps/web`

**Decisión**: `fids-player` define su propia escala tipográfica (no
reutiliza los `font-size` de `apps/web`, que están pensados para
consolas administrativas leídas de cerca). La fila de contenido usa
`clamp()` con un mínimo generoso (≥ 3rem) para adaptarse a distintos
tamaños de pantalla física sin perder legibilidad a distancia.

**Razón**: spec.md SC-001 exige legibilidad a 3+ metros — una escala de
consola (diseñada para 40-60cm de un monitor de escritorio) no alcanza
sin importar el token de color/familia que se reutilice. Los *tokens*
(color, familia tipográfica) sí se comparten (Decisión 4); la *escala de
tamaño* no, porque responde a una restricción física distinta.

**Alternativas consideradas**: multiplicar los `font-size` de
`apps/web` por un factor fijo — rechazado, esta app tiene una sola
"columna" de contenido a la vez (no una tabla densa de 40 filas), así
que no hay tensión entre densidad y tamaño que resolver con un factor de
escala — se puede simplemente elegir el tamaño más grande que sigue
siendo legible como bloque.

## Decisión 6 — El formulario de configuración reutiliza el navy/ámbar del login de S1.10, no un layout nuevo

**Decisión**: el modo `configuracion` usa una composición similar al
login (`apps/web/auth/login`): franja/fondo navy, campo de texto claro,
sin las clases `.ah-campo`/`.ah-btn` (no se copia `_primitivos.scss`,
Decisión 4) pero sí el mismo lenguaje visual (bordes, radios, contraste).

**Razón**: spec.md US2 exige que la pantalla de configuración se sienta
"claramente distinta" del modo reproducción, pero coherente con el
sistema — reutilizar el patrón visual del login (ya reconocible como
"pantalla de acceso/configuración" en el resto del sistema) resuelve
ambas cosas sin inventar un tercer lenguaje visual.

## Decisión 7 — Respaldo de `definicion_json` sin la estructura `filas`

**Decisión**: cuando `filasDeTexto()` devuelve `null` (estructura no
reconocida), se muestra un mensaje centrado "Contenido no disponible en
este formato" en la misma tipografía grande del modo reproducción — no
el `<pre>{{ definicionJson() | json }}</pre>` actual.

**Razón**: spec.md FR-007 lo exige explícitamente — un JSON crudo es
ilegible a distancia y expone estructura interna en una pantalla
pública. Mostrar el JSON solo tiene valor para depuración, que no es un
caso de uso de esta pantalla (spec.md — nadie interactúa con ella).
