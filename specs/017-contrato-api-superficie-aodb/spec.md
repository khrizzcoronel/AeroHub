# Feature Specification: Contrato de API y superficie del AODB

**Feature Branch**: `017-contrato-api-superficie-aodb`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "S1.15 -- Fase 1.5, sprint 1. Regenerar el contrato de API desde el backend real (hoy documenta 60 rutas contra ~72 reales, y CI valida ese documento desactualizado sin detectarlo); construir en apps/web la superficie de alta/edición de vuelos y registro de cambio de estado que M1 AODB no tiene hoy (la vista actual solo muestra cambios de estado por WebSocket, no permite producirlos); cerrar dos endpoints huérfanos de bajo costo en vistas que ya existen (cancelar asignación de puerta, reenviar verificación de correo)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar y actualizar el estado de un vuelo desde la aplicación (Priority: P1)

Una persona con el rol de controlador de operaciones necesita dar de alta
un vuelo nuevo del día y, conforme avanza (embarcando, en vuelo,
aterrizado, cancelado, desviado), registrar cada cambio de estado. Hoy
la aplicación solo le muestra esos cambios en tiempo real después de
que ocurren -- no tiene forma de producirlos. Su única alternativa es
pedirle a alguien con acceso a la API que lo haga por ella, lo cual
convierte al módulo núcleo del sistema en un panel de solo lectura para
su propio operador.

**Why this priority**: Es el caso de uso más grave detectado en la
auditoría de superficie -- el rol tiene los permisos, el backend tiene
el endpoint, y no existe ningún camino para ejercerlos desde la
aplicación.

**Independent Test**: Dar de alta un vuelo real desde la aplicación,
consultarlo, registrar dos cambios de estado consecutivos, y confirmar
que la vista de tiempo real (WebSocket) refleja cada cambio sin
recargar la página.

**Acceptance Scenarios**:

1. **Given** la vista de vuelos, **When** la persona completa el
   formulario de alta con los datos mínimos de un vuelo, **Then** el
   vuelo queda registrado y es consultable de inmediato.
2. **Given** un vuelo ya registrado, **When** la persona registra un
   cambio de estado válido (por ejemplo, de "programado" a
   "embarcando"), **Then** el cambio se refleja tanto en la consulta
   puntual del vuelo como en la vista de tiempo real que ya consume el
   WebSocket.
3. **Given** un vuelo ya registrado, **When** la persona intenta
   consultarlo, **Then** puede ver sus datos completos y su historial
   de estados sin depender de que un evento en vivo se lo muestre.
4. **Given** un intento de registrar un cambio de estado inválido (por
   ejemplo, de un estado terminal a otro), **When** ocurre, **Then** la
   aplicación presenta el rechazo con el mismo tratamiento visual que
   cualquier otro error de formulario del sistema.

---

### User Story 2 - Confiar en que el contrato de API publicado describe la API real (Priority: P2)

Una persona responsable de integrar un sistema externo, o de auditar la
plataforma, consulta el contrato de API publicado para saber qué rutas
existen y qué forma tienen. Hoy ese documento le miente por omisión:
describe 60 rutas cuando el backend expone alrededor de 72, y la
verificación automática que debería detectar esa discrepancia pasa en
verde porque solo confirma que el documento es válido, no que coincide
con la API real.

**Why this priority**: Es la causa raíz que permite que la Historia 1 (y
cualquier brecha futura) pase desapercibida -- sin un contrato confiable
no hay forma automática de saber qué le falta a la interfaz.

**Independent Test**: Agregar una ruta nueva al backend sin actualizar el
documento de contrato manualmente, y confirmar que la verificación
automática lo rechaza en vez de pasar en verde.

**Acceptance Scenarios**:

1. **Given** el backend con todas sus rutas reales, **When** se genera
   el contrato de API, **Then** el documento resultante incluye el 100%
   de las rutas expuestas, sin mantenimiento manual.
2. **Given** el contrato de API comiteado en el repositorio, **When**
   difiere del que se generaría desde el backend actual, **Then** la
   verificación automática de integración continua falla explícitamente,
   señalando la discrepancia.
3. **Given** el contrato ya regenerado y sincronizado, **When** se
   ejecuta la verificación de formato existente, **Then** sigue pasando
   sin errores (no se pierde la validación de forma ya existente al
   agregar la de contenido).

---

### User Story 3 - Completar dos acciones que ya tienen pantalla pero les falta el botón (Priority: P3)

Una persona operando el tablero de puertas necesita poder deshacer una
asignación que ya no corresponde (por ejemplo, un cambio de última hora),
y hoy no tiene ningún control para hacerlo aunque la posibilidad ya
existe en el sistema. De forma similar, alguien que no recibió a tiempo
el correo de verificación de su cuenta no tiene manera de pedir que se
lo reenvíen sin contactar a soporte.

**Why this priority**: Es la brecha más barata de cerrar del proyecto --
ambas vistas ya existen, solo falta el control que invoca una acción que
el backend ya sabe hacer.

**Independent Test**: Cancelar una asignación de puerta real desde el
tablero y confirmar que la puerta queda libre; solicitar el reenvío del
correo de verificación desde la vista correspondiente y confirmar que
llega un correo nuevo.

**Acceptance Scenarios**:

1. **Given** una puerta con una asignación activa, **When** la persona
   la cancela desde el tablero, **Then** la asignación se marca como
   cancelada y la puerta vuelve a mostrarse libre.
2. **Given** una cuenta con correo sin verificar, **When** la persona
   solicita el reenvío desde la vista de verificación, **Then** recibe
   un correo nuevo con un enlace válido.

---

### Edge Cases

- ¿Qué pasa si dos personas intentan registrar cambios de estado
  contradictorios sobre el mismo vuelo casi al mismo tiempo? El sistema
  ya resuelve conflictos de escritura concurrente a nivel de motor
  (comportamiento existente, no de este sprint) -- la interfaz debe
  mostrar el rechazo con claridad si ocurre, no un error genérico.
- ¿Qué pasa si se intenta dar de alta un vuelo con datos incompletos o
  inválidos? El error se presenta con el mismo tratamiento que cualquier
  otro formulario del sistema, sin permitir el envío.
- ¿Qué pasa si el contrato de API generado automáticamente pierde
  documentación descriptiva que alguien había agregado a mano? Se
  documenta como riesgo aceptado en Assumptions -- el contrato pasa a
  generarse desde las anotaciones del propio código, no desde un archivo
  editado aparte.
- ¿Qué pasa si se cancela una asignación de puerta que ya estaba
  vinculada a un turnaround en curso? Queda fuera de alcance de este
  sprint verificar esa interacción entre módulos -- se hereda el
  comportamiento que el endpoint ya tiene.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir dar de alta un vuelo nuevo desde
  la aplicación, con los datos mínimos necesarios para identificarlo y
  operarlo.
- **FR-002**: El sistema DEBE permitir consultar los datos completos de
  un vuelo puntual desde la aplicación, sin depender de un evento en
  vivo para mostrarlos.
- **FR-003**: El sistema DEBE permitir registrar un cambio de estado
  sobre un vuelo existente desde la aplicación.
- **FR-004**: Un cambio de estado registrado desde la aplicación DEBE
  reflejarse en la vista de tiempo real existente sin recargar la
  página.
- **FR-005**: Un intento de registrar un dato inválido (alta o cambio de
  estado) DEBE presentarse con el mismo tratamiento visual de error que
  el resto de la aplicación, sin completar la acción.
- **FR-006**: El contrato de API publicado DEBE generarse a partir de la
  definición real del backend, sin mantenimiento manual paralelo.
- **FR-007**: La integración continua DEBE fallar si el contrato de API
  comiteado en el repositorio no coincide con el que se generaría desde
  el backend actual en ese momento.
- **FR-008**: El sistema DEBE permitir cancelar una asignación de puerta
  activa desde la vista donde las asignaciones ya se gestionan.
- **FR-009**: El sistema DEBE permitir solicitar el reenvío del correo
  de verificación de cuenta desde la vista de verificación existente.
- **FR-010**: Ninguna de las vistas de este sprint DEBE requerir que la
  persona conozca o invoque manualmente un identificador técnico que la
  aplicación ya tiene disponible (por ejemplo, pegar un id a mano cuando
  ya se seleccionó el registro en pantalla).

### Key Entities

- **Vuelo**: registro operativo con número, aeropuertos de origen/destino,
  horarios previstos, y un historial de cambios de estado.
- **Cambio de estado de vuelo**: evento con el estado nuevo y el momento
  en que se registró, asociado a un vuelo.
- **Contrato de API**: documento que describe las rutas, métodos y formas
  de datos que el backend expone; debe ser un reflejo fiel y automático
  del backend, no un artefacto mantenido por separado.
- **Asignación de puerta**: vínculo entre un vuelo y una puerta con un
  intervalo de tiempo, que puede cancelarse.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona con el rol correspondiente completa el ciclo
  de alta de un vuelo y registro de su primer cambio de estado, desde la
  aplicación, en menos de 2 minutos.
- **SC-002**: El 100% de las rutas reales del backend aparece en el
  contrato de API publicado, verificado automáticamente en cada cambio.
- **SC-003**: Una ruta nueva agregada al backend sin regenerar el
  contrato hace fallar la verificación automática correspondiente, sin
  excepción.
- **SC-004**: Las dos acciones huérfanas (cancelar asignación, reenviar
  verificación) son ejecutables desde sus vistas existentes sin ningún
  paso adicional fuera de la aplicación.
- **SC-005**: Con este sprint cerrado, M1 AODB deja de ser el módulo con
  menor cobertura de superficie del sistema.

## Assumptions

- El backend ya expone los 3 endpoints REST de vuelos (alta, consulta,
  registro de estado) y los 2 endpoints huérfanos (cancelar asignación,
  solicitar verificación) -- este sprint no construye backend nuevo,
  solo su consumo desde la aplicación y la regeneración del contrato.
- El mecanismo de resolución de conflictos de escritura concurrente
  sobre un mismo vuelo ya existe en el backend; este sprint no lo
  modifica, solo asegura que su rechazo se presente con claridad en la
  interfaz.
- La generación automática del contrato de API puede implicar perder
  anotaciones descriptivas agregadas a mano en el documento actual --
  se acepta como costo de tener un contrato confiable, documentado como
  riesgo conocido, no como pendiente abierto.
- No se construyen en este sprint: administración de plantillas/pantallas
  FIDS, tarifarios, conciliación de pax, informes, ni las vistas de M9/D6
  -- son sprints posteriores de la misma fase (S1.16-S1.20).
