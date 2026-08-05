# Feature Specification: Soporte D6

**Feature Branch**: `022-soporte-d6`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "Sprint S1.20 -- Soporte D6 (PLAN v3.0 §8-bis.6). Dar superficie en apps/web a los 11 endpoints de aerohub_support construidos en S1.8, que hoy solo existen por API. Bandeja de tickets con SLA visible, hilo de conversación, cambio de estado, base de conocimientos con búsqueda y publicación, changelog publicable a tenants. Observabilidad de uptime queda fuera (Grafana ya lo resuelve). Cierra la Fase 1.5."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bandeja de tickets con SLA y conversación (Priority: P1)

Un agente de soporte abre la bandeja de tickets, ve el estado, la
severidad y cuánto tiempo le queda (o le quedó) para la primera
respuesta según el SLA, entra a un ticket para leer el hilo de
mensajes, responde (o deja una nota interna que el tenant nunca ve) y
cambia el estado del ticket a medida que avanza el caso.

**Why this priority**: Es el flujo central del departamento D6 — sin
esto, el equipo de soporte sigue dependiendo de herramientas externas
o de pegar peticiones HTTP a mano, exactamente la brecha que motiva la
Fase 1.5 completa.

**Independent Test**: Puede probarse íntegramente creando un ticket
(vía API o desde una vista de creación), abriéndolo en la bandeja,
respondiendo y cambiando su estado hasta `cerrado`, y verificando que
cada paso se refleja en la lista y en el detalle.

**Acceptance Scenarios**:

1. **Given** un ticket recién creado con severidad `alta`, **When** el
   agente abre la bandeja, **Then** ve el ticket con su severidad,
   estado `abierto` y el tiempo restante para la primera respuesta
   calculado a partir de `sla_objetivo_min`.
2. **Given** un ticket cuyo tiempo de primera respuesta ya venció,
   **When** el agente lo ve en la bandeja, **Then** el indicador de SLA
   muestra que está vencido, no un número negativo sin explicar.
3. **Given** un ticket abierto, **When** el agente escribe una
   respuesta visible al tenant, **Then** el mensaje aparece en el hilo
   con su autor y hora, y queda registrada la primera respuesta si era
   la primera.
4. **Given** un ticket abierto, **When** el agente escribe una nota
   marcada como interna, **Then** el mensaje se distingue visualmente
   de los mensajes visibles al tenant.
5. **Given** un ticket en estado `abierto`, **When** el agente intenta
   cambiarlo directamente a `resuelto`, **Then** el sistema rechaza la
   transición porque no es válida (debe pasar por `en_progreso`
   primero) y explica por qué.
6. **Given** un ticket en estado `en_progreso`, **When** el agente lo
   cambia a `resuelto` y luego a `cerrado`, **Then** ambas transiciones
   se aceptan y el ticket refleja el nuevo estado en la bandeja.

---

### User Story 2 - Base de conocimientos compartida (Priority: P2)

Un agente de soporte busca un artículo existente por texto o etiqueta
antes de responder un ticket repetido, y publica un artículo nuevo
cuando encuentra una solución que vale la pena documentar para el
futuro — sabiendo en todo momento que ese artículo es visible para
cualquier tenant, no solo para el suyo.

**Why this priority**: Reduce el tiempo de resolución de tickets
repetidos, pero no es indispensable para operar el flujo central de
tickets (US1) el primer día.

**Independent Test**: Puede probarse publicando un artículo con un
título y etiqueta conocidos, buscándolo por texto y por etiqueta, y
confirmando que la interfaz advierte explícitamente que el contenido
es compartido entre tenants.

**Acceptance Scenarios**:

1. **Given** la base de conocimientos vacía o con artículos previos,
   **When** el agente publica un artículo nuevo con título, cuerpo y
   etiquetas, **Then** el artículo aparece en el listado con su versión
   inicial.
2. **Given** artículos publicados, **When** el agente busca por una
   palabra del título o del cuerpo, **Then** ve solo los artículos que
   coinciden.
3. **Given** artículos publicados con distintas etiquetas, **When** el
   agente filtra por una etiqueta, **Then** ve solo los artículos que
   la tienen.
4. **Given** cualquier pantalla de la base de conocimientos, **When**
   el agente la abre, **Then** ve un aviso explícito de que el
   contenido es compartido entre todos los tenants (no aislado por
   tenant como el resto de la aplicación).

---

### User Story 3 - Changelog publicable a tenants (Priority: P3)

Un responsable de producto publica una entrada de changelog cuando
sale una mejora o corrección, describiendo qué módulo cambió y de qué
tipo fue el cambio, y cualquier persona autenticada puede consultar el
historial de versiones publicadas.

**Why this priority**: Es informativo, no bloquea ninguna operación
diaria de soporte — cierra la superficie pendiente pero tiene el menor
impacto de los tres flujos.

**Independent Test**: Puede probarse publicando una entrada de
changelog con al menos un ítem asociado a un módulo, y confirmando que
aparece en el listado con su resumen y sus ítems.

**Acceptance Scenarios**:

1. **Given** un formulario de changelog, **When** el responsable
   completa versión, resumen y al menos un ítem (módulo + tipo de
   cambio + descripción), **Then** la entrada se publica y aparece en
   el listado, más reciente primero.
2. **Given** entradas de changelog publicadas, **When** cualquier
   usuario autenticado con acceso a soporte abre el listado, **Then**
   ve todas las entradas con sus ítems agrupados por entrada.

---

### Edge Cases

- Un ticket sin ninguna respuesta todavía: el indicador de SLA debe
  mostrarse igual, calculado desde `creado_en`, no desde
  `primera_respuesta_en` (que es `null`).
- Un intento de transición de estado inválida (p. ej. `cerrado` →
  `en_progreso`) se rechaza con un mensaje claro, no un error genérico.
- Un rol con `support:leer` pero sin `support:escribir` puede ver la
  bandeja, el hilo y la base de conocimientos, pero no ve los
  controles de responder/cambiar estado/publicar artículo/publicar
  changelog.
- Un mensaje interno nunca se muestra al mismo tiempo que se le da al
  usuario la sensación de que el tenant también lo vería — la
  distinción visual debe ser inequívoca.
- La observabilidad de uptime (`GET /support/observabilidad/uptime`)
  queda deliberadamente sin vista propia — decisión de producto ya
  tomada, documentada como "sin consumidor por diseño".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST mostrar una bandeja de tickets con
  estado, severidad y tiempo restante (o vencido) para la primera
  respuesta, calculado a partir de `sla_objetivo_min` y, si existe,
  `primera_respuesta_en`.
- **FR-002**: El sistema MUST permitir filtrar la bandeja por estado y
  por severidad.
- **FR-003**: El sistema MUST mostrar el detalle de un ticket con su
  hilo completo de mensajes, distinguiendo visualmente los mensajes
  internos de los visibles al tenant.
- **FR-004**: El sistema MUST permitir responder un ticket, marcando
  opcionalmente el mensaje como interno.
- **FR-005**: El sistema MUST permitir cambiar el estado de un ticket
  únicamente entre las transiciones válidas (`abierto`→`en_progreso`,
  `en_progreso`↔`esperando_cliente`, `en_progreso`→`resuelto`,
  `resuelto`→`cerrado`), y MUST mostrar un mensaje de error claro
  cuando el backend rechaza una transición inválida.
- **FR-006**: El sistema MUST permitir buscar artículos de la base de
  conocimientos por texto libre y/o por etiqueta.
- **FR-007**: El sistema MUST permitir publicar un artículo nuevo con
  título, cuerpo y etiquetas.
- **FR-008**: El sistema MUST mostrar de forma explícita e inequívoca
  que la base de conocimientos es contenido compartido entre todos los
  tenants, no aislado por tenant.
- **FR-009**: El sistema MUST permitir publicar una entrada de
  changelog con versión de producto, resumen y uno o más ítems (cada
  uno asociado a un módulo M1-M9 y a un tipo de cambio).
- **FR-010**: El sistema MUST mostrar el listado de changelog
  publicado, con sus ítems visibles por entrada.
- **FR-011**: El sistema MUST ocultar los controles de escritura
  (responder, cambiar estado, publicar artículo, publicar changelog) a
  cualquier sesión sin el permiso de escritura correspondiente, aunque
  pueda seguir leyendo.
- **FR-012**: El sistema MUST NOT construir una vista propia para la
  observabilidad de uptime/error budget — se considera resuelta por la
  herramienta de observabilidad ya existente fuera de esta aplicación.

### Key Entities *(include if feature involves data)*

- **Ticket**: caso de soporte abierto por o para un tenant; tiene
  categoría, severidad, estado, objetivo de SLA en minutos, y
  timestamps de creación/primera respuesta/resolución.
- **Mensaje de ticket**: entrada del hilo de conversación de un
  ticket; tiene autor, cuerpo, momento de envío, y si es interno o
  visible al tenant.
- **Artículo de base de conocimientos**: contenido compartido entre
  todos los tenants (sin aislamiento propio); tiene título, cuerpo,
  versión, etiquetas y momento de publicación.
- **Entrada de changelog**: versión de producto publicada, con un
  resumen y una lista de ítems, cada uno asociado a un módulo y a un
  tipo de cambio (nuevo, mejora, corrección, obsolescencia).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un agente de soporte puede ver, responder y cerrar un
  ticket de punta a punta sin salir de la aplicación ni pegar
  peticiones HTTP a mano.
- **SC-002**: El tiempo restante o vencido de SLA es visible en la
  bandeja sin que el agente tenga que abrir el detalle del ticket.
- **SC-003**: Un agente encuentra un artículo relevante de la base de
  conocimientos en menos de 3 interacciones (búsqueda + selección).
- **SC-004**: El 100% de las pantallas de base de conocimientos deja
  explícito que el contenido no está aislado por tenant.
- **SC-005**: Una entrada de changelog publicada es visible para
  cualquier usuario autenticado con acceso a soporte, sin pasos
  adicionales.

## Assumptions

- El backend de `aerohub_support` (S1.8) no requiere cambios: los 11
  endpoints necesarios ya existen y ya fueron verificados contra
  MonetDB real en su sprint original.
- Los scopes `support:leer`/`support:escribir` ya están asignados a
  los roles que deben operar esta vista (`role_sre`, `role_support`,
  `role_tenant_admin`) — se confirma antes de implementar, sin asumido
  como hallazgo pendiente de corrección.
- No existe una ruta libre de módulo M1-M9 para esta vista (D6 no es
  un módulo licenciable); se expone como enlace manual del menú,
  igual que tarifarios/informes en sprints anteriores.
- La vista de observabilidad de uptime queda fuera de alcance por
  decisión de producto ya tomada (Grafana la resuelve).
- Verificación en navegador real solo si el usuario lo pide
  explícitamente (regla de trabajo vigente desde S1.16).
