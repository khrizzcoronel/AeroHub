# Feature Specification: M2 FIDS -- plantillas y pantallas en tiempo real, detección de sin-señal

**Feature Branch**: `main`

**Created**: 2026-08-01 (spec retroactiva)

**Status**: Completado -- commit `55a9e95`

**Input**: Sprint S1.3 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.3. Distribución
de plantillas FIDS a pantallas físicas con detección de corte de señal
(RF-T03, RF-O07, RNF-P02, RNF-R04, RNF-PO01).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publicar una plantilla y que se refleje en las pantallas al instante (Priority: P1)

Como administrador de contenido del aeropuerto, necesito publicar una nueva
versión de una plantilla de información de vuelos y que todas las pantallas
que la usan la muestren en menos de 1 segundo, sin reiniciar ninguna
pantalla física.

**Why this priority**: es el propósito central del módulo FIDS -- información
de vuelos desactualizada en una pantalla física es un problema operacional
visible para pasajeros.

**Independent Test**: publicar una plantilla nueva vía `POST /fids/plantillas`
+ `PATCH /fids/pantallas/{id}/plantilla`, medir el tiempo hasta que el WS de
la pantalla recibe el evento.

**Acceptance Scenarios**:

1. **Given** una pantalla suscrita a `/fids/ws/pantalla/{codigo}`, **When**
   se le asigna una plantilla nueva, **Then** recibe el evento en menos de
   1 segundo (RNF-P02).
2. **Given** una plantilla con un campo de PII (p. ej. `pasajero`,
   `numero_boleto`), **When** se intenta publicar, **Then** se rechaza con
   422 (PN-11) -- el layout de FIDS nunca puede identificar a un pasajero.

---

### User Story 2 - Detectar una pantalla física que dejó de emitir señal (Priority: P1)

Como responsable de operaciones, necesito que el sistema detecte
automáticamente cuando una pantalla física deja de enviar heartbeats, en
menos de 60 segundos, para poder despachar mantenimiento antes de que un
pasajero note la pantalla apagada o congelada.

**Why this priority**: una pantalla "muerta" sin que nadie lo sepa es peor que
una pantalla con contenido desactualizado -- no hay forma de que un pasajero
la reporte si no está mirándola en ese momento.

**Independent Test**: simular el cese de heartbeats de una pantalla (o
retroceder su `ultima_senal_en`), correr el ciclo de monitoreo con un umbral
corto inyectado, confirmar la transición a `sin_senal`.

**Acceptance Scenarios**:

1. **Given** una pantalla sin heartbeat por más del umbral, **When** corre
   el ciclo de monitoreo, **Then** su estado pasa a `sin_senal`.
2. **Given** una pantalla en `mantenimiento`, **When** corre el ciclo,
   **Then** NO se transiciona a `sin_senal` (una pantalla apagada a
   propósito no es una alerta).

---

### User Story 3 - Reproducir una plantilla en una pantalla física real (Priority: P2)

Como integrador de hardware de pantallas, necesito una aplicación mínima
(`apps/fids-player`) que, dado el código de una pantalla, se conecte, cargue
su plantilla vigente, la renderice, y envíe heartbeats periódicos.

**Why this priority**: sin un reproductor de referencia, no hay forma de
verificar el sistema de punta a punta ni de integrar hardware real después.

**Independent Test**: abrir `apps/fids-player`, ingresar un código de
pantalla y un JWT, confirmar que carga la plantilla vigente y que los
heartbeats llegan al backend.

**Acceptance Scenarios**:

1. **Given** el código de una pantalla existente, **When** el reproductor se
   conecta, **Then** carga la plantilla vigente vía HTTP y se suscribe al WS
   para actualizaciones.
2. **Given** el reproductor conectado, **When** pasa el intervalo de
   heartbeat, **Then** envía `POST /fids/pantallas/{id}/heartbeat`.

### Edge Cases

- ¿Qué pasa si el WebSocket de una pantalla necesita resolver
  `código → id` antes de suscribirse, y esa consulta requiere contexto de
  tenant? `aerohub_repository.contexto` nunca se puebla para el scope
  `"websocket"` (el middleware HTTP no corre ahí) -- se resuelve poblando el
  contexto A MANO, solo para esa consulta puntual, dentro de la propia
  función del handler WS.
- ¿Qué pasa si el ciclo de monitoreo de sin-señal necesita escanear pantallas
  de TODOS los tenants? Corre bajo `alcance_global()` (proceso de
  plataforma), como CU-O18.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir publicar versiones INMUTABLES de una
  plantilla (cada publicación es un INSERT nuevo, nunca un UPDATE sobre una
  versión vigente).
- **FR-002**: El sistema DEBE rechazar cualquier plantilla cuyo
  `definicion_json` contenga una clave de un vocabulario cerrado de PII
  (PN-11), recorriendo el JSON completo, no solo el nivel raíz.
- **FR-003**: El sistema DEBE registrar pantallas físicas asociadas a un
  terminal y una plantilla vigente.
- **FR-004**: El sistema DEBE exponer un canal WebSocket por pantalla
  (`/fids/ws/pantalla/{codigo}`) que propague el cambio de plantilla en
  menos de 1 segundo (RNF-P02).
- **FR-005**: El sistema DEBE aceptar heartbeats periódicos de cada pantalla,
  actualizando `ultima_senal_en` y su estado a `en_linea`.
- **FR-006**: Un ciclo periódico de monitoreo DEBE detectar una pantalla sin
  heartbeat por más de 60 segundos y transicionarla a `sin_senal`
  (RNF-R04), salvo que esté en `mantenimiento`.
- **FR-007**: El sistema DEBE exponer métricas Prometheus de latencia de
  propagación WS y conteo de heartbeats/transiciones sin-señal en `/metrics`,
  exento de autenticación (scraping técnico).
- **FR-008**: `apps/fids-player` DEBE ser una aplicación Angular mínima
  funcional que reproduzca la plantilla vigente de una pantalla y envíe
  heartbeats.

### Key Entities

- **`PlantillaFids`**: `(nombre, version, definicion_json, vigente_desde)`
  -- versionada e inmutable; `definicion_json` es un layout declarativo sin
  ningún campo de PII.
- **`PantallaFids`**: `(codigo, terminal_id, plantilla_id, estado,
  ultima_senal_en)` -- `estado ∈ {en_linea, sin_senal, mantenimiento}`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Latencia de propagación de plantilla por WS < 1s (RNF-P02),
  medida contra un servidor real.
- **SC-002**: Una pantalla sin heartbeat se detecta como `sin_senal` en menos
  de 60s (RNF-R04); el intervalo del ciclo periódico (10s) deja margen real,
  no solo en el caso promedio.
- **SC-003**: PN-11 rechaza el 100% de los intentos de publicar una plantilla
  con un campo de PII, en cualquier profundidad del JSON.
- **SC-004**: El reproductor Angular, ejercitado en un navegador real,
  muestra un cambio de plantilla publicado por HTTP en tiempo real.
- **SC-005**: Regresión completa de la suite de tests en verde
  (`232 passed` al cierre de este sprint), ruff/mypy/bandit/import-linter
  en verde.

## Assumptions

- No se construye un dashboard de Grafana para las métricas de FIDS en este
  sprint -- se expone `/metrics` (scrapeable) pero el panel visual queda
  fuera de alcance, decisión explícita tomada con el usuario al inicio del
  sprint.
- El reproductor Angular no maneja reconexión avanzada de WebSocket
  (backoff, reintentos automáticos) -- reconexión manual por ahora, un
  reproductor de hardware real lo añadiría después.
