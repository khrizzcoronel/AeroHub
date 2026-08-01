# Feature Specification: Capa de repositorio -- guardián de tenant, roles y DDL fundacional

**Feature Branch**: `main`

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commit `0cdc813`

**Input**: Sprint S0.2 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §7.2. Dejar la capa
de repositorio operativa antes de la primera tabla de negocio de Fase 1, con el
guardián de tenant fail-closed (ADR-019) y el journal de continuidad (ADR-018)
verificados contra MonetDB real.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ninguna consulta sin filtro de tenant llega al motor (Priority: P1)

Como responsable de seguridad del sistema, necesito que sea estructuralmente
imposible que una consulta contra una tabla de alcance `'tenant'` llegue a
MonetDB sin un filtro explícito de `tenant_id` -- no como buena práctica de
código, sino como control que aborta la sentencia antes de ejecutarse.

**Why this priority**: es el control central de todo el sistema multi-tenant;
sin él, cualquier bug futuro en cualquier módulo es una fuga de datos entre
tenants.

**Independent Test**: 21 casos de prueba contra el guardián (`packages/repository/aerohub_repository/guard.py`),
incluyendo un JOIN adversarial de dos tablas de alcance `'tenant'` donde solo
una lleva el filtro.

**Acceptance Scenarios**:

1. **Given** una sentencia `SELECT` sobre una tabla de alcance `'tenant'` sin
   predicado de `tenant_id`, **When** se ejecuta, **Then** el guardián la
   aborta con `TenantScopeViolation` antes de llegar al motor.
2. **Given** un `JOIN` entre dos tablas de alcance `'tenant'` donde solo una
   lleva el filtro, **When** se ejecuta, **Then** el guardián también la
   aborta (no basta con que UNA tabla del join esté filtrada).
3. **Given** una tabla usada sin haber declarado su alcance vía
   `registrar_alcance()`, **When** se consulta, **Then** lanza
   `AlcanceNoDeclarado` (fail-closed ante lo desconocido, no fail-open).
4. **Given** SQL de texto crudo (`TextClause`), **When** se ejecuta sobre una
   tabla de alcance tenant, **Then** el guardián lo rechaza siempre (no puede
   verificar el alcance de texto opaco).

---

### User Story 2 - Detectar una fuga que el guardián estructural no puede ver (Priority: P1)

Como responsable de seguridad, necesito una segunda línea de defensa
(suite cruzada por introspección) que detecte una fuga real de datos entre
tenants incluso cuando el guardián estructural (G2) no puede verla -- por
ejemplo, un filtro con `OR` en vez de `AND` que sigue "teniendo" un predicado
de `tenant_id` pero no restringe nada.

**Why this priority**: el guardián G2 verifica la FORMA de la sentencia
(¿hay un predicado de igualdad sobre `tenant_id`?), no su SEMÁNTICA completa
-- un `OR` mal puesto pasa la verificación estructural pero sigue siendo una
fuga real.

**Independent Test**: `tests/cross_tenant/` (suite G4) probada contra una fuga
real inyectada deliberadamente (`OR` en vez de `AND`), confirmando que la
detecta donde G2 no puede.

**Acceptance Scenarios**:

1. **Given** una consulta con `WHERE tenant_id = :t OR 1=1` (fuga real, pasa
   la verificación estructural de G2), **When** corre la suite cruzada G4,
   **Then** detecta que el tenant B ve datos del tenant A.

---

### User Story 3 - Cada mutación de negocio queda en el journal y auditada (Priority: P2)

Como responsable de cumplimiento, necesito que toda mutación de negocio
escriba en `continuidad.journal_mutacion` (ADR-018 C1) y en
`compliance.log_auditoria` (P8) en la MISMA transacción, para que un rollback
nunca deje un registro huérfano en uno de los dos.

**Why this priority**: sin esto, RTO/RPO (ADR-018) y la trazabilidad de
cumplimiento (P8) no son reales, son aspiracionales.

**Independent Test**: escritura transaccional probada con rollback real
contra MonetDB -- confirmar que ni el journal ni la auditoría persisten si la
transacción completa revierte.

**Acceptance Scenarios**:

1. **Given** una mutación que escribe `journal_mutacion` +
   `log_auditoria` + la tabla de negocio en la misma transacción,
   **When** la transacción falla y revierte, **Then** ninguna de las tres
   escrituras persiste.

### Edge Cases

- ¿Qué pasa con `GENERATED ALWAYS AS IDENTITY` bajo `SET ROLE`? No funciona en
  esta versión de MonetDB (ninguna secuencia es accesible bajo un rol asumido,
  ni para el rol más privilegiado) -- resuelto generando el id en la
  aplicación (`packages/kernel/identificador.py`, estilo Snowflake), no en el
  motor.
- ¿Qué pasa si `log_auditoria.usuario_id` lleva una FK hacia
  `tenants.usuario`? Rompe el INSERT para todos los roles, incluido el más
  privilegiado -- se retiró la FK, la integridad de ese campo se delega al
  JWT ya validado, no al motor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE registrar el alcance (`'tenant'`, `'global'`,
  `'interno'`) de cada tabla antes de que pueda usarse en una consulta (G1).
- **FR-002**: El sistema DEBE verificar, en el evento `before_execute` del
  motor, que toda sentencia sobre una tabla de alcance `'tenant'` lleve un
  predicado de igualdad vinculado al `tenant_id` del contexto de la petición
  (G2) -- recorriendo el árbol de la sentencia SQLAlchemy Core, nunca el
  texto SQL compilado.
- **FR-003**: El sistema DEBE proveer `alcance_global()` como única excepción
  nominal al filtro obligatorio, exigiendo `motivo` y `rol` explícitos, y
  auditando su uso.
- **FR-004**: Toda sesión de base de datos DEBE activar el rol RBAC real vía
  `SET ROLE` (P2) -- la membresía de rol no se activa sola en MonetDB.
- **FR-005**: El DDL fundacional DEBE aplicar: 10 catálogos globales, esquema
  `tenants` completo (10 tablas), `compliance.log_auditoria` (adelantada
  desde S1.7 porque P8 la exige desde el primer commit de negocio),
  `continuidad.journal_mutacion` (ADR-018 C1), los 16 roles de la matriz 4.3.1
  con sus GRANT reales, y el usuario técnico `aerohub_app`.
- **FR-006**: Toda mutación de negocio DEBE escribir su registro de journal y
  de auditoría en la MISMA transacción que la mutación en sí.
- **FR-007**: Los IDs de entidades DEBEN generarse en la aplicación (estilo
  Snowflake), no por el motor -- MonetDB no soporta `GENERATED ALWAYS AS
  IDENTITY` bajo `SET ROLE`.

### Key Entities

- **`RegistroAlcance`**: `(esquema, tabla, alcance, columna_tenant)` -- el
  registro G1 que declara cómo debe filtrarse cada tabla.
- **`continuidad.journal_mutacion`**: bitácora transaccional de toda mutación
  de negocio (ADR-018 C1), insumo del mecanismo de continuidad completo de
  S1.9.
- **`compliance.log_auditoria`**: registro append-only de toda operación
  auditable, sin FK hacia `tenants.usuario` (integridad delegada al JWT).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 21/21 casos del guardián G1/G2 pasan, incluido el JOIN
  adversarial.
- **SC-002**: La suite cruzada G4 detecta el 100% de una fuga inyectada
  deliberadamente que el guardián estructural no puede ver por sí solo.
- **SC-003**: 58/58 casos de la batería de pruebas negativas (PN-03, PN-04,
  PN-08, PN-15) pasan contra MonetDB real.
- **SC-004**: 134/134 tests totales del repositorio pasan contra MonetDB real
  (no mocks).
- **SC-005**: ruff, mypy, bandit, import-linter, nomenclatura DDL y
  `docker-compose config` quedan limpios.

## Assumptions

- MonetDB es el único motor operacional (ADR-013); el diseño del guardián
  asume sus particularidades reales (sin `SELECT ... FOR UPDATE`, sin
  secuencias bajo `SET ROLE`), no las de un motor genérico.
- El mecanismo de continuidad completo (failover real, snapshot, standby
  caliente) queda fuera de alcance de este sprint -- aquí solo se sienta la
  base transaccional (`journal_mutacion`) que S1.9 va a usar.
