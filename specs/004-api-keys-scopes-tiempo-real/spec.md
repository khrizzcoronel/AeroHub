# Feature Specification: API del AODB -- API Keys, scopes, rate limiting y WebSocket en tiempo real

**Feature Branch**: `main`

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commit `14d75ab`

**Input**: Sprint S1.2 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.2. Exponer el
AODB con contrato formal y propagación en tiempo real (RF-T02, RF-O04,
RNF-P01, RNF-C03).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autenticarse con API Key ademّas de JWT (Priority: P1)

Como sistema externo (no un usuario humano con sesión), necesito autenticarme
con una API Key de larga vida en vez de un JWT de corta vida, para
integraciones máquina-a-máquina que no pasan por un flujo de login.

**Why this priority**: sin esto, cualquier integración externa (partners,
sistemas de aeropuerto) tendría que reautenticar cada 15 minutos -- inviable
para uso no interactivo.

**Independent Test**: `POST /vuelos` con cabecera `X-Api-Key` (en vez de
`Authorization: Bearer`) autentica correctamente y respeta los mismos scopes
que un JWT.

**Acceptance Scenarios**:

1. **Given** una API Key activa y vigente, **When** se usa en `X-Api-Key`,
   **Then** la petición se autentica igual que con JWT.
2. **Given** una API Key revocada, **When** se usa, **Then** responde 401
   (PN-06).
3. **Given** una API Key recién creada, **When** se muestra el secreto,
   **Then** se muestra UNA sola vez -- no se puede recuperar después.

---

### User Story 2 - Proteger cada endpoint con un scope de grano fino (Priority: P1)

Como diseñador de la API, necesito que cada endpoint declare el scope
mínimo que exige (p. ej. `vuelos:leer` vs `vuelos:escribir`), y que un JWT o
API Key sin ese scope sea rechazado, sin filtrar qué scopes SÍ tiene el
llamador.

**Why this priority**: mínimo privilegio real, no solo por rol -- distintos
clientes de un mismo rol pueden necesitar distintos permisos.

**Independent Test**: PN-07 (JWT expirado o scope insuficiente → 401/403 sin
fuga de información) verificado con HTTP real.

**Acceptance Scenarios**:

1. **Given** un JWT con scope `vuelos:leer` pero sin `vuelos:escribir`,
   **When** intenta `POST /vuelos`, **Then** responde 403 sin listar qué
   scopes sí tiene.
2. **Given** un JWT expirado, **When** se usa, **Then** responde 401.

---

### User Story 3 - Ver cambios de estado de vuelo en tiempo real (Priority: P1)

Como controlador de operaciones, necesito ver los cambios de estado de vuelo
de mi tenant en tiempo real, sin refrescar la pantalla, para reaccionar a
demoras o cambios de gate sin retraso.

**Why this priority**: es el primer requisito de "tiempo real" del sistema
(RF-O04) -- sienta el patrón de WebSocket que S1.3 (FIDS) y S1.4/S1.5
(dashboards) reutilizan.

**Independent Test**: WebSocket `/vuelos/ws/estado` recibe el evento de un
cambio de estado en menos de 1 segundo desde que la mutación HTTP confirma
(RNF-P01), medido con 100 cambios concurrentes.

**Acceptance Scenarios**:

1. **Given** una conexión WebSocket abierta con un JWT de scope
   `vuelos:leer`, **When** otro cliente registra un cambio de estado,
   **Then** el WS recibe el evento en menos de 1 segundo.
2. **Given** 100 cambios de estado concurrentes repartidos entre varios
   vuelos, **When** se miden, **Then** la latencia máxima de propagación es
   < 1s (RNF-P01).

---

### User Story 4 - No agotar el sistema con tráfico excesivo (Priority: P2)

Como operador de la plataforma, necesito que un tenant o cliente no pueda
saturar el sistema con peticiones -- un límite de tasa por tenant+rol que
responda 429 al agotarse.

**Why this priority**: protección básica de disponibilidad compartida entre
tenants (RNF-C03).

**Independent Test**: exceder la cuota de peticiones de un tenant+rol
produce 429.

**Acceptance Scenarios**:

1. **Given** un tenant que agota su cupo de peticiones, **When** hace una
   petición adicional, **Then** responde 429.

### Edge Cases

- ¿Qué pasa cuando 100 cambios de estado concurrentes escriben sobre
  tablas TRANSVERSALES compartidas (journal/auditoría, P8), no solo sobre
  filas de negocio distintas? MonetDB aborta transacciones (SQLSTATE 40001)
  incluso repartiendo la carga entre vuelos distintos -- resuelto con
  reintento de la operación completa (backoff + jitter), límite de
  paralelismo sostenible observado ~3 escritores concurrentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE soportar autenticación dual: JWT
  (`Authorization: Bearer`, corta vida de 15 min) o API Key (`X-Api-Key`,
  larga vida).
- **FR-002**: El sistema DEBE permitir crear y revocar API Keys, mostrando
  el secreto en claro una única vez al crearlas.
- **FR-003**: Cada endpoint DEBE declarar su scope mínimo requerido vía
  `requiere_scope` (dependencia FastAPI en `aerohub_contracts`, para que
  cada módulo proteja sus propios endpoints sin importar `aerohub_gateway`).
- **FR-004**: Un scope insuficiente DEBE responder 403 sin revelar qué
  scopes sí tiene el llamador (PN-07).
- **FR-005**: El sistema DEBE limitar la tasa de peticiones por tenant+rol
  (cubo de fichas en memoria), respondiendo 429 al agotar cupo.
- **FR-006**: El sistema DEBE exponer `/vuelos/ws/estado`, un canal
  WebSocket de cambios de estado de vuelo en tiempo real, autenticado con
  JWT por query string (la API WebSocket del navegador no admite cabeceras
  personalizadas).
- **FR-007**: La propagación de un cambio de estado por WebSocket DEBE
  completarse en menos de 1 segundo (RNF-P01), incluso bajo 100 cambios
  concurrentes.
- **FR-008**: El sistema DEBE generar automáticamente su especificación
  OpenAPI 3.1 (`docs/api/openapi.yaml`), validada con Spectral sin errores.
- **FR-009**: `apps/web` DEBE tener una vista mínima que se conecte al
  WebSocket y muestre los cambios en vivo.

### Key Entities

- **`ApiKey`**: prefijo público + hash del secreto, tenant, estado
  (activa/revocada), fecha de expiración opcional.
- **Scope**: string de la forma `<recurso>:<accion>` (p. ej.
  `vuelos:leer`), transportado en el claim `scopes` del JWT o asociado a la
  API Key.
- **`EventoEstadoVuelo`**: evento publicado por el broadcaster en proceso al
  confirmar un cambio de estado, consumido por los suscriptores WS del mismo
  tenant.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 211/211 tests (unit/integration/negative/cross_tenant,
  incluye PN-06, PN-07 y la medición de RNF-P01) pasan contra MonetDB real.
- **SC-002**: OpenAPI 3.1 generado con 0 errores de Spectral.
- **SC-003**: Latencia máxima de propagación WS < 1s bajo 100 cambios de
  estado concurrentes (RNF-P01), medido contra un servidor uvicorn real (no
  `TestClient` in-process, que produce un deadlock reproducible entre WS y
  HTTP en el mismo transporte ASGI).
- **SC-004**: build/lint/test de Angular en verde; WebSocket ejercitado
  end-to-end en un navegador real contra el backend real.
- **SC-005**: ruff, mypy, bandit y los 15 contratos de import-linter en verde.

## Assumptions

- El límite de paralelismo real sostenible en MonetDB para escritura
  concurrente sobre tablas transversales compartidas es de ~3 escritores
  simultáneos con el mecanismo de reintento actual -- documentado como
  hallazgo empírico, no resuelto estructuralmente en este sprint (queda
  abierto para revisión posterior si el volumen real lo exige).
- El WebSocket de vuelos NO necesita poblar `aerohub_repository.contexto`
  porque no toca la base de datos (solo retransmite eventos ya calculados
  por el broadcaster) -- a diferencia del WS de FIDS en S1.3, que sí lo
  necesita.
