# Feature Specification: Vistas administrativas + consolidación

**Feature Branch**: `015-vistas-administrativas-consolidacion`

**Created**: 2026-08-03

**Status**: Draft

**Input**: User description: "Sprint S1.13 -- Vistas administrativas + consolidación. Tercero de 4 sprints de rediseño de interfaz. Rediseñar billing/panel-facturas y tenants/tenant-creation con el sistema de diseño ya construido en S1.11/S1.12, y auditar las 8 vistas de S1.10 (auth + shell) contra ese sistema ya formalizado."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Revisar y gestionar facturas con la misma claridad que el resto de la aplicación (Priority: P1)

Una persona con el módulo Revenue & Billing visible abre el panel de
facturas. Hoy ve una tabla cruda de facturas y, al ver el detalle de una,
otra tabla cruda de líneas de cargo. Es una vista de baja frecuencia (se
consulta ocasionalmente, no constantemente como AODB o Gate Manager), así
que necesita ser clara y correcta antes que densa — pero debe leerse
como parte del mismo sistema visual que el resto de la aplicación, no
como una pantalla aparte.

**Why this priority**: Es la última vista de alta frecuencia de negocio
que queda sin rediseñar de las tres capas operativas ya cubiertas
(vuelos, puertas/rampa, ahora billing).

**Independent Test**: Cargar facturas reales, ver el detalle de una con
sus líneas, emitir o disputar una factura según su estado, y verificar
que la presentación es coherente con el resto del sistema.

**Acceptance Scenarios**:

1. **Given** la lista de facturas cargada, **When** la persona la
   observa, **Then** cada factura comunica su estado (borrador, emitida,
   disputada) mediante color, y los montos se leen alineados por
   columna.
2. **Given** el detalle de una factura, **When** la persona lo abre,
   **Then** las líneas de cargo se presentan con el mismo componente de
   tabla densa que el resto del sistema.
3. **Given** una factura en borrador, **When** la persona la emite, o
   **Given** una factura emitida, **When** la persona la disputa,
   **Then** la acción usa los mismos controles de formulario y botón que
   el resto de la aplicación.
4. **Given** la vista en un teléfono, **When** se abre, **Then** el
   contenido es legible sin desplazamiento horizontal.

---

### User Story 2 - Crear un tenant nuevo con el mismo formulario que el resto de la aplicación (Priority: P2)

Una persona con `role_platform_admin` abre el formulario de
aprovisionamiento de tenant. Hoy ve campos de texto sin ningún estilo.
Necesita un formulario que se sienta parte de la misma aplicación que
acaba de usar para iniciar sesión, no una pantalla distinta.

**Why this priority**: Se usa con mucha menor frecuencia que facturas
(solo al incorporar un cliente nuevo), así que se resuelve después,
aunque sea una vista simple.

**Independent Test**: Completar el formulario con datos reales, crear un
tenant, y verificar que el resultado (incluida la contraseña temporal)
se presenta con claridad.

**Acceptance Scenarios**:

1. **Given** el formulario vacío, **When** la persona lo completa,
   **Then** los campos usan el mismo componente visual que cualquier
   otro formulario de la aplicación.
2. **Given** un envío exitoso, **When** se muestra el resultado
   (identificadores y contraseña temporal), **Then** se presenta con
   claridad suficiente para copiar los datos, no como una lista
   genérica.
3. **Given** un error de envío, **When** ocurre, **Then** se presenta
   con el mismo tratamiento visual de error que el resto de la
   aplicación.

---

### User Story 3 - Confirmar que las vistas de identidad siguen coherentes con el sistema ya formalizado (Priority: P3)

Una persona responsable del proyecto quiere confirmar que las 8 vistas
construidas en S1.10 (login, cambiar contraseña, recuperar, restablecer,
verificar correo, aceptar invitación, invitar usuario, y el shell) —que
se diseñaron ANTES de que el sistema de diseño se formalizara en S1.11—
siguen siendo visualmente coherentes con él, y no quedaron con detalles
sueltos que solo se notarían al compararlas una por una.

**Why this priority**: Es una auditoría, no una construcción — de menor
riesgo que las dos historias anteriores, y depende de que el sistema ya
esté maduro (viene consolidándose desde S1.11).

**Independent Test**: Revisar cada una de las 8 vistas contra los tokens
y primitivos actuales, documentando cualquier inconsistencia encontrada
(y corrigiéndola si es menor) o confirmando que no hay ninguna.

**Acceptance Scenarios**:

1. **Given** las 8 vistas de identidad, **When** se revisan contra el
   sistema de diseño actual, **Then** cada una usa los mismos tokens de
   color, tipografía y espaciado que las vistas rediseñadas en S1.11/
   S1.12.
2. **Given** una inconsistencia encontrada durante la auditoría, **When**
   es menor (no requiere rediseñar la vista completa), **Then** se
   corrige en este mismo sprint; si es mayor, se documenta como hallazgo
   para un sprint futuro en vez de expandir el alcance de este.

---

### Edge Cases

- ¿Qué pasa si una factura no tiene líneas de cargo? Estado vacío
  explícito, no una tabla en blanco.
- ¿Qué pasa si no hay facturas cargadas todavía? Estado vacío explícito.
- ¿Qué pasa si el formulario de tenant se envía con datos inválidos? El
  error se presenta con el mismo tratamiento que cualquier otro error de
  formulario del sistema.
- ¿Qué pasa si la auditoría de las 8 vistas encuentra una inconsistencia
  que implicaría cambiar el propio sistema de diseño (no solo una
  vista)? Se documenta como hallazgo para discusión, no se decide
  unilateralmente un cambio al sistema ya aprobado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La lista de facturas DEBE comunicar el estado de cada
  factura (borrador, emitida, disputada) mediante color, además del
  texto.
- **FR-002**: Los montos de facturas y líneas de cargo DEBEN alinearse
  por columna con tipografía de dato consistente con el resto del
  sistema.
- **FR-003**: El detalle de una factura y sus líneas DEBEN presentarse
  con el mismo componente de tabla densa que el resto del sistema.
- **FR-004**: Las acciones sobre una factura (emitir, disputar) DEBEN
  usar los mismos componentes de formulario y botón que el resto de la
  aplicación.
- **FR-005**: El formulario de aprovisionamiento de tenant DEBE usar los
  mismos componentes de campo y botón que el resto de la aplicación.
- **FR-006**: El resultado de crear un tenant (identificadores,
  contraseña temporal) DEBE presentarse con claridad, distinguiendo
  visualmente cada dato.
- **FR-007**: Ambas vistas nuevas DEBEN ser utilizables en escritorio y
  en móvil, sin desplazamiento horizontal.
- **FR-008**: Las 8 vistas de identidad construidas en S1.10 DEBEN
  revisarse contra el sistema de diseño actual; cualquier inconsistencia
  menor encontrada DEBE corregirse en este sprint.
- **FR-009**: Ninguna de las vistas de este sprint DEBE requerir cambios
  de backend, de contrato HTTP, ni de esquema — es un sprint exclusivo
  de presentación.

### Key Entities

- **Factura**: documento de cobro a una aerolínea; su estado determina
  qué acciones están disponibles y qué color comunica.
- **Línea de cargo**: detalle de una factura.
- **Tenant**: cliente de AeroHub que se aprovisiona con un usuario
  administrador inicial.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona puede identificar el estado de todas las
  facturas de una lista real sin leer el texto de estado, solo por
  color.
- **SC-002**: El panel de facturas y el formulario de tenant son
  utilizables (contenido legible, sin desplazamiento horizontal,
  controles operables) tanto en escritorio como en móvil.
- **SC-003**: Las 8 vistas de identidad de S1.10, revisadas al cierre de
  este sprint, no presentan ninguna inconsistencia visual conocida
  respecto al sistema de diseño vigente.
- **SC-004**: Con este sprint cerrado, las cinco áreas de negocio de
  `apps/web` (identidad, vuelos, puertas, rampa, facturación) y el
  formulario de tenant se leen como un mismo sistema visual de punta a
  punta.

## Assumptions

- El sistema de diseño (tokens, primitivos `.ah-*`, incluido `.ah-punto`
  de S1.12) ya existe y no se vuelve a decidir — este sprint lo aplica y,
  en el caso de la auditoría, lo usa como vara de medir.
- La auditoría de las 8 vistas de S1.10 es de alcance acotado: corregir
  inconsistencias menores (un color o espaciado que no siguió el token
  correcto), no rediseñar esas vistas desde cero — ya tienen identidad
  visual propia desde S1.10.
- No se toca ningún backend, endpoint, ni esquema en este sprint.
- `fids-player/pantalla-player` queda fuera (es S1.14, otra aplicación
  con otras restricciones).
