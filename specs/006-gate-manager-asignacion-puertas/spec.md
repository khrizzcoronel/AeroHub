# Feature Specification: M3 Terminal & Gate Manager -- asignación de puertas sin solapamiento

**Feature Branch**: `main`

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commit `dbe3b23`

**Input**: Sprint S1.4 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.4. Asignación
de puertas sin solapamiento, en ausencia de restricción de exclusión nativa
en MonetDB (RF-O02, OP2a).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Asignar manualmente una puerta a un vuelo sin conflictos (Priority: P1)

Como controlador de operaciones, necesito asignar una puerta a un vuelo para
una ventana horaria específica, y que el sistema rechace la asignación si esa
puerta ya está comprometida con otro vuelo en un horario que se superpone.

**Why this priority**: es la garantía central del módulo -- sin ella, dos
vuelos podrían terminar asignados a la misma puerta al mismo tiempo, un
conflicto operacional real en el mundo físico.

**Independent Test**: `POST /puertas/asignaciones` con una ventana que se
superpone con una asignación existente de la misma puerta responde 409.

**Acceptance Scenarios**:

1. **Given** una puerta con una asignación en `[09:00, 10:00)`, **When** se
   intenta asignar otro vuelo en `[09:30, 10:30)` (solape parcial), **Then**
   responde 409.
2. **Given** la misma puerta, **When** se asigna un vuelo en `[10:00, 11:00)`
   (justo adyacente, sin solapar), **Then** se acepta -- los intervalos
   semiabiertos que solo se TOCAN no son un conflicto.
3. **Given** una aeronave cuya envergadura excede la envergadura máxima de la
   puerta, **When** se intenta asignar, **Then** responde 422.

---

### User Story 2 - Detectar el conflicto incluso bajo dos peticiones simultáneas (Priority: P1)

Como responsable de integridad de datos, necesito que la garantía de no
solapamiento se sostenga incluso cuando dos peticiones de asignación sobre la
MISMA puerta llegan al mismo tiempo -- MonetDB no tiene un mecanismo nativo
de exclusión por rango (`EXCLUDE USING gist`) para apoyarse.

**Why this priority**: una garantía que solo funciona en el caso secuencial
no es una garantía real en un sistema con más de un operador trabajando a la
vez.

**Independent Test**: dos peticiones HTTP concurrentes reales de asignación
sobre la misma puerta y ventana -- exactamente una debe aceptarse (201) y la
otra rechazarse (409), nunca ambas aceptadas ni un 500.

**Acceptance Scenarios**:

1. **Given** dos peticiones simultáneas sobre la misma puerta y ventana
   horaria, **When** ambas se procesan, **Then** exactamente una obtiene 201
   y la otra 409.

---

### User Story 3 - Generar un plan de asignación automático sin conflictos (Priority: P2)

Como controlador de operaciones, necesito poder disparar una asignación
automática que reparta los vuelos sin puerta entre las puertas compatibles
(por envergadura y ventana horaria), maximizando cuántos vuelos quedan
asignados.

**Why this priority**: la asignación manual, vuelo por vuelo, no escala a la
operación real de un aeropuerto con decenas de vuelos simultáneos.

**Independent Test**: `POST /puertas/asignaciones/automatica` sobre un
conjunto sintético de vuelos y puertas produce un plan sin conflictos de
solapamiento ni de envergadura.

**Acceptance Scenarios**:

1. **Given** un conjunto de vuelos sin puerta asignada, **When** se ejecuta
   la asignación automática, **Then** el plan resultante no tiene ningún par
   de vuelos solapados en la misma puerta.
2. **Given** más vuelos que puertas compatibles en una franja horaria,
   **When** se ejecuta, **Then** el plan maximiza la cantidad de vuelos
   asignados, dejando el resto sin asignar (no falla el proceso completo).

### Edge Cases

- ¿Qué pasa con dos intervalos que terminan/empiezan EXACTAMENTE en el mismo
  instante (`fin_a == inicio_b`)? NO se considera solapamiento (semántica de
  intervalo semiabierto `[inicio, fin)`).
- ¿Qué pasa si dos transacciones concurrentes reales compiten por la misma
  fila de `ops.puerta` (no solo la misma tabla)? MonetDB aborta con
  SQLSTATE 42000 ("Update failed due to conflict with another transaction"),
  distinto del SQLSTATE 40001 ya conocido de S1.2 -- el decorador de
  reintentos se amplía para reconocer ambos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE rechazar una asignación de puerta cuyo
  intervalo `[inicio_previsto, fin_previsto)` se solape con otra asignación
  `'planificada'` o `'activa'` de la MISMA puerta.
- **FR-002**: Dos intervalos que solo se tocan (`fin_a == inicio_b`) NO
  constituyen solapamiento.
- **FR-003**: El sistema DEBE rechazar una asignación si la envergadura de la
  aeronave excede la envergadura máxima de la puerta.
- **FR-004**: La garantía de no solapamiento DEBE sostenerse bajo peticiones
  concurrentes reales sobre la misma puerta, ante la ausencia de
  `EXCLUDE USING gist` en MonetDB -- documentada como riesgo acotado, no
  como control cerrado.
- **FR-005**: El sistema DEBE permitir cancelar una asignación (baja lógica,
  nunca DELETE de motor), liberando la puerta para nuevas asignaciones.
- **FR-006**: El sistema DEBE ofrecer una asignación automática por
  programación lineal que considere envergadura, tipo de puerta
  (contacto/remota, como preferencia) y ventanas horarias, maximizando
  vuelos asignados sin generar conflictos.
- **FR-007**: `apps/web` DEBE tener un tablero de puertas que muestre las
  asignaciones vigentes y notifique visualmente un conflicto de asignación
  manual (el 409 del backend, mostrado inline).

### Key Entities

- **`AsignacionPuerta`**: `(vuelo_id, puerta_id, inicio_previsto,
  fin_previsto, estado)` -- `estado ∈ {planificada, activa, finalizada,
  cancelada}`; solo `planificada`/`activa` ocupan la puerta a efectos del
  chequeo de solapamiento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: PN-05 (asignación de dos vuelos solapados a la misma puerta)
  en verde tanto en variante secuencial como concurrente, verificada con
  peticiones HTTP reales.
- **SC-002**: 27 pruebas unitarias exhaustivas del algoritmo de intersección
  de intervalos, cubriendo bordes (`fin == inicio`), contención y solape
  parcial.
- **SC-003**: El plan de asignación automática, sobre el dataset sintético,
  no produce ningún conflicto de solapamiento ni de envergadura.
- **SC-004**: Regresión completa en verde (264/264 tests al cierre de este
  sprint), ruff/mypy/bandit/import-linter en verde.
- **SC-005**: El tablero de puertas, ejercitado en un navegador real,
  muestra el conflicto 409 de forma legible para el usuario.

## Assumptions

- El "bloqueo de fila" sobre `puerta_id` se simula con un `UPDATE` sin efecto
  sobre la propia fila de la puerta, ejecutado ANTES de leer las
  asignaciones existentes -- MonetDB no soporta `SELECT ... FOR UPDATE`
  (verificado empíricamente, error de sintaxis).
- La preferencia por puertas de tipo `contacto` sobre `remota` en la
  asignación automática es un desempate en la función objetivo, no una
  restricción dura -- ningún vuelo se rechaza por no tener puerta de
  contacto disponible si hay una remota compatible.
