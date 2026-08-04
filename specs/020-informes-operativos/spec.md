# Feature Specification: Informes operativos (RF-I)

**Feature Branch**: `020-informes-operativos`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "S1.18 -- Fase 1.5, sprint 4: Informes operativos, familia de requisitos RF-I nueva (docs/PLAN_IMPLEMENTACION_v3.0.md §8-bis.0 y §8-bis.4). Formaliza informes simples (RF-I01) y compuestos con subtotales/total calculados en el servidor (RF-I02), parametros declarados en el artefacto (RF-I03), auditoria de emision para informes con validez externa (RF-I04). 6 informes (uno simple + uno compuesto), cada uno en su modulo dueño: M1 AODB, M3 Gates, M4 Ground Ops, M5 Billing, Tenancy, M9 Compliance. Horizonte operativo (MonetDB), no tactico (eso es ClickHouse en S2.4). Filtros en el servidor, totales en el servidor, exportacion CSV desde el mismo endpoint, primitivo visual unico .ah-informe."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Emitir un informe simple con filtros de período (Priority: P1)

Una persona con acceso a un módulo (por ejemplo, un administrador de
tenant viendo AODB) necesita un listado de una entidad —vuelos, tarifas,
asignaciones de puerta, turnarounds, usuarios, eventos de auditoría—
acotado a un período y con los mismos filtros que hoy solo existen como
búsqueda en pantalla, pero calculado en el servidor y exportable.

**Why this priority**: Es el caso base de RF-I01 y el prerequisito de
todo lo demás — sin informes simples funcionando de punta a punta, los
compuestos no tienen dónde apoyarse conceptualmente.

**Independent Test**: Se puede probar por completo pidiendo un informe
simple de cualquiera de los 6 módulos con un rango de fechas, y
verificando que el conjunto de filas devuelto coincide exactamente con
lo que existe en la base de datos para ese período — sin depender de
ningún otro informe.

**Acceptance Scenarios**:

1. **Given** un módulo con datos en un período conocido, **When** la
   persona pide su informe simple con ese período como filtro, **Then**
   el sistema devuelve exactamente las filas de ese período, ni una más
   ni una menos.
2. **Given** un informe simple ya mostrado en pantalla, **When** la
   persona pide exportarlo, **Then** el archivo exportado contiene las
   mismas filas y valores mostrados en pantalla, sin recalcular nada.
3. **Given** un período sin ningún dato, **When** la persona pide el
   informe, **Then** el sistema muestra un resultado vacío explícito, no
   un error.

---

### User Story 2 - Emitir un informe compuesto con subtotales reconciliables (Priority: P1)

Una persona necesita ver un dato agrupado por una dimensión relevante
para su módulo (aerolínea, puerta, tipo de tarea, concepto de cargo,
plan de tenant) con un subtotal por grupo y un total general, para
tomar una decisión operativa (por ejemplo, qué aerolínea tiene la peor
puntualidad del período, o qué puerta está más ocupada).

**Why this priority**: Es el caso que motiva RF-I02, la promesa central
de "informes" frente a "otro panel más" — sin subtotales calculados por
el servidor, cualquier consumidor externo (o dos personas con distinto
filtro) puede llegar a números distintos del mismo dato.

**Independent Test**: Se puede probar pidiendo el informe compuesto de
un módulo con datos conocidos y verificando manualmente que la suma de
los subtotales mostrados coincide exactamente con el total general
mostrado, sin que el navegador haya hecho ningún cálculo.

**Acceptance Scenarios**:

1. **Given** datos reales de un período con al menos 2 grupos distintos
   de la dimensión de agrupación, **When** la persona pide el informe
   compuesto, **Then** cada grupo muestra su subtotal, y la suma de
   todos los subtotales es exactamente igual al total general mostrado.
2. **Given** un informe compuesto de facturación, **When** se compara
   contra las facturas ya emitidas del mismo período (vista de
   facturas, S1.6/S1.13), **Then** los montos coinciden sin diferencias
   (RF-E02, parte operativa).
3. **Given** el mismo informe compuesto pedido dos veces con el mismo
   filtro, **When** se comparan ambas respuestas, **Then** son
   idénticas — el cálculo no depende de qué vio el navegador antes.

---

### User Story 3 - Saber exactamente qué se pidió y cuándo (Priority: P2)

Una persona que recibe un informe exportado (propio o de un colega)
necesita poder reconstruir, mirando solo el archivo, qué parámetros se
usaron para generarlo y en qué momento — sin tener que preguntar ni
volver a la aplicación.

**Why this priority**: Es RF-I03 — un informe sin sus parámetros
visibles es una tabla suelta, no un artefacto verificable; importante
pero no bloquea la demostración del cálculo correcto (US1/US2).

**Independent Test**: Se puede probar exportando cualquier informe y
verificando, sin abrir la aplicación, que el archivo declara el período
filtrado, cualquier otro filtro aplicado, y la fecha/hora exacta de
generación.

**Acceptance Scenarios**:

1. **Given** un informe (simple o compuesto) con filtros aplicados,
   **When** se exporta, **Then** el archivo exportado incluye una
   sección o encabezado con los parámetros usados y la fecha de
   generación, antes de las filas de datos.

---

### User Story 4 - Auditar la emisión de informes con validez externa (Priority: P3)

Un responsable de cumplimiento necesita saber, más adelante, quién
emitió un informe de facturación o el informe regulatorio de M9 y
cuándo, porque esos documentos pueden presentarse fuera de la
organización.

**Why this priority**: Es RF-I04 — importante para trazabilidad, pero
solo aplica a 2 de los 6 informes (facturación, M9) y no bloquea que el
resto del sprint funcione; es la última pieza en cerrarse.

**Independent Test**: Se puede probar emitiendo el informe de
facturación o el de M9, y verificando que aparece una entrada nueva en
el registro de auditoría con quién lo pidió y cuándo.

**Acceptance Scenarios**:

1. **Given** un informe de facturación o del módulo M9, **When** se
   emite (con o sin exportar), **Then** queda una entrada en el
   registro de auditoría del sistema con el usuario y la fecha/hora.
2. **Given** un informe de cualquiera de los otros 4 módulos, **When**
   se emite, **Then** NO se exige entrada de auditoría (solo aplica a
   los 2 informes con validez externa, spec.md Assumptions).

---

### Edge Cases

- ¿Qué pasa si alguien pide un informe compuesto sin ningún grupo
  resultante (todos los filtros excluyen todo)? El total general debe
  mostrarse como `0`, explícito, no como ausencia de respuesta.
- ¿Qué pasa si el rango de fechas pedido es inválido (fin antes que
  inicio)? El sistema rechaza el pedido con un mensaje claro antes de
  consultar cualquier dato.
- ¿Qué pasa con el aislamiento por tenant? Cada informe es una consulta
  más sobre tablas ya protegidas por el guardián de tenant — ningún
  informe puede mostrar datos de un tenant distinto al de quien lo pide,
  sin excepción.
- ¿Qué pasa si dos personas de distinto rol piden el mismo informe? Cada
  una ve solo lo que su tenant/scope ya le permitiría ver por cualquier
  otro medio — un informe no es una puerta de acceso nueva.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ofrecer, para cada uno de los 6 módulos en
  alcance (AODB, Gates, Ground Ops, Billing, Tenancy, Compliance), un
  informe simple de su entidad principal, filtrable por período (y por
  la dimensión adicional que ese módulo ya expone en sus vistas, p. ej.
  aerolínea o estado).
- **FR-002**: El sistema DEBE ofrecer, para cada uno de los 6 módulos,
  un informe compuesto que agrupe su entidad principal por una dimensión
  relevante, con un subtotal por grupo.
- **FR-003**: Todo informe compuesto DEBE incluir un total general
  calculado por el sistema, igual a la suma exacta de todos los
  subtotales mostrados.
- **FR-004**: El sistema DEBE aplicar todos los filtros de un informe en
  el servidor — el resultado ya viene acotado, nunca se filtra una lista
  completa después de recibirla.
- **FR-005**: El sistema DEBE permitir exportar cualquier informe (simple
  o compuesto) a un archivo, desde el mismo lugar donde se genera —
  nunca desde un camino separado que pueda mostrar datos distintos.
- **FR-006**: Todo informe exportado DEBE declarar, dentro del propio
  archivo, los parámetros usados para generarlo y la fecha/hora de
  generación.
- **FR-007**: El sistema DEBE registrar en el log de auditoría la
  emisión del informe de facturación (M5) y del informe regulatorio de
  M9 — los dos únicos con validez externa en este sprint.
- **FR-008**: El sistema DEBE aplicar el mismo aislamiento por tenant que
  el resto de la aplicación a cada informe, sin excepción.
- **FR-009**: El informe compuesto de facturación DEBE conciliar
  exactamente con las facturas ya emitidas del mismo período, sin
  diferencias.

### Key Entities *(include if feature involves data)*

- **Informe**: un resultado calculado bajo demanda (no persistido) sobre
  datos existentes de un módulo, con parámetros de filtro, fecha de
  generación, y — si es compuesto — grupos con subtotal y un total
  general. No es una entidad de base de datos nueva; es una forma de
  consultar entidades ya existentes de cada módulo (vuelo, asignación de
  puerta, turnaround, factura/cargo, tenant/usuario, evento de
  auditoría/reporte DGAC).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los 6 módulos en alcance tienen su informe simple y su
  informe compuesto accesibles desde la aplicación, sin necesidad de
  consultar la base de datos directamente.
- **SC-002**: En el 100% de los informes compuestos verificados contra
  datos reales, la suma de subtotales iguala exactamente el total
  general mostrado.
- **SC-003**: El informe de facturación concilia con las facturas
  emitidas del mismo período sin ninguna diferencia, verificado contra
  datos reales.
- **SC-004**: Una persona puede generar y exportar cualquiera de los 6
  informes simples en menos de 30 segundos desde que abre el módulo
  correspondiente.
- **SC-005**: El 100% de los informes exportados incluye sus parámetros
  y fecha de generación dentro del propio archivo, verificable sin
  volver a la aplicación.

## Assumptions

- Horizonte operativo únicamente (período en curso / histórico reciente
  del propio módulo) — comparativas multi-período o tendencias quedan
  fuera de alcance, corresponden a la capa analítica de S2.4 (ADR-016).
- Los 6 informes compuestos usan CADA UNO su propia dimensión de
  agrupación natural (aerolínea, puerta×franja, tipo de tarea, concepto
  de cargo, plan de tenant, ninguna agrupación adicional para
  auditoría/DGAC más allá de lo que el reporte regulatorio ya define) —
  no hay un mecanismo de agrupación configurable por el usuario en este
  sprint.
- "Validez externa" (RF-I04) se interpreta, para este sprint, como
  exactamente 2 informes: el de facturación (M5) y el regulatorio de M9
  — los otros 4 no generan entrada de auditoría por emitirse.
- La exportación es CSV (formato explícito ya mencionado en el plan,
  `?formato=csv`) — no se agregan otros formatos (PDF, Excel) en este
  sprint.
- El primitivo visual `.ah-informe` se construye una sola vez y se
  reutiliza en los 6 módulos — no hay 6 diseños visuales distintos.
- No se modifica ningún dato existente — los informes son de solo
  lectura sobre tablas ya existentes de cada módulo.
