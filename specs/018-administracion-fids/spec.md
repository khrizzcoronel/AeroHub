# Feature Specification: Administración de FIDS

**Feature Branch**: `018-administracion-fids`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "S1.16 -- Fase 1.5, sprint 2. M2 FIDS tiene endpoints de administración (publicar plantilla, registrar pantalla, asignar plantilla) sin ningún consumidor en apps/web -- el reproductor pide un código de pantalla que ninguna interfaz puede crear. Construir una vista administrativa nueva (M2 nunca tuvo ruta en apps/web) con: gestión de plantillas, registro y telemetría de pantallas, y asignación de plantilla a pantalla. Requiere agregar los endpoints de listado que hoy no existen (solo hay altas, no consultas de lista) y un catálogo de terminales."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar una pantalla física y ponerla en producción (Priority: P1)

Una persona responsable de FIDS necesita dar de alta una pantalla física
recién instalada en una terminal, asignarle la plantilla que debe mostrar,
y obtener el código que la persona técnica ingresará en el reproductor
físico. Hoy esto es imposible desde la aplicación: el reproductor
(`apps/fids-player`) pide exactamente ese código, y no existe ninguna
pantalla donde generarlo.

**Why this priority**: Es el caso de uso que bloquea todo lo demás -- sin
una pantalla registrada, el reproductor no tiene nada que consumir, sin
importar cuántas plantillas existan.

**Independent Test**: Registrar una pantalla nueva desde la aplicación,
con una plantilla ya existente asignada, y confirmar que el código
generado conecta con éxito en `apps/fids-player`.

**Acceptance Scenarios**:

1. **Given** al menos una plantilla ya publicada, **When** la persona
   registra una pantalla nueva seleccionando terminal y plantilla de
   listas (nunca escribiendo un id), **Then** la pantalla queda
   registrada con un código visible y copiable.
2. **Given** una pantalla registrada, **When** la persona la busca en el
   listado, **Then** ve su terminal, su plantilla vigente, y su estado de
   telemetría (en línea, sin señal, o en mantenimiento).
3. **Given** el código de una pantalla recién registrada, **When** se
   ingresa en `apps/fids-player`, **Then** el reproductor conecta y
   muestra la plantilla asignada.

---

### User Story 2 - Publicar y reutilizar plantillas de contenido (Priority: P1)

Una persona responsable de FIDS necesita crear el contenido que las
pantallas van a mostrar (información de vuelos, avisos) sin depender de
que alguien lo inserte directamente en la base de datos. Necesita poder
ver qué plantillas ya existen para no duplicar trabajo, y crear una
nueva cuando haga falta.

**Why this priority**: Es un prerrequisito de la Historia 1 -- no se
puede registrar una pantalla con una plantilla que nadie puede ver ni
crear desde la aplicación.

**Independent Test**: Publicar una plantilla nueva desde la aplicación,
confirmar que aparece en el listado, y que es seleccionable al registrar
o reasignar una pantalla.

**Acceptance Scenarios**:

1. **Given** la vista de plantillas, **When** la persona publica una
   plantilla nueva con nombre y contenido, **Then** la plantilla queda
   disponible en el listado y en los selects de asignación.
2. **Given** un contenido de plantilla con formato inválido, **When** se
   intenta publicar, **Then** el error se presenta con el mismo
   tratamiento visual que cualquier otro formulario del sistema, sin
   completar la publicación.

---

### User Story 3 - Reasignar la plantilla de una pantalla ya en producción (Priority: P2)

Una persona responsable de FIDS necesita cambiar qué está mostrando una
pantalla que ya está funcionando (por ejemplo, mover de una plantilla de
llegadas a una de salidas), sin reinstalar ni reconfigurar el
dispositivo físico.

**Why this priority**: Depende de que existan pantallas y plantillas
(Historias 1 y 2); es la operación de mantenimiento recurrente una vez
que el sistema está poblado.

**Independent Test**: Cambiar la plantilla asignada a una pantalla ya
registrada y confirmar que el reproductor conectado a esa pantalla
actualiza su contenido sin intervención manual en el dispositivo.

**Acceptance Scenarios**:

1. **Given** una pantalla con una plantilla vigente, **When** la persona
   le asigna una plantilla distinta desde el listado, **Then** la
   pantalla queda con la nueva plantilla vigente de inmediato.
2. **Given** un reproductor ya conectado a esa pantalla, **When** la
   reasignación ocurre, **Then** el reproductor refleja el contenido
   nuevo sin que nadie lo reconecte manualmente.

---

### Edge Cases

- ¿Qué pasa si se intenta registrar una pantalla con un código ya
  existente? El error se presenta con el mismo tratamiento que cualquier
  otro conflicto de datos del sistema.
- ¿Qué pasa si no hay ninguna plantilla publicada todavía? El registro
  de pantalla lo indica con claridad (estado vacío explícito) en vez de
  ofrecer un select vacío sin explicación.
- ¿Qué pasa si no hay ninguna terminal disponible para seleccionar? Se
  documenta como riesgo conocido en Assumptions -- el catálogo de
  terminales depende de datos que hoy no se siembran formalmente.
- ¿Qué pasa con una pantalla cuya última señal fue hace mucho tiempo?
  Su telemetría debe distinguirse visualmente ("sin señal") de una
  pantalla que nunca reportó señal.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir consultar el listado completo de
  plantillas publicadas para el tenant de quien consulta.
- **FR-002**: El sistema DEBE permitir publicar una plantilla nueva desde
  la aplicación, con nombre y contenido.
- **FR-003**: El sistema DEBE permitir consultar el listado completo de
  pantallas registradas para el tenant de quien consulta, incluyendo su
  estado de telemetría y el momento de su última señal.
- **FR-004**: El sistema DEBE permitir registrar una pantalla física
  nueva desde la aplicación, seleccionando su terminal y su plantilla
  inicial de listas existentes, nunca escribiendo un identificador
  técnico a mano.
- **FR-005**: El sistema DEBE permitir reasignar la plantilla vigente de
  una pantalla ya registrada.
- **FR-006**: El código de una pantalla recién registrada DEBE quedar
  visible y fácil de copiar, porque es el dato que se transcribe al
  dispositivo físico.
- **FR-007**: El sistema DEBE distinguir visualmente los tres estados de
  telemetría de una pantalla (en línea, sin señal, en mantenimiento).
- **FR-008**: La vista administrativa de FIDS DEBE ser alcanzable desde
  la navegación principal de la aplicación para quien tenga el permiso
  correspondiente -- hoy el módulo no aparece en ningún menú.
- **FR-009**: Ninguna acción de esta vista DEBE requerir tocar la base
  de datos ni la API por fuera de la aplicación.

### Key Entities

- **Plantilla FIDS**: contenido publicable con nombre, versión y
  definición de lo que una pantalla muestra.
- **Pantalla FIDS**: dispositivo físico identificado por código, asociado
  a una terminal y a una plantilla vigente, con un estado de telemetría
  derivado de su última señal reportada.
- **Terminal**: ubicación física del aeropuerto a la que pertenece una
  pantalla.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona completa el ciclo de publicar una plantilla,
  registrar una pantalla con esa plantilla, y conectar el reproductor
  físico con el código resultante, en menos de 3 minutos.
- **SC-002**: El 100% de las pantallas registradas es visible en el
  listado con su estado de telemetría correcto, verificado contra datos
  reales.
- **SC-003**: Reasignar la plantilla de una pantalla ya conectada se
  refleja en el reproductor sin ninguna acción manual sobre el
  dispositivo.
- **SC-004**: Con este sprint cerrado, M2 FIDS deja de ser el único
  módulo con vista en `apps/fids-player` pero ninguna superficie
  administrativa en `apps/web`.

## Assumptions

- El backend ya expone (o expondrá como parte de este mismo sprint, sin
  requerir diseño de negocio nuevo) los endpoints de listado de
  plantillas y pantallas -- no existían al momento de escribir esta
  especificación, pero agregarlos es una consulta de solo lectura sobre
  datos que el sistema ya modela, no una capacidad de negocio nueva.
- El catálogo de terminales puede estar vacío o incompleto en el entorno
  de desarrollo actual (nunca se sembró formalmente) -- este sprint
  expone el catálogo tal cual existe, no se responsabiliza por poblar
  datos de terminales que pertenecen a otro sprint/módulo.
- No se modifica `apps/fids-player` (cerrado en S1.14) ni el mecanismo de
  telemetría de "sin señal" ya construido ahí -- esta vista solo consume
  el estado ya calculado por el backend.
- No se construyen en este sprint: tarifarios, conciliación de pax, ni
  informes -- son S1.17/S1.18.
