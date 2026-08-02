# Feature Specification: M5 Revenue & Billing + M6 Passenger Experience

**Feature Branch**: `main`

**Created**: 2026-08-01

**Status**: Draft

**Input**: Sprint S1.6 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.6. Tarifación
normalizada, facturación conciliada y tiempos de espera agregados sin PII
(RF-O15, RF-O17, RF-E02 parcial, RF-T10, CU-O17, CU-O19).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El motor de facturación calcula la factura mensual automáticamente (Priority: P1)

Como sistema (motor de facturación, sin intervención humana en el cálculo),
necesito consolidar al cierre del período los despegues, aterrizajes y usos
de infraestructura de un tenant, aplicar el tarifario vigente en ese momento,
y emitir una factura por aerolínea -- para que el `role_billing_officer`
tenga algo que revisar en vez de calcularlo a mano.

**Why this priority**: es el propósito central de M5 -- sin cálculo
automático, la facturación de un aeropuerto con decenas de vuelos diarios es
inviable manualmente, y es el requisito que consolida ingresos reales
(RF-E02, OE1).

**Independent Test**: cerrar un período con vuelos y usos de infraestructura
ya registrados, ejecutar el cálculo de facturación, y confirmar que la
factura resultante concilia al 100% con los movimientos consolidados del
período (RF-O15).

**Acceptance Scenarios**:

1. **Given** un tenant con vuelos completados en el período y un tarifario
   vigente, **When** se ejecuta el cálculo de facturación, **Then** se
   genera un `cargo_aeronautico` por cada hecho facturable (slot operado,
   uso de manga, estacionamiento, tasa por pasajero), con la tarifa y el
   monto aplicados en ese momento como instantánea inmutable.
2. **Given** los cargos aeronáuticos del período, **When** se emite la
   factura, **Then** cada línea de la factura referencia exactamente un
   `cargo_aeronautico` (sin duplicar ni omitir ninguno) y el total de la
   factura se deriva de la suma de sus líneas, sin almacenarse como columna
   propia.

---

### User Story 2 - Cambiar el tarifario vigente no altera facturas históricas (Priority: P1)

Como responsable de negocio, necesito poder publicar una nueva versión del
tarifario (nuevos montos por concepto) sin que esa publicación afecte
retroactivamente ningún cargo o factura ya calculados con la versión
anterior.

**Why this priority**: es la garantía de integridad financiera central del
módulo -- una factura que cambia de monto después de emitida es, por
definición, un error contable grave.

**Independent Test**: calcular una factura con el tarifario A vigente,
publicar el tarifario B, y confirmar que la factura ya emitida sigue
mostrando los montos calculados con el tarifario A.

**Acceptance Scenarios**:

1. **Given** un `cargo_aeronautico` calculado con la tarifa vigente al
   momento del cálculo, **When** se publica una nueva versión del tarifario
   con montos distintos, **Then** el `cargo_aeronautico` histórico
   conserva su `tarifa_aplicada` y `monto_calculado` originales, sin
   cambio alguno.
2. **Given** un tarifario nuevo publicado, **When** se calculan cargos
   DESPUÉS de esa publicación, **Then** usan la tarifa nueva -- la
   inmutabilidad protege lo histórico, no congela el sistema completo.

---

### User Story 3 - El operador de facturación concilia la factura y registra disputas (Priority: P2)

Como `role_billing_officer`, necesito revisar la factura generada
automáticamente, confirmar que concilia contra los movimientos del período
sin diferencias, y poder registrar una disputa sobre una línea específica si
no estoy de acuerdo con un cargo.

**Why this priority**: cierra el ciclo de CU-O17 -- sin esta revisión
humana, una factura mal calculada (por un bug en el motor, por ejemplo)
llegaría al tenant sin ningún control.

**Independent Test**: conciliar una factura contra `conciliacion_pax` y
confirmar diferencia cero; registrar una disputa sobre una línea y
confirmar que queda trazada sin alterar el cálculo original.

**Acceptance Scenarios**:

1. **Given** una factura emitida, **When** `role_billing_officer` la
   concilia contra los movimientos de pasajeros del período, **Then** la
   diferencia es cero (se deriva, no se almacena como columna).
2. **Given** una línea de factura en disputa, **When** se registra la
   disputa, **Then** la línea queda marcada en revisión con trazabilidad
   completa del cálculo original, sin modificar `monto_calculado`.

---

### User Story 4 - El sistema estima y publica tiempos de espera por terminal, sin PII (Priority: P2)

Como sistema (sin intervención humana), necesito calcular una estimación
agregada del tiempo de espera por puerta/terminal a partir de datos
operativos ya existentes (ocupación de puertas, histórico de turnaround), y
publicarla, para que un pasajero (vía pantalla FIDS o portal público) tenga
una expectativa razonable sin que el sistema capture ningún dato individual
sobre él.

**Why this priority**: es el propósito central de M6 -- mejora la
experiencia del pasajero (OE4) sin el costo/riesgo de capturar información
nominal (RNF-S05).

**Independent Test**: con datos de ocupación de puertas y turnarounds ya
existentes en el sistema, ejecutar la estimación y confirmar que se publica
una fila de `tiempo_espera_agregado` por terminal/franja, con un conteo de
muestras (`muestra_n`), sin ningún campo que pueda identificar a un
pasajero (PN-11).

**Acceptance Scenarios**:

1. **Given** datos de `ops.asignacion_puerta` y `rampa.turnaround` del día,
   **When** se ejecuta la estimación, **Then** se publica un tiempo de
   espera agregado por terminal y franja horaria, con `muestra_n > 0`.
2. **Given** cualquier intento de incluir un campo que identifique a un
   pasajero individual en el modelo de datos de M6, **When** se valida,
   **Then** se rechaza (PN-11, igual que el guardia ya construido para
   `definicion_json` de FIDS en S1.3).
3. **Given** una estimación ya publicada, **When** pasan más de 15 minutos
   sin una actualización nueva, **Then** se considera una violación del
   requisito de frescura (RF-O17) -- a verificar con una medición explícita,
   no solo asumida.

### Edge Cases

- ¿Qué pasa si un período de facturación se cierra sin ningún vuelo
  completado? El cálculo produce cero cargos y ninguna factura -- no es un
  error, es un período sin actividad facturable.
- ¿Qué pasa si dos cargos aeronáuticos terminan referenciados por la misma
  línea de factura? No debe ser posible -- `factura_linea` lleva un
  `UNIQUE` sobre `cargo_aeronautico_id`.
- ¿Qué pasa si `role_support` intenta leer cualquier dato de `billing`?
  Debe rechazarse -- la matriz de privilegios NO le da acceso a `billing`
  (segregación de funciones, compuerta de pruebas explícita del sprint).
- ¿Qué pasa si la estimación de tiempo de espera de una terminal no tiene
  ninguna puerta con actividad reciente? `muestra_n = 0` y la fila no se
  publica (o se publica con un valor nulo explícito) -- nunca se inventa un
  estimado sin datos de respaldo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mantener un catálogo global de conceptos
  facturables (`concepto_cargo`), independiente del tenant.
- **FR-002**: El sistema DEBE permitir publicar versiones de un tarifario
  (`tarifario` + `tarifario_concepto`) por tenant, con vigencia temporal,
  soportando variantes de precio por volumen sin desplegar código nuevo
  (RF-T10).
- **FR-003**: El motor de facturación DEBE consolidar, al cierre de un
  período, los hechos facturables del tenant desde `ops` (despegues,
  aterrizajes, uso de infraestructura, pasajeros) y generar un
  `cargo_aeronautico` por cada uno, aplicando el tarifario VIGENTE en ese
  momento.
- **FR-004**: Cada `cargo_aeronautico` DEBE almacenar `tarifa_aplicada` y
  `monto_calculado` como instantánea inmutable -- una publicación posterior
  de un tarifario nuevo NUNCA modifica un cargo ya calculado.
- **FR-005**: El sistema DEBE emitir una `factura` por aerolínea y período,
  compuesta de `factura_linea` (cada una referenciando exactamente un
  `cargo_aeronautico`, con `UNIQUE` sobre esa referencia); el total de la
  factura se DERIVA de sus líneas, no se almacena.
- **FR-006**: El sistema DEBE permitir conciliar una factura contra los
  movimientos de pasajeros del período (`conciliacion_pax`), con la
  diferencia SIEMPRE derivada (cero si concilia), nunca almacenada como
  columna.
- **FR-007**: `role_billing_officer` DEBE poder revisar facturas, registrar
  y trazar disputas sobre líneas específicas, sin poder alterar el cálculo
  original de un cargo.
- **FR-008**: `role_support` NO DEBE tener ningún acceso (ni lectura) a
  datos del esquema `billing` (segregación de funciones).
- **FR-009**: El sistema DEBE estimar, de forma automática y periódica, un
  tiempo de espera agregado por terminal y franja horaria
  (`billing.tiempo_espera_agregado`), derivado de datos operativos ya
  existentes (ocupación de `ops.asignacion_puerta`, histórico de
  `rampa.turnaround`) -- nunca de un dato individual de pasajero.
- **FR-010**: El modelo de datos de M6 DEBE tener 0 campos capaces de
  identificar a un pasajero individual, verificado estructuralmente
  (PN-11), no solo por convención documentada.
- **FR-011**: La estimación de tiempo de espera DEBE actualizarse con una
  frecuencia tal que ninguna fila quede desactualizada por más de 15
  minutos (RF-O17).

### Key Entities

- **`ConceptoCargo`**: catálogo global -- `(codigo, nombre)`, ej. "tasa de
  aterrizaje", "uso de manga", "estacionamiento", "tasa por pasajero".
- **`Tarifario`** (cabecera) + **`TarifarioConcepto`** (detalle): versión
  vigente de precios por tenant y concepto -- resuelve una relación
  ternaria (tenant × concepto × vigencia) en 5NF.
- **`CargoAeronautico`**: instantánea inmutable de un hecho facturable ya
  calculado -- `(vuelo_id o referencia de infraestructura, concepto,
  tarifa_aplicada, monto_calculado)`.
- **`Factura`** + **`FacturaLinea`**: agregado de cargos por aerolínea y
  período; el total se deriva de las líneas.
- **`ConciliacionPax`**: cruce de una factura contra los movimientos de
  pasajeros del período; la diferencia se deriva.
- **`TiempoEsperaAgregado`**: `(terminal, franja_horaria, estimado_minutos,
  muestra_n)` -- sin ningún campo de pasajero individual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una factura mensual generada por el motor concilia al 100%
  con los movimientos consolidados del período, sin diferencias (RF-O15,
  RF-E02).
- **SC-002**: Cambiar la tarifa vigente después de calcular un cargo NUNCA
  altera ese cargo ni ninguna factura que ya lo incluya -- verificado
  explícitamente, no solo por diseño.
- **SC-003**: `role_support` no puede leer ni escribir ningún dato de
  `billing` -- verificado con una petición HTTP real que confirme el
  rechazo.
- **SC-004**: El modelo de datos de M6 tiene 0 campos de PII, verificado
  estructuralmente (PN-11).
- **SC-005**: La estimación de tiempo de espera se actualiza con una
  frecuencia que garantiza ninguna fila desactualizada por más de 15
  minutos, medido explícitamente.
- **SC-006**: Regresión completa de las pruebas negativas ya existentes
  (PN-01 a PN-11) en verde tras agregar los dos módulos nuevos.

## Assumptions

- El "período" de facturación (mensual, según el nombre del CU) se trata
  como un rango de fechas parametrizable en el cálculo, no hay un job
  calendario automático de cierre de mes en el alcance de este sprint --
  el disparo del cálculo es una operación explícita (vía API), no un cron.
- La sincronización de la estimación de tiempo de espera con las pantallas
  FIDS (mencionada en el flujo de CU-O19) es una integración deseable pero
  NO bloqueante para el cierre de este sprint si el tiempo no alcanza --
  la publicación en `billing.tiempo_espera_agregado` y su exposición por
  API son el entregable mínimo verificable.
- `role_operations_controller` u otro rol con acceso de escritura a `ops`
  no participa en la facturación -- el cálculo es enteramente un proceso
  de sistema (motor de facturación), sin un caso de uso de "registrar cargo
  manualmente" en el alcance de este sprint (no está en el catálogo de CU
  fuente).
- Los "movimientos del período" contra los que concilia `conciliacion_pax`
  son los propios registros operativos de `ops` (vuelos y pasajeros
  estimados) ya consolidados en los cargos -- no una fuente bancaria o de
  pasarela de pago externa, que no está modelada en ningún documento
  fuente de este sprint.
