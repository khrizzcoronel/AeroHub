# Feature Specification: Tarifarios y conciliación de pax

**Feature Branch**: `019-tarifarios-conciliacion-pax`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "S1.17 -- Fase 1.5, sprint 3: Tarifarios y conciliacion de pax (docs/PLAN_IMPLEMENTACION_v3.0.md §8-bis.3). RF-T10 promete 'variantes de tarifario aplicables sin despliegue de codigo' pero hoy exige un INSERT manual en MonetDB -- servicios/billing/aerohub_billing/api/router.py ya tiene POST /billing/tarifarios, POST /billing/tarifarios/{id}/conceptos, POST /billing/tarifarios/{id}/activar, POST /billing/conciliaciones, GET /billing/conciliaciones/{id}, POST /billing/conciliaciones/{id}/conciliar -- todos sin ningun consumidor en apps/web. Faltan endpoints de listado (tarifarios, conciliaciones). Alcance: GETs de listado tenant-scoped, vista de tarifarios (alta, conceptos, activar con aviso de inmutabilidad), vista/seccion de conciliacion de pax (registrar, ver diferencia derivada, conciliar). Fuera de alcance: motor de facturación (ya cerrado en S1.6), informes (S1.18), segregación de funciones (ya existente, no se toca)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publicar una variante de tarifario sin tocar la base de datos (Priority: P1)

Un administrador de tenant necesita crear una nueva versión de tarifario
aeronáutico (por ejemplo, para reflejar un ajuste anual de tarifas) sin
pedirle a nadie que ejecute un `INSERT` manual en la base de datos. Crea
la cabecera del tarifario (moneda, notas), agrega los conceptos de cargo
con su tarifa unitaria, y lo activa cuando está listo. El sistema
advierte explícitamente que activar este tarifario no modifica ningún
cargo ya calculado con el tarifario anterior.

**Why this priority**: Es el caso que motiva el sprint -- RF-T10 promete
"variantes de tarifario sin despliegue de código" y hoy es falso en la
práctica; sin esto, el requisito queda incumplido en el fondo aunque
esté "cumplido" en el papel (los endpoints existen desde S1.6).

**Independent Test**: Se puede probar por completo creando un tarifario
nuevo, agregándole al menos un concepto, activándolo, y verificando que
aparece como "vigente" en la tabla -- sin escribir ningún SQL a mano.

**Acceptance Scenarios**:

1. **Given** un tenant con un tarifario vigente ya activo, **When** el
   administrador crea un tarifario nuevo en el mismo moneda con al menos
   un concepto y lo activa, **Then** el tarifario nuevo pasa a estado
   "vigente" y el anterior deja de estarlo, sin alterar ningún cargo
   aeronáutico histórico ya calculado con el tarifario anterior.
2. **Given** un tarifario recién creado sin ningún concepto, **When** el
   administrador intenta activarlo, **Then** el sistema deja claro (antes
   de o al intentar la activación) que un tarifario sin conceptos no es
   útil para facturar, replicando cualquier validación que el backend ya
   aplique.
3. **Given** un tarifario que el administrador está a punto de activar,
   **When** ve la pantalla de confirmación, **Then** el sistema muestra
   explícitamente que los cargos y facturas ya emitidos con el tarifario
   vigente actual no se verán afectados.

---

### User Story 2 - Ver el historial completo de tarifarios de mi tenant (Priority: P2)

Un administrador de tenant necesita ver todos los tarifarios que ha
tenido su aeropuerto -- vigentes, retirados e inactivos -- junto con sus
conceptos y tarifas, para auditar qué tarifa aplicaba en cada período.

**Why this priority**: Sin un listado completo, la única forma de saber
qué tarifarios existen es consultando la base de datos directamente --
el mismo problema de fondo que motiva todo el sprint, aplicado a lectura
en vez de a escritura.

**Independent Test**: Se puede probar abriendo la vista de tarifarios y
verificando que se listan todos los tarifarios del tenant (no solo el
vigente), cada uno con sus conceptos visibles al expandir/ver detalle.

**Acceptance Scenarios**:

1. **Given** un tenant con 3 tarifarios (1 vigente, 2 históricos),
   **When** el administrador abre la vista de tarifarios, **Then** ve
   los 3 en una tabla, con el estado de cada uno claramente distinguible.
2. **Given** un tarifario con varios conceptos agregados, **When** el
   administrador ve su detalle, **Then** ve cada concepto con su tarifa
   unitaria.

---

### User Story 3 - Registrar y resolver una conciliación de pasajeros (Priority: P2)

Un administrador de tenant necesita registrar, para un vuelo y un
período dados, el conteo de pasajeros reportado por la aerolínea junto
con el conteo que el sistema tiene registrado (ambos capturados en el
momento de registrar la conciliación), ver la diferencia derivada entre
ambos, y marcar la conciliación como resuelta cuando la diferencia sea
cero.

**Why this priority**: Es el segundo caso de uso explícito del sprint
(RF-O15) -- sin esta vista, conciliar un vuelo requiere pedirle a
alguien con acceso a la base de datos que lo haga por fuera de la
aplicación.

**Independent Test**: Se puede probar registrando una conciliación para
un vuelo con un conteo de aerolínea distinto al del sistema, verificando
que la diferencia mostrada es la resta correcta, y marcándola como
conciliada.

**Acceptance Scenarios**:

1. **Given** un vuelo y un período, **When** el administrador registra
   una conciliación con un conteo de aerolínea y un conteo de sistema
   distintos entre sí, **Then** el sistema muestra la diferencia entre
   ambos conteos como un valor calculado, nunca como un campo que el
   usuario escribe directamente.
2. **Given** una conciliación registrada con diferencia distinta de
   cero, **When** el administrador intenta marcarla como "conciliada",
   **Then** el sistema rechaza la operación y dice por qué -- solo una
   diferencia de cero puede marcarse como conciliada (regla ya aplicada
   por el backend desde S1.6, la interfaz no la relaja ni la duplica).
3. **Given** una conciliación registrada con diferencia igual a cero,
   **When** el administrador la marca como "conciliada", **Then** la
   conciliación pasa a un estado que indica que fue revisada y cerrada,
   visible en el listado.
4. **Given** un tenant con varias conciliaciones registradas, **When**
   el administrador abre la vista, **Then** ve todas las conciliaciones
   del tenant en una tabla, con la diferencia de cada una visible sin
   tener que abrir el detalle.

---

### Edge Cases

- ¿Qué pasa si dos tarifarios de la misma moneda intentan estar
  "vigente" al mismo tiempo? El backend ya garantiza "a lo sumo uno
  vigente por (tenant, moneda)" (ver `obtener_tarifario_vigente`,
  S1.6) -- la interfaz debe reflejar el rechazo del backend si ocurre,
  no intentar prevenirlo por su cuenta con lógica duplicada.
- ¿Qué pasa si la diferencia de una conciliación es cero (conteos
  coinciden)? Debe mostrarse igual como "0", no ocultarse ni tratarse
  como caso de error.
- ¿Qué pasa si el administrador intenta agregar el mismo concepto de
  cargo dos veces al mismo tarifario? El backend decide si lo permite o
  lo rechaza (fuera de alcance de este sprint modificar esa regla); la
  interfaz solo debe mostrar con claridad el error que el backend
  devuelva.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir crear la cabecera de un tarifario
  nuevo (moneda, notas) desde la aplicación, sin requerir acceso directo
  a la base de datos.
- **FR-002**: El sistema DEBE permitir agregar conceptos de cargo (del
  catálogo existente) a un tarifario, cada uno con su tarifa unitaria.
- **FR-003**: El sistema DEBE permitir activar un tarifario, mostrando
  antes de confirmar un aviso explícito de que los cargos y facturas ya
  emitidos con el tarifario anterior no se ven afectados.
- **FR-004**: El sistema DEBE listar todos los tarifarios del tenant
  (vigentes e históricos), no solo el vigente.
- **FR-005**: El sistema DEBE mostrar, para cada tarifario, sus conceptos
  de cargo con su tarifa unitaria.
- **FR-006**: El sistema DEBE permitir registrar una conciliación de
  pasajeros para un vuelo y un período, capturando el conteo reportado
  por la aerolínea y el conteo registrado por el sistema (ambos son
  datos de entrada al registrar; el modelo no calcula el conteo de
  sistema automáticamente, verificado contra `registrar_conciliacion`).
- **FR-007**: El sistema DEBE mostrar la diferencia entre el conteo de
  aerolínea y el conteo de sistema como un valor calculado en el momento
  de la consulta, nunca como un dato que el usuario ingresa directamente
  o que se guarda como columna propia.
- **FR-008**: El sistema DEBE permitir marcar una conciliación como
  conciliada únicamente cuando su diferencia es cero, mostrando un
  mensaje claro si el usuario intenta hacerlo con una diferencia
  distinta de cero (regla ya aplicada por el backend, `puede_conciliar`).
- **FR-009**: El sistema DEBE listar todas las conciliaciones del
  tenant, mostrando la diferencia de cada una sin requerir abrir el
  detalle.
- **FR-010**: El sistema DEBE aplicar el mismo aislamiento por tenant que
  el resto de la aplicación -- ningún usuario puede ver tarifarios o
  conciliaciones de un tenant distinto al propio.

### Key Entities *(include if feature involves data)*

- **Tarifario**: cabecera de una variante de tarifas aeronáuticas para un
  tenant y una moneda, con un estado (p. ej. vigente / histórico /
  borrador) y una fecha de vigencia. A lo sumo uno puede estar "vigente"
  por tenant y moneda a la vez.
- **Concepto de tarifario**: la tarifa unitaria que un tarifario asigna a
  un concepto de cargo del catálogo (p. ej. aterrizaje, estacionamiento).
- **Concepto de cargo**: catálogo de solo lectura de los tipos de cargo
  aeronáutico que existen (independiente del tenant).
- **Conciliación de pasajeros**: registro, por vuelo y período, del
  conteo de pasajeros reportado por la aerolínea frente al conteo del
  sistema, con un estado que indica si ya fue revisada/cerrada. La
  diferencia entre ambos conteos es siempre un valor derivado, nunca
  almacenado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador de tenant puede publicar y activar un
  tarifario nuevo, con al menos un concepto, sin ninguna intervención
  fuera de la aplicación (cero `INSERT` manuales).
- **SC-002**: El histórico de tarifarios y cargos permanece observable e
  inalterado después de activar un tarifario nuevo -- verificable
  comparando el total de una factura ya emitida antes y después de la
  activación.
- **SC-003**: Un administrador de tenant puede registrar y resolver una
  conciliación de pasajeros para un vuelo específico en menos de 1
  minuto, sin salir de la aplicación.
- **SC-004**: El 100% de los endpoints de tarifarios y conciliación ya
  existentes en el backend (S1.6) tienen al menos un punto de consumo
  real en `apps/web` al cierre de este sprint.

## Assumptions

- El motor de facturación (`calcular_facturacion`, S1.6) no se modifica
  en este sprint -- este sprint solo cierra la superficie de usuario
  sobre tarifarios y conciliación, no cambia su lógica de negocio.
- La segregación de funciones ya existente (p. ej. `role_support` sin
  acceso a `billing`) se mantiene sin cambios; este sprint no agrega ni
  quita scopes de ningún rol salvo lo estrictamente necesario para que
  los roles que ya tienen acceso a `billing` puedan ver las vistas
  nuevas (mismo criterio que el hallazgo de scopes de S1.16, verificar
  antes de asumir que ya está resuelto).
- Los informes derivados de tarifarios/conciliación (comparativas,
  tendencias) quedan fuera de alcance -- corresponden a la familia RF-I
  del sprint S1.18.
- "Sin despliegue de código" (RF-T10) se interpreta como "sin necesidad
  de una migración de base de datos ni de tocar el backend" -- una vez
  cerrado este sprint, publicar una variante de tarifario es una
  operación 100% de aplicación.
