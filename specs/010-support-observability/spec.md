# Feature Specification: Soporte D6 y observabilidad

**Feature Branch**: `010-support-observability`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Sprint S1.8 del docs/PLAN_IMPLEMENTACION_v2.0.md §8.8: Soporte D6 y observabilidad. Objetivo: cerrar la vertical de soporte y la observabilidad que alimenta el BSC. Modulo: services/support. Requisitos: RF-O08, RF-O10, RF-O11, RF-O14, RF-E03 (base), RNF-R02, RNF-R03. Entregables: support.categoria_ticket, ticket (sla_objetivo_min, primera_respuesta_en), ticket_mensaje (hilo), articulo_kb (sin tenant_id), etiqueta, articulo_kb_etiqueta, changelog, changelog_item; pila LGTM con dashboards de uptime AODB/FIDS, error budget y alertas Sev1-Sev3; bloqueo automatico de despliegues al superar el 80% del error budget."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestión de tickets de soporte con SLA (Priority: P1)

Un usuario de un tenant reporta un problema con AODB, FIDS o rampa. Un especialista de soporte (`role_support`) recibe el ticket, lo categoriza, conversa con el tenant en un hilo de mensajes y lo resuelve dentro del plazo de SLA correspondiente a la severidad y el módulo afectado.

**Why this priority**: Es el requisito obligatorio (RF-O08, prioridad M en el SRS) y la vertical D6 no existe sin esto — sin gestión de tickets no hay soporte operativo formal, solo comunicación informal no trazable.

**Independent Test**: Puede probarse íntegramente creando un ticket como usuario de un tenant, respondiendo como `role_support`, y verificando que el sistema registra `primera_respuesta_en` y compara contra `sla_objetivo_min` — sin depender de observabilidad ni de la base de conocimientos.

**Acceptance Scenarios**:

1. **Given** un tenant con un vuelo AODB retrasado por un error del sistema, **When** su usuario crea un ticket de severidad "alta", **Then** el sistema le asigna `sla_objetivo_min` según el módulo afectado (< 120 min para AODB/FIDS, < 240 min para rampa) y el ticket queda visible para `role_support`.
2. **Given** un ticket abierto sin respuesta, **When** un especialista de soporte publica el primer mensaje en el hilo, **Then** el sistema registra `primera_respuesta_en` una única vez (mensajes posteriores no la modifican).
3. **Given** un hilo de ticket con mensajes internos y mensajes visibles para el cliente, **When** el tenant consulta su ticket, **Then** solo ve los mensajes marcados como no internos.
4. **Given** un especialista de soporte autenticado, **When** intenta acceder a datos de facturación de un tenant a través del flujo de soporte, **Then** el sistema no expone esa información (segregación de funciones D6, ya vigente desde S1.6).

---

### User Story 2 - Visibilidad de uptime y consumo de error budget (Priority: P1)

Un responsable de operaciones necesita ver, en cualquier momento, el uptime mensual de AODB y FIDS y cuánto error budget llevan consumido, sin tener que pedirle el dato a Ingeniería.

**Why this priority**: RF-E03 y RNF-R02 son prioridad M — es el panel base que alimenta el BSC (OE3) y la precondición para que el bloqueo automático de despliegues (User Story 3) tenga un dato del cual disparar.

**Independent Test**: Puede probarse de forma aislada verificando que, tras un período con incidentes simulados de disponibilidad, el panel refleja el porcentaje de uptime del mes y el porcentaje de error budget consumido, sin necesidad de que el bloqueo de despliegues esté implementado.

**Acceptance Scenarios**:

1. **Given** un mes calendario con cierta cantidad de tiempo de indisponibilidad registrada en AODB, **When** un responsable de operaciones abre el panel de uptime, **Then** ve el porcentaje de uptime del mes en curso y el porcentaje de error budget consumido, con granularidad mensual.
2. **Given** un incidente de severidad Sev1 en curso, **When** se dispara la alerta correspondiente, **Then** el responsable de guardia la recibe con la severidad correcta (Sev1/Sev2/Sev3) sin demora significativa.
3. **Given** el uptime real del mes iguala exactamente el objetivo de SLA (99.9 % en MVP), **When** se consulta el panel, **Then** el consumo de error budget reportado es 100 % (el budget se agotó exactamente, sin margen).

---

### User Story 3 - Bloqueo automático de despliegues por error budget (Priority: P2)

Cuando el consumo de error budget de un servicio crítico supera el 80 % del presupuesto mensual, la plataforma bloquea automáticamente nuevos despliegues sobre ese servicio hasta que una persona autorizada lo libere explícitamente, dejando constancia del motivo.

**Why this priority**: RF-O10/RNF-R03 son prioridad S — dependen de que exista el cálculo de error budget de la User Story 2. Es el mecanismo de contención, no la visibilidad en sí.

**Independent Test**: Puede probarse en un escenario simulado fijando el consumo de error budget de un servicio por encima del 80 % y verificando que un intento de despliegue sobre ese servicio es rechazado, y que una persona autorizada puede levantar el bloqueo dejando un motivo auditado.

**Acceptance Scenarios**:

1. **Given** un servicio cuyo error budget mensual lleva 79 % de consumo, **When** el consumo cruza el 80 %, **Then** el siguiente intento de despliegue sobre ese servicio es rechazado automáticamente.
2. **Given** un despliegue bloqueado por error budget, **When** una persona con autorización de plataforma decide continuar de todas formas, **Then** puede levantar el bloqueo únicamente dejando un motivo explícito, y esa acción queda auditada.
3. **Given** el error budget de un servicio se repone al iniciar un nuevo mes, **When** comienza el nuevo período, **Then** el bloqueo se levanta automáticamente sin intervención manual.

---

### User Story 4 - Base de conocimientos con etiquetado (Priority: P3)

El equipo de soporte publica artículos de la base de conocimientos, compartidos entre todos los tenants, organizados con etiquetas normalizadas para que un tenant pueda resolver dudas comunes sin abrir un ticket.

**Why this priority**: RF-O14 es prioridad C (deseable) — mejora la eficiencia del soporte pero no bloquea el resto de la vertical D6.

**Independent Test**: Puede probarse publicando un artículo con una o más etiquetas y verificando que aparece indexado y recuperable por texto y por etiqueta, independientemente de si hay tickets o changelog cargados.

**Acceptance Scenarios**:

1. **Given** un especialista de soporte con un artículo en estado "borrador", **When** lo publica, **Then** el artículo queda visible para todos los tenants con su fecha de publicación registrada.
2. **Given** un artículo publicado con varias etiquetas, **When** un tenant busca por una de esas etiquetas, **Then** el artículo aparece en los resultados.
3. **Given** un artículo con una nueva versión, **When** se publica la versión siguiente, **Then** ambas versiones quedan identificables por separado (no se sobrescribe la anterior).

---

### User Story 5 - Publicación de changelog (Priority: P3)

El equipo de producto publica el changelog de cada versión, desglosado en ítems por módulo y tipo de cambio, visible para todos los tenants en el portal.

**Why this priority**: RF-O11 es prioridad C (deseable) — es la vertical de menor impacto directo en SLA/BSC entre las incluidas en este sprint.

**Independent Test**: Puede probarse publicando una entrada de changelog con varios ítems y verificando que es visible para un tenant en el portal, sin depender de tickets, KB ni observabilidad.

**Acceptance Scenarios**:

1. **Given** una nueva versión del producto, **When** se publica su changelog con ítems desglosados por módulo y tipo de cambio ("nuevo", "mejora", "corrección", "obsolescencia"), **Then** queda visible para todos los tenants en el portal.
2. **Given** un changelog ya publicado, **When** un tenant lo consulta, **Then** ve el resumen y cada ítem asociado a su módulo correspondiente, sin importar si ese tenant tiene licencia vigente para ese módulo.

### Edge Cases

- ¿Qué pasa si un ticket se resuelve sin que nunca se haya registrado `primera_respuesta_en` (p. ej. se cierra directamente)? El sistema debe seguir permitiendo el cierre, mostrando el SLA de primera respuesta como incumplido.
- ¿Qué pasa si el consumo de error budget se recalcula y baja de 80 % mientras el despliegue sigue bloqueado por una liberación manual pendiente? El bloqueo automático se levanta solo, independientemente de liberaciones manuales previas.
- ¿Qué pasa si dos especialistas de soporte responden al mismo ticket casi simultáneamente? Ambos mensajes se conservan en el hilo; `primera_respuesta_en` solo se fija con el primero en persistir.
- ¿Qué pasa si se intenta etiquetar un artículo con una etiqueta que no existe? Debe rechazarse o crear la etiqueta primero — no se admiten etiquetas huérfanas fuera del catálogo de `etiqueta`.
- ¿Qué pasa con un artículo archivado? Deja de aparecer en las búsquedas de tenants pero se conserva para auditoría interna.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir a un usuario de un tenant crear un ticket de soporte asociado a una categoría, con severidad ('baja','media','alta','critica') y asunto.
- **FR-002**: El sistema MUST asignar automáticamente un `sla_objetivo_min` al crear el ticket, según el módulo afectado (< 120 min para AODB/FIDS, < 240 min para rampa).
- **FR-003**: El sistema MUST registrar `primera_respuesta_en` la primera vez que `role_support` publica un mensaje en el ticket, y no debe modificarse en respuestas posteriores.
- **FR-004**: El sistema MUST soportar un hilo de mensajes por ticket (`ticket_mensaje`), cada uno marcable como interno (no visible al tenant) o visible al cliente.
- **FR-005**: El sistema MUST impedir que el flujo de soporte exponga datos financieros/facturación a `role_support` (segregación de funciones D6).
- **FR-006**: El sistema MUST calcular y exponer el uptime mensual de los servicios críticos (AODB, FIDS) con granularidad mensual.
- **FR-007**: El sistema MUST calcular el consumo de error budget de cada servicio crítico contra su objetivo de SLA de uptime (99.9 % MVP / 99.95 % Scale).
- **FR-008**: El sistema MUST emitir alertas diferenciadas por severidad (Sev1, Sev2, Sev3) cuando ocurre un incidente de disponibilidad.
- **FR-009**: El sistema MUST bloquear automáticamente nuevos despliegues sobre un servicio cuando su consumo de error budget del período supere el 80 %.
- **FR-010**: El sistema MUST permitir a un rol autorizado de plataforma levantar manualmente un bloqueo de despliegue, exigiendo un motivo explícito que quede auditado.
- **FR-011**: El sistema MUST reponer el error budget y levantar automáticamente cualquier bloqueo asociado al iniciar cada nuevo período mensual.
- **FR-012**: El sistema MUST permitir publicar artículos de base de conocimientos (`articulo_kb`) sin asociarlos a ningún tenant específico (conocimiento compartido).
- **FR-013**: El sistema MUST permitir versionar un artículo de base de conocimientos, conservando versiones anteriores identificables por separado.
- **FR-014**: El sistema MUST permitir etiquetar artículos de la base de conocimientos con etiquetas normalizadas del catálogo `etiqueta`, y permitir buscar artículos publicados por etiqueta o texto.
- **FR-015**: El sistema MUST permitir publicar entradas de changelog (`changelog`) con ítems (`changelog_item`) asociados a un módulo del catálogo y a un tipo de cambio ('nuevo','mejora','correccion','obsolescencia').
- **FR-016**: El sistema MUST hacer visible el changelog publicado a todos los tenants, sin condicionarlo a que el tenant tenga licencia vigente del módulo referenciado.

### Key Entities

- **CategoriaTicket**: catálogo de categorías de ticket (código, nombre).
- **Ticket**: solicitud de soporte de un tenant; severidad, estado, SLA objetivo, marcas de tiempo de primera respuesta y resolución, agente asignado.
- **TicketMensaje**: mensaje individual dentro del hilo de un ticket; autor, cuerpo, visibilidad (interno/cliente).
- **ArticuloKB**: artículo de base de conocimientos, sin tenant; título, cuerpo, versión, estado de publicación, autor, puntero a búsqueda semántica futura.
- **Etiqueta**: etiqueta normalizada reutilizable entre artículos.
- **ArticuloKbEtiqueta**: asociación muchos-a-muchos entre artículo y etiqueta.
- **Changelog**: entrada de versión de producto; versión, resumen, fecha de publicación.
- **ChangelogItem**: ítem individual de un changelog, asociado a un módulo y a un tipo de cambio.
- **PresupuestoDeError (concepto derivado)**: consumo de error budget de un servicio crítico en el período en curso, calculado a partir del uptime observado contra el objetivo de SLA.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 95 % de los tickets de severidad alta/crítica sobre AODB o FIDS reciben primera respuesta en menos de 2 horas.
- **SC-002**: El 95 % de los tickets de severidad alta/crítica sobre rampa reciben primera respuesta en menos de 4 horas.
- **SC-003**: Un responsable de operaciones puede conocer el uptime y el consumo de error budget del mes en curso para AODB/FIDS sin solicitar el dato a Ingeniería.
- **SC-004**: El 100 % de los intentos de despliegue sobre un servicio con más de 80 % de error budget consumido son rechazados automáticamente, verificado en escenario simulado.
- **SC-005**: Un tenant puede encontrar un artículo publicado de la base de conocimientos relevante a su duda mediante texto o etiqueta, sin necesidad de abrir un ticket.
- **SC-006**: Un tenant puede ver el changelog de la versión actual del producto, desglosado por módulo, sin depender de que un especialista de soporte se lo comunique manualmente.

## Assumptions

- El uptime de AODB/FIDS se calcula a partir de métricas ya emitidas por el Gateway y los servicios existentes (tasa de éxito de requests / health checks), sin necesidad de nuevos agentes de sondeo externos.
- El bloqueo de despliegue es una compuerta automatizada en el pipeline de entrega que consulta el consumo de error budget; puede levantarse manualmente solo por un rol de plataforma autorizado, dejando motivo auditado — mismo patrón de excepciones auditadas ya usado en el proyecto (p. ej. `alcance_global`, publicación de post-mortem).
- La búsqueda de la base de conocimientos usa comparación textual (título/cuerpo) para este sprint; `embedding_ref` se persiste desde ahora como puntero reservado para una futura integración de búsqueda semántica, pero la indexación vectorial real queda fuera de alcance de S1.8.
- El "portal de clientes" donde se publican changelog y base de conocimientos es el propio `apps/web` existente — no se crea un portal separado.
- Los umbrales de severidad Sev1–Sev3 y el proceso de post-mortem (<72 h) ya fueron cerrados en S1.7 (`compliance.post_mortem`); S1.8 no los redefine, solo genera las alertas que pueden originar un incidente y alimenta el cálculo de error budget.
- `role_support` puede leer datos de tickets, KB y changelog de cualquier tenant (necesario para atender soporte cross-tenant), pero nunca datos de facturación — la segregación de funciones ya vigente desde S1.6 se mantiene sin cambios.
