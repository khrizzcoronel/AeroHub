# Feature Specification: AODB backend + Angular mínimo -- aprovisionamiento de tenant y alta de vuelo

**Feature Branch**: `main`

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commit `72488fe`

**Input**: Sprint S1.1 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.1. Implementar
CU-O18 (aprovisionar_tenant) y el alta/consulta/cambio de estado de vuelo
(RF-O02 parcial) de extremo a extremo: dominio → aplicación → infraestructura
→ API HTTP real → formulario Angular mínimo funcional.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aprovisionar un tenant nuevo (Priority: P1)

Como `role_platform_admin`, necesito dar de alta un tenant nuevo (aeropuerto
cliente) con su usuario administrador inicial, para que ese aeropuerto pueda
empezar a operar en la plataforma.

**Why this priority**: sin un tenant, no existe ningún dato de negocio
posible -- es el primer paso literal de cualquier operación del sistema.

**Independent Test**: `POST /tenants` con un JWT de `role_platform_admin`
(sin `tenant_id` propio, vía `alcance_global`) crea el tenant y devuelve un
usuario admin con contraseña temporal.

**Acceptance Scenarios**:

1. **Given** un JWT válido de `role_platform_admin`, **When** se envía
   `POST /tenants` con código, razón social, aeropuerto y plan,
   **Then** se crea el tenant y su usuario admin en la misma transacción.
2. **Given** el formulario Angular de alta de tenant, **When** se completa y
   envía contra el backend real, **Then** el tenant aparece en MonetDB con
   los valores EXACTOS ingresados (sin corrupción de precisión en los IDs).

---

### User Story 2 - Dar de alta, consultar y cambiar el estado de un vuelo (Priority: P1)

Como `role_operations_controller`, necesito registrar un vuelo nuevo,
consultarlo por id, y registrar sus cambios de estado (programado →
embarcando → en vuelo → aterrizado, etc.), todo dentro de mi propio tenant.

**Why this priority**: es el núcleo operacional mínimo del AODB (Airport
Operational Database) -- sin esto no hay ningún dato operacional que
gestionar en los sprints siguientes.

**Independent Test**: `POST /vuelos`, `GET /vuelos/{id}`,
`POST /vuelos/{id}/estados` contra el backend real, con las transiciones de
estado validadas por dominio.

**Acceptance Scenarios**:

1. **Given** un vuelo recién creado, **When** se consulta por su id dentro
   del mismo tenant, **Then** se devuelve con los datos exactos.
2. **Given** un vuelo en estado terminal (p. ej. `aterrizado`), **When** se
   intenta registrar un nuevo cambio de estado, **Then** el dominio rechaza
   la transición (`TransicionEstadoInvalida`).

---

### User Story 3 - Un tenant nunca ve ni puede intuir la existencia de un recurso ajeno (Priority: P1)

Como responsable de seguridad, necesito que solicitar un vuelo que pertenece
a OTRO tenant devuelva exactamente el mismo resultado que solicitar un vuelo
que no existe -- 404 en ambos casos, nunca 403 (que confirmaría que el
recurso ajeno existe).

**Why this priority**: es la aplicación end-to-end del guardián de tenant
construido en S0.2 -- si esto falla en la primera API real, el guardián no
sirve de nada en la práctica.

**Independent Test**: PN-01 (recurso de otro tenant → 404, nunca 403) y
PN-02 (`tenant_id` del cuerpo de la petición se ignora, siempre se usa el
del JWT) verificados con peticiones HTTP reales.

**Acceptance Scenarios**:

1. **Given** un vuelo del tenant B, **When** el tenant A lo solicita por id,
   **Then** responde 404 (idéntico a un id inexistente).
2. **Given** una petición `POST /vuelos` con un `tenant_id` distinto al del
   JWT en el cuerpo, **When** se procesa, **Then** el vuelo se crea bajo el
   tenant del JWT, el campo del cuerpo se ignora silenciosamente.

### Edge Cases

- ¿Qué pasa si un id Snowflake de 64 bits se transmite como número JSON
  nativo? Se corrompe en silencio en el navegador por encima de
  `Number.MAX_SAFE_INTEGER` -- reproducido con el formulario Angular real,
  no detectable con pruebas en Python. Resuelto transmitiendo IDs como
  string en ambos sentidos (request y response).
- ¿Qué pasa si `registrar_auditoria()` corre bajo `alcance_global()` (sin
  tenant propio, p. ej. CU-O18)? Debe usar `rol_activo_de_sesion()`, no
  `contexto_rol_actor()` directamente (que asume un tenant ambiente).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE exponer `POST /tenants` que crea un tenant y su
  usuario administrador inicial en una única transacción (CU-O18).
- **FR-002**: El sistema DEBE exponer `POST /vuelos`, `GET /vuelos/{id}`,
  `POST /vuelos/{id}/estados` con autenticación JWT real vía middleware del
  Gateway.
- **FR-003**: Cada módulo de negocio DEBE poseer su propio `infrastructure/`
  (registro G1, tablas, consultas) -- no centralizado en
  `packages/repository` como en S0.2.
- **FR-004**: Todo id Snowflake de 64 bits DEBE viajar como string en JSON
  (request y response), nunca como número nativo.
- **FR-005**: Un recurso de otro tenant DEBE responder 404, nunca 403 (PN-01).
- **FR-006**: El `tenant_id` recibido en el cuerpo de una petición DEBE
  ignorarse siempre -- el tenant real viene del JWT vía
  `contexto_tenant_id()` (PN-02).
- **FR-007**: El dominio DEBE validar las transiciones de estado de vuelo
  (un estado terminal no admite transición posterior).
- **FR-008**: `apps/web` DEBE tener un formulario mínimo funcional de alta de
  tenant, sin login real (JWT pegado a mano).

### Key Entities

- **`Tenant`**: aeropuerto cliente de la plataforma -- código, razón social,
  aeropuerto asociado, plan.
- **`Vuelo`**: entidad núcleo del AODB -- aerolínea, aeronave, número de
  vuelo, tipo, fecha de operación, sentido (L/S), aeropuertos origen/destino,
  horarios previstos/reales.
- **`VueloEstado`**: bitácora append-in-place de transiciones de estado de un
  vuelo -- el estado vigente es el registro más reciente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 186/186 tests (unit/integration/negative/cross_tenant) pasan
  contra MonetDB real.
- **SC-002**: ruff, mypy, bandit y los 15 contratos de `import-linter` en
  verde.
- **SC-003**: build/lint/test de Angular en verde.
- **SC-004**: El formulario de alta de tenant, ejercitado en un navegador
  real contra el backend real, produce datos EXACTOS en MonetDB (sin pérdida
  de precisión de IDs).
- **SC-005**: PN-01 y PN-02 verificados con peticiones HTTP reales, no solo
  unit tests de dominio.

## Assumptions

- No hay login real todavía -- el JWT se pega a mano en un textarea. Esta
  decisión se repite en cada sprint posterior con UI hasta que exista un CU
  de emisión de sesión.
- El middleware de autenticación del Gateway es el mismo para cualquier
  cliente HTTP (formulario Angular o `curl`) -- no hay un atajo de seguridad
  específico para la UI de desarrollo.
