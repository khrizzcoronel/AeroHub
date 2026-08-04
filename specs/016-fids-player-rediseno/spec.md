# Feature Specification: Rediseño de fids-player/pantalla-player

**Feature Branch**: `016-fids-player-rediseno`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "S1.14 -- Rediseño de fids-player/pantalla-player (M2 FIDS). Cuarto y último sprint del rediseño de interfaz. Aplicar el sistema de diseño ya construido en apps/web a la única vista de apps/fids-player, hoy HTML sin ningún estilo. Restricciones distintas a las de apps/web: se ve a 3+ metros sin interacción, corre 24/7 sin usuario humano de por vida, tipografía enorme, contraste máximo, cero elementos de interfaz de consola. El formulario de conexión (código de pantalla + token JWT pegado a mano) sigue siendo necesario -- no es deuda técnica aquí, es el mecanismo real de configuración inicial, y se rediseña como una pantalla de configuración separada del modo de reproducción. Debe manejar correctamente el estado 'sin señal' -- hoy el error de conexión WS solo se muestra como texto de error genérico. Sin backend nuevo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el contenido de la pantalla FIDS a distancia, sin ambigüedad (Priority: P1)

Un pasajero o empleado del aeropuerto mira una pantalla FIDS física desde
varios metros de distancia, de pie, en movimiento, sin tiempo de
detenerse a leer con atención. Hoy la pantalla en modo reproducción
muestra texto plano sin jerarquía, del mismo tamaño que cualquier
párrafo web -- ilegible a esa distancia. Necesita que el contenido de la
plantilla activa (filas de texto: vuelo, hora, puerta, estado) se lea de
un vistazo, con el mismo criterio de "densidad, no aire" que el resto
del sistema pero llevado al extremo de tipografía y contraste que exige
una pantalla pública.

**Why this priority**: Es la razón de existir de la aplicación completa
-- sin esto, nada más importa.

**Independent Test**: Conectar una pantalla con una plantilla real
(filas de texto de un vuelo) y confirmar que el contenido es legible a
3+ metros, con jerarquía visual clara entre los distintos campos.

**Acceptance Scenarios**:

1. **Given** una pantalla conectada con una plantilla activa, **When**
   se observa en modo reproducción, **Then** el contenido se presenta en
   tipografía monoespaciada de tamaño mucho mayor al de cualquier vista
   administrativa, sobre fondo de alto contraste.
2. **Given** el modo reproducción, **When** se observa la pantalla,
   **Then** no hay ningún elemento de interfaz de consola visible
   (botones, formularios, tablas administrativas) -- solo el contenido
   de la plantilla.
3. **Given** una actualización de plantilla en tiempo real, **When**
   llega por WebSocket, **Then** el contenido se actualiza sin parpadeo
   ni recarga de página perceptible.
4. **Given** una plantilla cuyo `definicion_json` no sigue la
   convención `filas: [{texto}]`, **When** se recibe, **Then** se
   presenta un respaldo legible (no la estructura JSON cruda como hoy).

---

### User Story 2 - Configurar una pantalla nueva sin ambigüedad sobre qué modo está activo (Priority: P2)

Una persona de operaciones instala físicamente una pantalla FIDS nueva
(o reconecta una existente tras un reinicio) y necesita ingresar su
código de pantalla y el token de acceso. Hoy ese formulario y el
contenido en reproducción comparten la misma pantalla sin ninguna
separación visual -- no está claro cuándo termina la configuración y
empieza la reproducción real. Como no existe un login humano en esta
aplicación (a diferencia de `apps/web`), este formulario seguirá siendo
la única vía de conexión.

**Why this priority**: Se usa con muchísima menor frecuencia que el
modo reproducción (una vez por instalación o reinicio), pero un fallo
aquí bloquea todo lo demás.

**Independent Test**: Conectar una pantalla con un código y token
válidos desde el formulario de configuración, y confirmar que la
transición a modo reproducción es clara e inequívoca.

**Acceptance Scenarios**:

1. **Given** la aplicación recién cargada, **When** todavía no se
   conectó ninguna pantalla, **Then** se presenta una pantalla de
   configuración claramente distinta del modo reproducción (otra
   composición visual, no solo un formulario flotando sobre el
   contenido).
2. **Given** el formulario de configuración completado con datos
   inválidos, **When** se intenta conectar, **Then** el error se
   presenta con claridad dentro de la misma pantalla de configuración,
   sin pasar a modo reproducción.
3. **Given** una conexión exitosa, **When** se recibe la primera
   plantilla, **Then** la aplicación transiciona a modo reproducción de
   forma completa (la pantalla de configuración deja de ser visible).

---

### User Story 3 - Reconocer cuándo una pantalla dejó de recibir datos (Priority: P3)

Una persona de operaciones o soporte observa una pantalla FIDS física y
necesita poder distinguir, de un vistazo, si esa pantalla está mostrando
información vigente o si perdió la conexión y está mostrando contenido
obsoleto. Hoy, si el WebSocket se cierra o falla, solo aparece un texto
de error genérico superpuesto o nada distinguible -- el dominio ya
define un estado `sin_senal` para esto, pero la pantalla nunca lo
comunica de forma dedicada.

**Why this priority**: Es un caso de error, no el camino feliz -- pero
su ausencia hoy es un riesgo operativo real (una pantalla "congelada"
que parece viva).

**Independent Test**: Forzar el cierre de la conexión WebSocket (o
dejar de enviar heartbeats exitosos) y confirmar que la pantalla
transiciona a un estado visual de "sin señal" propio, distinto del
contenido normal y del formulario de configuración.

**Acceptance Scenarios**:

1. **Given** una pantalla en modo reproducción, **When** la conexión
   WebSocket se cierra de forma anómala, **Then** se presenta un estado
   visual de "sin señal" con su propia composición (no un texto de error
   flotando sobre el último contenido).
2. **Given** el estado de "sin señal", **When** la conexión se
   restablece y llega una plantilla nueva, **Then** la pantalla vuelve
   al modo reproducción normal automáticamente.
3. **Given** el estado de "sin señal", **When** se observa, **Then** es
   distinguible del estado de configuración inicial (uno implica "nunca
   se conectó", el otro "se conectó y perdió señal").

---

### Edge Cases

- ¿Qué pasa si la plantilla activa no tiene ninguna fila (`filas: []`)?
  Estado vacío explícito, no una pantalla en blanco sin explicación.
- ¿Qué pasa si el heartbeat falla pero el WebSocket sigue abierto? Se
  documenta como comportamiento asumido en Assumptions -- no hay
  información suficiente en el sistema actual para diferenciarlo de una
  señal íntegra sin construir lógica de backend nueva.
- ¿Qué pasa si se pierde la señal y se recupera en menos de un
  heartbeat? No debe alcanzar a mostrarse el estado "sin señal" de forma
  perceptible (evitar parpadeo ante cortes de red intermitentes muy
  breves).
- ¿Qué pasa en una pantalla más pequeña de lo esperado (viewport
  angosto)? Sigue siendo el mismo modo reproducción de alto contraste,
  sin adaptar a un layout tipo "app móvil" -- esta aplicación no corre
  en teléfonos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El modo reproducción DEBE presentar el contenido de la
  plantilla activa en tipografía monoespaciada de tamaño legible a 3
  o más metros de distancia.
- **FR-002**: El modo reproducción NO DEBE mostrar ningún elemento de
  interfaz de consola (botones, formularios, tablas administrativas,
  controles de navegación).
- **FR-003**: La actualización de contenido en tiempo real (vía
  WebSocket) DEBE reflejarse sin recarga de página ni parpadeo
  perceptible.
- **FR-004**: El formulario de conexión (código de pantalla + token)
  DEBE mantenerse funcionalmente idéntico al actual -- mismos campos,
  mismo mecanismo de autenticación -- y presentarse en una composición
  visual propia, claramente distinta del modo reproducción.
- **FR-005**: El sistema DEBE presentar un estado visual dedicado de
  "sin señal", distinto del modo reproducción normal y de la pantalla
  de configuración, cuando la conexión WebSocket se cierra de forma
  anómala.
- **FR-006**: El sistema DEBE volver automáticamente al modo
  reproducción normal al recibir contenido nuevo tras un estado de "sin
  señal", sin intervención manual.
- **FR-007**: El sistema DEBE presentar un respaldo legible cuando
  `definicion_json` no sigue la convención `filas: [{texto}]` conocida,
  en vez de mostrar la estructura JSON cruda.
- **FR-008**: El sistema DEBE reutilizar los tokens de color y
  tipografía ya definidos en `apps/web/src/styles.scss` (semáforo
  operacional, IBM Plex Sans/Mono) -- no define una paleta nueva.
- **FR-009**: Este sprint NO DEBE requerir cambios de backend, de
  contrato HTTP/WebSocket, ni de esquema -- es un sprint exclusivo de
  presentación, igual que S1.11-S1.13.
- **FR-010**: El estado "sin señal" transitorio (corte de red menor a
  la duración de un ciclo de heartbeat) NO DEBE alcanzar a mostrarse de
  forma perceptible.

### Key Entities

- **Pantalla**: dispositivo físico FIDS identificado por código, con un
  estado de dominio (`en_linea`/`sin_senal`/`mantenimiento`) que hoy solo
  se consulta al conectar, no se empuja por WebSocket.
- **Plantilla / `definicion_json`**: contenido activo a mostrar, JSON
  libre cuya convención más común es una lista de filas de texto.
- **Evento de plantilla**: mensaje WebSocket con la definición
  actualizada y su marca de tiempo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona puede leer el contenido de una plantilla real
  (vuelo, hora, puerta, estado) desde 3 o más metros de distancia, sin
  acercarse.
- **SC-002**: En modo reproducción, ninguna captura de pantalla real
  contiene un elemento de interfaz de consola visible.
- **SC-003**: Ante un corte de conexión real (simulado cerrando el
  WebSocket), la pantalla comunica "sin señal" en menos de un ciclo de
  heartbeat (≤ 15 s) y se recupera automáticamente al restablecerse la
  conexión.
- **SC-004**: Con este sprint cerrado, `apps/web` y `apps/fids-player`
  --las dos aplicaciones del rediseño-- comparten el mismo sistema de
  tokens visuales, cerrando por completo el rediseño de interfaz
  iniciado en S1.11.

## Assumptions

- El sistema de diseño (tokens de `apps/web/src/styles.scss`) ya existe
  y no se vuelve a decidir -- este sprint lo extiende al contexto de
  pantalla pública, con tamaños de tipografía mucho mayores a los de
  cualquier vista administrativa.
- El formulario de conexión con token JWT pegado a mano NO es deuda
  técnica en esta aplicación (a diferencia de las 4 vistas de `apps/web`
  corregidas en S1.11) -- esta app no tiene `AuthService` ni login
  humano, así que es el mecanismo real de configuración de una pantalla
  física, y se mantiene funcionalmente igual.
- El estado "sin señal" se infiere enteramente en el cliente (cierre
  anómalo del WebSocket o ausencia de heartbeat exitoso) porque el
  backend no empuja hoy cambios de `estado` de pantalla por WebSocket;
  construir ese push es explícitamente fuera de alcance (sin backend
  nuevo, FR-009).
- No se toca ningún backend, endpoint, ni esquema en este sprint.
- Es la última vista pendiente del rediseño de interfaz (S1.11-S1.14);
  con este sprint cerrado no queda ninguna vista sin estilo en ninguna
  de las dos aplicaciones.
