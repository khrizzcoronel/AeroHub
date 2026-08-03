# Feature Specification: Tableros operativos densos (puertas + rampa)

**Feature Branch**: `014-tableros-operativos-densos`

**Created**: 2026-08-03

**Status**: Draft

**Input**: User description: "Sprint S1.12 -- Tableros operativos densos. Segundo de 4 sprints de rediseño de interfaz. Rediseñar visualmente puertas/tablero-puertas (M3) y rampa/panel-turnaround (M4) con el sistema de diseño ya construido en S1.11, sin tocar backend ni contrato HTTP."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver la ocupación de las puertas de un vistazo (Priority: P1)

Una persona con el módulo Terminal & Gate Manager visible abre el tablero
de puertas. Hoy ve una lista de secciones HTML sin estilo, cada una con
un encabezado de texto plano y una tabla cruda de asignaciones. Necesita,
en cambio, identificar de un vistazo qué puertas están libres, cuáles
tienen una asignación en curso y cuáles tienen un conflicto (más de una
asignación superpuesta en el tiempo), sin tener que leer cada fila de
cada tabla.

**Why this priority**: Es la vista de mayor frecuencia de uso de las dos
de este sprint (se consulta constantemente durante la operación diaria),
y prueba el componente "tira" del sistema de diseño en un caso de uso
distinto al de S1.11 (una tira por recurso, no por evento).

**Independent Test**: Cargar el tablero real contra el backend en Docker
y verificar que cada puerta aparece como una fila con un color de estado
que corresponde a su situación real de ocupación.

**Acceptance Scenarios**:

1. **Given** el tablero cargado, **When** una puerta no tiene ninguna
   asignación, **Then** su fila se muestra con el color neutro.
2. **Given** el tablero cargado, **When** una puerta tiene una única
   asignación vigente, **Then** su fila se muestra con el color de
   estado satisfactorio.
3. **Given** el tablero cargado, **When** una puerta tiene dos o más
   asignaciones que se superponen en el tiempo, **Then** su fila se
   muestra con el color de estado crítico, señalando el conflicto.
4. **Given** el formulario de asignación manual, **When** la persona lo
   completa y confirma, **Then** el tablero se actualiza y la fila de la
   puerta afectada refleja la nueva situación.
5. **Given** la vista en un teléfono, **When** se abre la misma pantalla,
   **Then** el contenido sigue siendo legible sin desplazamiento
   horizontal.

---

### User Story 2 - Seguir un turnaround y sus tareas sin perderse (Priority: P1)

Una persona con el módulo Ground Operations visible abre el panel de
turnaround. Hoy ve una tabla cruda de turnarounds y, al seleccionar uno,
otra tabla cruda de tareas e incidencias. Necesita identificar de un
vistazo qué turnarounds se desvían de lo esperado, y al entrar en el
detalle de uno, seguir el avance de sus tareas y ver sus incidencias
asociadas con la misma claridad visual que el resto de la aplicación.

**Why this priority**: Es la vista más grande de este sprint y la que
más carga de información combina (turnarounds, tareas, incidencias);
resolverla junto con puertas cierra el par de "tableros operativos
densos" que comparten el mismo ritmo visual.

**Independent Test**: Cargar turnarounds reales, seleccionar uno con
tareas e incidencias reales, y verificar que la información se presenta
con el mismo sistema visual que el resto de la aplicación (colores de
estado, tipografía de dato, densidad).

**Acceptance Scenarios**:

1. **Given** la lista de turnarounds cargada, **When** la persona la
   observa, **Then** cada turnaround muestra un color que refleja su
   situación (a tiempo, o con desviación).
2. **Given** un turnaround seleccionado, **When** tiene tareas propias
   registradas, **Then** se listan con su estado, y el mensaje de que
   "no hay tareas visibles / son de otro agente" se conserva tal cual
   cuando corresponde (es información real de negocio, no un texto
   genérico de relleno).
3. **Given** una lista de incidencias, **When** la persona la observa,
   **Then** cada incidencia comunica su severidad mediante color, sin
   tener que leer la palabra de severidad para distinguirla.
4. **Given** la vista en un teléfono, **When** se abre la misma pantalla,
   **Then** el contenido sigue siendo legible sin desplazamiento
   horizontal.
5. **Given** una persona que navega solo con teclado, **When** recorre
   los controles de la vista (cargar, seleccionar turnaround, iniciar
   tarea, finalizar tarea), **Then** el control con foco es siempre
   identificable.

---

### Edge Cases

- ¿Qué pasa si el tablero de puertas no tiene ninguna puerta cargada
  todavía? Se muestra un estado vacío explícito, no una pantalla en
  blanco.
- ¿Qué pasa si un turnaround no tiene ninguna tarea (o ninguna es propia
  del rol con mínimo privilegio)? El mensaje que ya distingue ambos casos
  se conserva, con el mismo tratamiento visual de estado vacío que el
  resto del sistema.
- ¿Qué pasa si no hay incidencias registradas? Estado vacío explícito.
- ¿Qué pasa en una pantalla angosta con muchas columnas de dato (la
  tabla de asignaciones o de tareas)? Las columnas mantienen su
  alineación; el contenido se adapta al ancho disponible sin recortar
  datos de forma ambigua.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El tablero de puertas DEBE representar cada puerta como una
  fila con un indicador de color que refleje su situación de ocupación:
  sin asignaciones, con una asignación vigente, o con un conflicto de
  asignaciones superpuestas.
- **FR-002**: Las asignaciones de cada puerta DEBEN presentarse en una
  tabla densa consistente con el resto del sistema (misma tipografía de
  dato, mismo alto de fila).
- **FR-003**: El formulario de asignación manual de puertas DEBE usar los
  mismos componentes de campo y botón que el resto de la aplicación.
- **FR-004**: El resultado de una asignación automática y cualquier error
  DEBEN presentarse con el mismo tratamiento visual de aviso/error que el
  resto de la aplicación.
- **FR-005**: La lista de turnarounds DEBE representar cada turnaround
  como una fila con un indicador de color que refleje si está dentro de
  lo esperado o con desviación.
- **FR-006**: Las tareas de un turnaround seleccionado DEBEN presentarse
  en una tabla densa consistente con el resto del sistema, incluido el
  mensaje real de negocio que distingue "sin tareas" de "las tareas
  existen pero pertenecen a otra persona" (mínimo privilegio).
- **FR-007**: Las incidencias DEBEN presentarse en una tabla donde la
  severidad se comunique también mediante color, no solo mediante texto.
- **FR-008**: Ambas vistas DEBEN ser utilizables tanto en pantallas de
  escritorio como en pantallas móviles, sin desplazamiento horizontal.
- **FR-009**: Todo control interactivo de ambas vistas DEBE mostrar un
  indicador de foco visible al navegar con teclado.
- **FR-010**: Ninguna de las dos vistas DEBE requerir un cambio en cómo
  se autentican o en qué datos consumen del backend — el rediseño es
  exclusivamente de presentación.
- **FR-011**: Ambas vistas, junto con la vista de estado de vuelos ya
  rediseñada, DEBEN leerse como parte de un mismo sistema visual (mismos
  colores de estado, misma tipografía para dato, mismo ritmo), no como
  pantallas resueltas de forma independiente entre sí.

### Key Entities

- **Puerta**: recurso físico de la terminal; esta entrega no cambia su
  forma, solo cómo se presenta junto con sus asignaciones.
- **Asignación**: relación entre un vuelo y una puerta en una ventana de
  tiempo; su superposición con otras asignaciones de la misma puerta es
  lo que determina el color de conflicto.
- **Turnaround**: ciclo de tierra de una aeronave entre un vuelo de
  llegada y uno de salida; su color refleja si se ajusta a lo previsto.
- **Tarea**: actividad dentro de un turnaround, con su propio estado y
  visibilidad limitada por rol.
- **Incidencia**: desviación registrada sobre una tarea, con severidad.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona puede identificar todas las puertas con
  conflicto en un tablero real sin leer el detalle de ninguna tabla
  anidada, solo por el color de cada fila.
- **SC-002**: Una persona puede identificar todas las incidencias de
  severidad alta en una lista real sin leer la palabra de severidad,
  solo por el color.
- **SC-003**: Ambas vistas son utilizables (contenido legible, sin
  desplazamiento horizontal, controles operables) tanto en una pantalla
  de escritorio como en una de ancho móvil típico.
- **SC-004**: Navegar cualquiera de las dos vistas solo con teclado
  permite operar sus controles con el foco siempre visible.
- **SC-005**: Una persona que ya conoce la vista de estado de vuelos
  (S1.11) reconoce el mismo patrón visual al abrir cualquiera de estas
  dos vistas nuevas, sin necesitar explicación adicional.

## Assumptions

- El sistema de diseño (tokens, primitivos `.ah-*`) construido en S1.11
  ya existe y no se vuelve a decidir aquí — este sprint lo aplica, no lo
  rediseña.
- "Conflicto" de una puerta se determina exclusivamente con los datos que
  el frontend ya recibe hoy (asignaciones con su ventana de tiempo) — no
  requiere ninguna consulta ni cálculo nuevo del backend.
- "Desviación" de un turnaround se aproxima con el dato de estado que el
  backend ya expone hoy — una señal más fina (comparar tiempos reales vs.
  previstos con precisión de minutos) queda fuera de alcance si el
  backend no la expone todavía.
- El mensaje de mínimo privilegio de `role_ramp_agent` sobre sus propias
  tareas es contenido de negocio real y se preserva sin reescribirlo.
- No se rediseñan `tenants/tenant-creation` ni `billing/panel-facturas`
  en este sprint (son S1.13), ni se modifica `vuelos/estado-tiempo-real`
  (ya cerrada en S1.11).
