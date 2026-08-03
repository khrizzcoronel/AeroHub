# Feature Specification: Sistema de diseño + deuda de JWT + vista canónica

**Feature Branch**: `013-diseno-sistema-jwt`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Sprint S1.11 -- Sistema de diseño + deuda de JWT + vista canónica (docs/diseno/DIRECCION_VISUAL.md, sección 3, S1.11). Primero de 4 sprints de rediseño de interfaz. Construir el sistema de diseño (tokens + primitivos compartidos), probarlo en `vuelos/estado-tiempo-real` (M1 AODB, la tira canónica), y cerrar la deuda del JWT manual en las 5 vistas que todavía lo piden."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el estado de los vuelos en una consola legible (Priority: P1)

Una persona con sesión iniciada (rol operativo con módulo M1 visible, ver
S1.10) abre la vista de estado de vuelos en tiempo real. Hoy ve HTML sin
ningún estilo: un botón, un textarea para pegar un token, y una lista
plana de eventos. Necesita, en cambio, una consola densa donde cada
cambio de estado de vuelo aparezca como una fila legible de un vistazo —
código de vuelo, ruta, puerta, hora y estado alineados en columnas,
con el estado más reciente arriba y un color de estado inequívoco.

**Why this priority**: Es la vista que prueba el sistema de diseño completo
contra datos reales en tiempo real (WebSocket), y establece el componente
("tira") que las siguientes 4 vistas reutilizarán. Sin esto, no hay
sistema de diseño verificado, solo tokens en el papel.

**Independent Test**: Abrir la vista con sesión iniciada, generar cambios
de estado de un vuelo real contra el backend en Docker, y verificar que
cada evento llega como una tira legible, con el más reciente arriba y el
color de estado correcto, sin recargar la página.

**Acceptance Scenarios**:

1. **Given** una sesión iniciada con un rol que tiene M1 visible, **When**
   la persona abre la vista de estado de vuelos, **Then** la conexión en
   tiempo real se establece sin pedir ningún dato de sesión adicional.
2. **Given** la vista conectada, **When** el estado de un vuelo cambia en
   el backend, **Then** aparece una fila nueva arriba de las anteriores,
   con el código de vuelo, ruta, puerta, hora y estado alineados en
   columnas y un color que identifica el tipo de estado.
3. **Given** la vista en un teléfono, **When** se abre la misma pantalla,
   **Then** la información sigue siendo legible sin desbordar la pantalla
   ni requerir scroll horizontal.
4. **Given** una persona que navega solo con teclado, **When** recorre los
   controles de la vista (conectar/desconectar), **Then** el control con
   foco es visualmente identificable en todo momento.

---

### User Story 2 - No tener que pegar un token para usar la aplicación (Priority: P1)

Una persona con sesión iniciada abre cualquiera de las vistas que todavía
piden un token pegado a mano (estado de vuelos, facturas, turnaround de
rampa, tablero de puertas). Ya inició sesión una vez — no debería tener
que copiar y pegar nada para que esas pantallas funcionen.

**Why this priority**: Es deuda técnica heredada de antes de que existiera
un login real (S1.10); dejarla intacta hace que el rediseño visual de las
otras vistas parezca honesto mientras sigue pidiendo un dato que la propia
aplicación ya tiene. Se marca P1 porque bloquea la credibilidad de todo
el rediseño, no porque requiera trabajo visual extenso.

**Independent Test**: Iniciar sesión una vez, y usar las 4 pantallas
afectadas sin que ninguna pida o acepte un token manualmente.

**Acceptance Scenarios**:

1. **Given** una sesión iniciada, **When** la persona abre la vista de
   estado de vuelos, facturas, turnaround o tablero de puertas, **Then**
   ninguna de las cuatro muestra un campo para pegar un token.
2. **Given** una sesión iniciada, **When** la persona usa cualquier acción
   de esas 4 vistas que llama al backend, **Then** la acción funciona sin
   que la persona haya provisto ningún dato de autenticación adicional.
3. **Given** una sesión vencida o inexistente, **When** la persona intenta
   usar alguna de esas 4 vistas, **Then** se le redirige a iniciar sesión,
   igual que ya ocurre en el resto de la aplicación desde S1.10.

---

### Edge Cases

- ¿Qué pasa si la sesión expira mientras la persona está viendo la
  consola de vuelos en tiempo real? La conexión en tiempo real se cierra
  y la persona ve un aviso claro de que debe volver a iniciar sesión, sin
  quedar con una pantalla que parece conectada pero ya no lo está.
- ¿Qué pasa si el backend no tiene ningún evento que mostrar todavía? La
  consola muestra un estado vacío explícito ("sin eventos aún"), no una
  pantalla en blanco indistinguible de un error.
- ¿Qué pasa si la persona tiene activada la preferencia de reducir
  movimiento del sistema operativo? Ninguna transición de color ni
  animación se reproduce; el cambio de estado se refleja igual, solo sin
  la transición suave.
- ¿Qué pasa en una pantalla angosta (móvil) con nombres de ruta largos o
  muchas columnas de dato? Las columnas mantienen su alineación; el
  contenido se prioriza (los datos operacionales nunca se recortan de
  forma ambigua) aunque el diseño se adapte al ancho disponible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE definir un conjunto de variables de diseño
  (color, tipografía, espaciado) reutilizable por cualquier vista de
  `apps/web`, que extienda —sin reemplazar— las ya definidas en S1.10.
- **FR-002**: El sistema DEBE incluir cuatro colores de estado
  operacional (satisfactorio, atención, crítico, neutro) como el único
  lugar de la superficie de trabajo donde aparece color saturado.
- **FR-003**: El sistema DEBE mostrar todo dato operacional (identificador
  de vuelo, hora, puerta, importe) en una tipografía monoespaciada que
  permita comparar valores verticalmente por columna.
- **FR-004**: El sistema DEBE ofrecer un conjunto de piezas de interfaz
  reutilizables (fila de dato con barra de estado, tabla densa, campo de
  formulario, botón, mensaje de aviso/error, estado vacío) que cualquier
  vista futura del rediseño pueda adoptar sin reinventarlas.
- **FR-005**: La vista de estado de vuelos en tiempo real DEBE presentar
  cada evento recibido como una fila con barra de color de estado,
  identificador de vuelo, ruta, puerta, hora y estado, con el evento más
  reciente en primer lugar.
- **FR-006**: Un cambio de color de estado que ocurre mientras la vista
  está abierta DEBE transicionar de forma perceptible pero breve (no
  instantánea, no prolongada), salvo que la persona tenga activada la
  preferencia de reducir movimiento del sistema operativo.
- **FR-007**: La vista de estado de vuelos en tiempo real DEBE ser
  utilizable tanto en pantallas de escritorio como en pantallas móviles.
- **FR-008**: Todo control interactivo de la vista rediseñada DEBE mostrar
  un indicador de foco visible al navegar con teclado.
- **FR-009**: Ninguna de las cuatro vistas afectadas (estado de vuelos,
  facturas, turnaround, tablero de puertas) DEBE solicitar ni aceptar un
  token de sesión escrito o pegado manualmente por la persona usuaria.
- **FR-010**: Las llamadas al backend que hacen esas cuatro vistas DEBEN
  autenticarse usando la sesión ya iniciada, sin que la persona provea
  ningún dato adicional, incluida la conexión en tiempo real de estado de
  vuelos (que no viaja por el mismo mecanismo que el resto de llamadas al
  backend y requiere su propia forma de portar la sesión).
- **FR-011**: Si la sesión no es válida o no existe, las cuatro vistas
  DEBEN comportarse igual que el resto de la aplicación desde S1.10:
  redirigir a iniciar sesión, no fallar en silencio ni exponer un error
  técnico.
- **FR-012**: El rediseño visual completo de este sprint se limita a la
  vista de estado de vuelos; las otras tres vistas afectadas por FR-009
  solo dejan de pedir el token manual — su apariencia visual completa se
  redefine en sprints posteriores ya planificados.

### Key Entities

- **Evento de estado de vuelo**: cambio de estado de un vuelo que llega en
  tiempo real; lo que la vista canónica representa como una fila.
- **Sesión de la persona usuaria**: ya establecida desde S1.10; esta
  entrega no crea sesión nueva, consume la existente para eliminar la
  necesidad de un token manual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona con sesión iniciada abre la vista de estado de
  vuelos y ve el primer evento en tiempo real sin ingresar ningún dato de
  autenticación adicional.
- **SC-002**: El 100% de los cambios de estado de vuelo emitidos por el
  backend durante una sesión de prueba aparecen en la vista, en el orden
  correcto (más reciente primero), sin recargar la página.
- **SC-003**: Cero de las cuatro vistas afectadas (estado de vuelos,
  facturas, turnaround, tablero de puertas) presentan un campo para
  pegar un token, verificado por inspección directa de cada pantalla.
- **SC-004**: La vista de estado de vuelos es utilizable (contenido
  legible, sin scroll horizontal, controles operables) tanto en una
  pantalla de escritorio como en una de ancho móvil típico.
- **SC-005**: Navegar la vista de estado de vuelos solo con teclado
  permite operar sus controles con el foco siempre visible.

## Assumptions

- Las personas que usan estas 4 vistas ya cuentan con una sesión iniciada
  vigente (S1.10) — este sprint no crea ni modifica el mecanismo de
  login, solo deja de exigir un dato que la sesión ya provee.
- El sistema de diseño se construye para que las vistas de S1.12/S1.13 lo
  reutilicen sin cambios estructurales; un cambio de fondo al sistema
  fuera de lo aquí definido no es alcance de este sprint.
- Las tres vistas que solo pierden el campo de token (facturas,
  turnaround, tablero de puertas) permanecen visualmente como están hoy
  en todo lo demás; su rediseño visual completo es alcance de sprints
  posteriores ya planificados (`docs/diseno/DIRECCION_VISUAL.md` sección
  3).
- M6 (Passenger Experience), M8 (Observability) y M9 (Compliance Hub) no
  tienen vista y no la reciben en este sprint — crear una vista nueva
  para ellos sería construir funcionalidad, no rediseñar una existente.
- El comportamiento de reconexión/desconexión ya existente de la vista de
  estado de vuelos (S1.2) se conserva; este sprint cambia su presentación
  y su forma de autenticarse, no su lógica de conexión.
