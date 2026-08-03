# Research: Sistema de diseño + deuda de JWT + vista canónica (S1.11)

## Decisión 1 — Primitivos en un archivo global nuevo, no dentro de `auth/`

**Decisión**: `apps/web/src/app/_primitivos.scss`, importado una vez desde
`styles.scss` (`@use`), no un archivo por módulo.

**Razón**: S1.12/S1.13 van a reutilizar `.ah-tira`/`.ah-tabla` desde
`puertas/`, `rampa/`, `billing/` y `tenants/` — carpetas que no tienen
ninguna relación de dependencia entre sí ni con `auth/`. Ponerlos dentro
de `auth/_auth-form.scss` (el único archivo compartido que existe hoy)
ataría un sistema transversal a un módulo que no es su dueño conceptual,
y obligaría a cada vista futura a importar un archivo llamado
"auth-form" para pintar una tabla de facturas.

**Alternativas consideradas**: (a) un archivo por primitivo — rechazado,
son piezas del mismo sistema que se leen mejor juntas y no tienen
dependencias entre sí que ameriten separarlos; (b) mixins/Sass en vez de
clases CSS reutilizables — rechazado, con componentes standalone y
plantillas HTML sencillas, clases utilitarias son más directas de aplicar
que un mixin por componente.

## Decisión 2 — `_auth-form.scss` se apoya en los primitivos nuevos, no se reemplaza

**Decisión**: `.card`/`.field`/`.btn`/`.alert`/`.notice` de
`_auth-form.scss` (S1.10) se reescriben para reusar los primitivos
nuevos (`.ah-campo`, `.ah-btn`, `.ah-alerta`) en vez de mantener sus
propias reglas duplicadas.

**Razón**: es exactamente la deuda que este sprint existe para prevenir
que se repita — si el rediseño crea `.ah-btn` pero deja `.btn` con sus
propias reglas de padding/color, el sistema queda con dos fuentes de
verdad para lo mismo, y S1.13 (que audita las 8 vistas de S1.10 contra el
sistema formalizado) heredaría exactamente ese trabajo de consolidación
que es más barato hacer ahora, mientras el autor todavía tiene el
contexto fresco.

**Alcance del cambio**: las 6 plantillas HTML de auth NO cambian sus
nombres de clase (`class="btn"`, `class="field"`) — solo el SCSS
subyacente cambia para delegar en los primitivos. Cero riesgo de romper
las vistas ya funcionando de S1.10; la auditoría visual completa de esas
8 vistas sigue siendo alcance de S1.13, no de aquí.

**Alternativas consideradas**: dejar `_auth-form.scss` intacto y que los
primitivos nuevos vivan en paralelo, sin tocarlo — rechazado, es la
inconsistencia que el propio `DIRECCION_VISUAL.md` §1 identifica como el
punto de partida a resolver, no a perpetuar.

## Decisión 3 — El WebSocket de vuelos lee el token de `AuthService.token()`, no de un textarea

**Decisión**: `estado-tiempo-real.ts` inyecta `AuthService` y arma la URL
del WebSocket con `auth.token()` en el mismo query param `?token=` que ya
usa hoy — el cambio es DE DÓNDE sale el valor, no el mecanismo de
transporte del token hacia el WebSocket (eso es un cambio de contrato de
`aerohub_gateway`, fuera de alcance de un sprint de frontend).

**Razón**: `AuthService` (S1.10) ya expone `token()` como signal
computado desde la sesión guardada — es exactamente el dato que hoy la
persona usuaria escribe a mano. `authInterceptor` no puede resolver este
caso porque intercepta `HttpClient`, y un `WebSocket` nativo del navegador
no pasa por ahí; pero el dato que necesita ya existe en el mismo
servicio, no hace falta pedirlo de nuevo.

**Comportamiento ante sesión ausente/vencida (Edge Case de spec.md)**: si
`auth.token()` es `null` (sin sesión) la vista no intenta conectar y
muestra el mismo patrón de aviso que el resto de la aplicación; si el
WebSocket se cierra con un código de rechazo (ya manejado hoy,
`evento.code >= 4000`) se interpreta como sesión inválida y se redirige a
`/login`, igual que hace `authInterceptor` ante un 401 de HTTP.

**Alternativas consideradas**: (a) cambiar el backend para que el
WebSocket acepte el token por header en el handshake — rechazado, el
protocolo WebSocket del navegador no permite headers custom en el
handshake inicial sin una librería adicional, y esto es un sprint de
frontend, no de backend; (b) usar una cookie de sesión en vez de query
param — rechazado, cambiaría el modelo de sesión completo (JWT en
`localStorage` vs. cookie httpOnly) que S1.10 ya decidió y hoy no está en
discusión.

## Decisión 4 — Transición de color fija en 150ms, sin librería de animación

**Decisión**: la barra de estado de `.ah-tira` usa
`transition: background-color 150ms ease` en CSS plano, respetando la
regla global `prefers-reduced-motion` ya definida en `styles.scss` (S1.10,
anula toda duración de transición/animación a 0.001ms).

**Razón**: es la única animación nueva permitida por
`DIRECCION_VISUAL.md` §2.5 — una transición CSS declarativa es la forma
más simple de lograrla; no hay justificación para introducir una
librería de animación (Framer Motion, GSAP) por un solo efecto de color.

**Alternativas consideradas**: animar mediante Angular Animations —
rechazado, Angular Animations añade una dependencia y complejidad de
API que una transición CSS ya cubre por completo para este caso.

## Decisión 5 — Fuente IBM Plex Mono: verificar carga antes de asumirla

**Decisión**: revisar `apps/web/src/index.html` (o el mecanismo de carga
de fuentes que S1.10 haya usado para IBM Plex Sans) y agregar el peso de
IBM Plex Mono si falta, en vez de asumir que ya está disponible.

**Razón**: S1.10 estableció `--ah-font-mono` en `styles.scss` pero
ninguna vista de auth usa dato tabular pesado (son formularios, no
tablas) — es posible que la fuente nunca se haya cargado de verdad y el
`font-family` caiga a su fallback (`ui-monospace`). Verificarlo empieza
la Fase 1 de implementación, no se asume en el plan.

**Alternativas consideradas**: ninguna — es una verificación, no una
decisión de diseño en disputa.
