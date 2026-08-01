# Feature Specification: M4 Ground Operations -- turnaround, y dockerización completa del stack

**Feature Branch**: `main`

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commits `0d95b2e` (turnaround) y `36c2f45` (CLAUDE.md)

**Input**: Sprint S1.5 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.5. Turnaround
como entidad propia que empareja llegada y salida (RF-O16, OP2b, CU-O16).
Ampliado durante el sprint, a pedido explícito del usuario, con la
dockerización completa del gateway y los frontends (antes corrían sueltos en
el host).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Emparejar el vuelo de llegada y el de salida de una misma aeronave (Priority: P1)

Como controlador de operaciones, necesito crear un turnaround que empareje
explícitamente el vuelo de llegada y el de salida de la MISMA aeronave, para
que el sistema tenga un punto de anclaje único donde registrar las tareas de
tierra entre ambos vuelos.

**Why this priority**: sin esta entidad, las tareas de rampa quedarían
colgando de un vuelo suelto, sin representar el ciclo completo llegada→salida
que define un turnaround real.

**Independent Test**: `POST /rampa/turnarounds` con un vuelo de sentido `'L'`
y uno de sentido `'S'` de la misma aeronave crea el turnaround; con vuelos de
aeronaves distintas o sentidos incorrectos, lo rechaza.

**Acceptance Scenarios**:

1. **Given** un vuelo de llegada (`'L'`) y uno de salida (`'S'`) de la misma
   aeronave, **When** se crea el turnaround, **Then** se registra
   correctamente.
2. **Given** dos vuelos de aeronaves distintas, **When** se intenta crear el
   turnaround, **Then** se rechaza (422).
3. **Given** un vuelo de llegada que YA tiene un turnaround, **When** se
   intenta crear otro con el mismo vuelo de llegada, **Then** se rechaza
   (409) -- un vuelo de llegada participa en un único turnaround.

---

### User Story 2 - Registrar tiempos de tareas de rampa y detectar demoras automáticamente (Priority: P1)

Como agente de rampa, necesito marcar el inicio y el fin de cada tarea de
turnaround que realizo (combustible, catering, limpieza, equipaje), y que el
sistema me alerte automáticamente -- sin que yo tenga que reportarlo -- si
me tomé más tiempo del estándar para ese tipo de tarea.

**Why this priority**: es el propósito central del módulo (RF-O16) --
alimenta la detección de demoras operativas sin depender de que alguien lo
reporte manualmente.

**Independent Test**: finalizar una tarea cuya duración real excede el
estándar de su tipo genera una incidencia en menos de 60 segundos desde que
se marca el fin (medido, no solo asumido).

**Acceptance Scenarios**:

1. **Given** una tarea de tipo "combustible" (estándar 30 min), **When** se
   finaliza tras 45 minutos, **Then** se genera una incidencia con
   severidad `alta` (ruta crítica) en menos de 1 segundo desde la petición
   de fin.
2. **Given** la misma tarea finalizada dentro del estándar, **When** se
   marca el fin, **Then** NO se genera ninguna incidencia.

---

### User Story 3 - Un agente de rampa nunca ve ni modifica tareas de otro agente (Priority: P1)

Como responsable de seguridad, necesito que un agente de rampa solo pueda
leer y finalizar SUS PROPIAS tareas de turnaround -- ninguna tarea que otro
agente haya iniciado, ni siquiera dentro del mismo tenant.

**Why this priority**: mínimo privilegio real dentro de un mismo tenant, más
allá del aislamiento entre tenants ya garantizado desde S0.2.

**Independent Test**: un segundo agente de rampa del mismo tenant no ve la
tarea de otro agente al listarlas, y recibe 404 (no 403) al intentar
finalizarla.

**Acceptance Scenarios**:

1. **Given** una tarea iniciada por el agente A, **When** el agente B (mismo
   tenant, mismo rol) la lista, **Then** no aparece en su lista.
2. **Given** la misma tarea, **When** el agente B intenta finalizarla,
   **Then** responde 404 (nunca 403 -- PN-01 aplicado también dentro de un
   mismo tenant, entre usuarios).
3. **Given** un rol sin la restricción de mínimo privilegio (p. ej.
   `role_operations_controller`), **When** lista las tareas del turnaround,
   **Then** SÍ ve la tarea del agente A (control positivo).

---

### User Story 4 - Todo servicio que se use para desarrollar o verificar corre en Docker (Priority: P1)

Como responsable del proyecto, necesito que el backend compuesto
(`services/gateway`) y los dos frontends Angular corran en contenedores
Docker, igual que ya corre toda la infraestructura de datos, para que el
entorno de desarrollo sea reproducible de punta a punta con un solo comando.

**Why this priority**: pedido explícito del usuario durante este sprint,
tras notar que en S1.1-S1.4 el backend y los frontends siempre se habían
verificado corriendo sueltos en el host.

**Independent Test**: `docker compose up` levanta MonetDB + gateway + web +
fids-player, y una petición HTTP real contra el gateway dockerizado, desde un
navegador contra el frontend dockerizado, responde con datos reales.

**Acceptance Scenarios**:

1. **Given** el stack completo levantado vía Docker Compose, **When** se
   navega a `localhost:4200` y se hace una petición autenticada,
   **Then** el frontend dockerizado se comunica correctamente con el
   gateway dockerizado y trae datos reales de MonetDB.
2. **Given** la imagen del gateway construida, **When** se inspecciona,
   **Then** el DSN de conexión a MonetDB usa el hostname interno de la red
   de Compose (`monetdb`), no `localhost`.

### Edge Cases

- ¿Qué pasa si `uv sync` corre sobre el proyecto raíz sin `--all-packages`?
  Solo instala el grupo de herramientas de desarrollo (`dependency-groups.dev`),
  NO las dependencias productivas de ningún módulo -- la primera imagen
  construida arrancó sin `uvicorn` instalado por este motivo exacto.
- ¿Qué pasa si el `uv.lock` del repo está desactualizado respecto a
  dependencias agregadas en sprints anteriores sin que `uv` estuviera
  disponible en el host (`pulp` de S1.4, `prometheus-client` de S1.3)? Se
  regenera DENTRO del contenedor (donde `uv` sí está disponible) y se copia
  de vuelta al repo con `docker cp`.
- ¿Cuándo se conoce la duración real de una tarea de rampa para compararla
  contra el estándar? En el mismo instante en que se marca el fin -- no hace
  falta un ciclo de monitoreo periódico como el de sin-señal de FIDS (S1.3),
  porque "fin de tarea" es un evento explícito, no la ausencia de uno.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir crear un turnaround emparejando un
  vuelo de sentido `'L'` y uno de sentido `'S'` de la MISMA aeronave, del
  mismo tenant.
- **FR-002**: Un vuelo de llegada DEBE participar en un único turnaround
  (`UQ(tenant_id, vuelo_llegada_id)`).
- **FR-003**: El sistema DEBE permitir a un agente de rampa marcar el inicio
  de una tarea de turnaround (creando el registro, con el agente y el
  timestamp actuales) y marcar su fin.
- **FR-004**: La duración de una tarea DEBE derivarse de
  `fin_real - inicio_real`; NUNCA se almacena como columna.
- **FR-005**: Al finalizar una tarea, el sistema DEBE comparar su duración
  contra `duracion_estandar_min` de su tipo, y generar una
  `incidencia_rampa` SINCRÓNICAMENTE (en la misma petición) si la excede --
  sin depender de un ciclo de fondo.
- **FR-006**: La severidad de la incidencia DEBE ser `alta` si el tipo de
  tarea es de ruta crítica, `media` en caso contrario -- pero la incidencia
  se genera para CUALQUIER tarea que exceda su estándar, sin condicionar la
  generación al indicador de ruta crítica.
- **FR-007**: Un agente de rampa (`role_ramp_agent`) DEBE poder leer y
  finalizar únicamente las tareas donde él mismo es el agente registrado --
  ninguna tarea de otro agente, ni siquiera dentro del mismo tenant. Otros
  roles con acceso a `rampa` (operaciones, plataforma) NO tienen esta
  restricción.
- **FR-008**: `apps/web` DEBE tener un panel de turnaround: crear
  turnaround, iniciar/finalizar tareas, ver incidencias generadas.
- **FR-009**: El gateway (`services/gateway`) y los frontends (`apps/web`,
  `apps/fids-player`) DEBEN poder levantarse íntegramente vía Docker Compose,
  con el gateway resolviendo MonetDB por el hostname interno de la red de
  Compose.

### Key Entities

- **`Turnaround`**: `(vuelo_llegada_id, vuelo_salida_id, aeronave_id,
  inicio_previsto, fin_previsto, estado)`.
- **`TareaTurnaround`**: `(turnaround_id, tipo_tarea_id, agente_usuario_id,
  inicio_real, fin_real, estado)` -- duración siempre derivada, nunca
  almacenada.
- **`IncidenciaRampa`**: `(tarea_turnaround_id, tipo_incidencia_id,
  descripcion, severidad, detectada_en)` -- generada automáticamente, sin
  columna numérica de magnitud de desviación (queda en `descripcion`).
- **`TipoTarea`**: catálogo -- `(codigo, duracion_estandar_min,
  es_ruta_critica)`. Ejemplos sembrados: combustible (30 min, crítica),
  catering (20 min), limpieza (15 min), equipaje (25 min, crítica).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: RF-O16 se cumple con margen amplio: incidencia generada en
  ~0.9s desde la petición de fin de tarea (exigido < 60s).
- **SC-002**: El mínimo privilegio de `role_ramp_agent` se verifica en ambos
  sentidos (no ve/no puede finalizar tarea ajena) más un control positivo
  (otro rol sí ve todo), con peticiones HTTP reales.
- **SC-003**: Regresión completa en verde (294/294 tests al cierre del
  sprint), ruff/mypy/bandit/import-linter en verde.
- **SC-004**: Los 4 contenedores del stack (MonetDB, gateway, web,
  fids-player) arrancan limpios vía `docker compose up` y se verifican en
  vivo -- petición HTTP real desde un navegador contra el frontend
  dockerizado trae datos reales de MonetDB a través del gateway dockerizado.
- **SC-005**: `uv.lock` del repositorio queda sincronizado con las
  dependencias reales de todos los módulos (corrige una desactualización
  arrastrada desde S1.3).

## Assumptions

- No hay un caso de uso documentado de "crear turnaround" separado de
  "registrar tareas" en el catálogo de casos de uso original -- se asume que
  `role_ramp_agent` (el único rol con escritura sobre `rampa` en la matriz de
  privilegios) también crea el turnaround, no solo sus tareas.
- Las tareas de turnaround NO se pre-crean vacías esperando ser reclamadas --
  una fila de `tarea_turnaround` solo existe desde que un agente marca su
  inicio (createlo, con agente y timestamp ya fijos).
- `npm ci` no se usa en las imágenes de los frontends (se usa `npm install`)
  porque el lockfile del repo se generó con una versión de npm más nueva que
  la de la imagen base -- decisión pragmática de imagen de desarrollo, no de
  build reproducible de producción.
