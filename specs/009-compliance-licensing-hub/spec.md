# Feature Specification: S1.7 -- Licenciamiento, credenciales y Compliance Hub

**Feature Branch**: `main`

**Created**: 2026-08-02

**Status**: Draft

**Input**: Sprint S1.7 del `docs/PLAN_IMPLEMENTACION_v2.0.md` §8.7. Cerrar el
control de acceso por licencia y la auditoría append-only (RF-O18, RF-O12,
RF-O13, RNF-S04, CU-O20, CU-O13).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El sistema deniega acceso a un módulo sin licencia vigente (Priority: P1)

Como sistema (Gateway, sin intervención humana), necesito verificar en
cada solicitud a un módulo que el tenant tiene una licencia activa para
ese módulo, para que ningún tenant use funcionalidad que no contrató --
y que ese rechazo quede auditado.

**Why this priority**: es el propósito central del sprint (CU-O20/RF-O18)
y la única compuerta de pruebas que el propio plan de sprint nombra en el
DoD ("PN-09 en verde").

**Independent Test**: un tenant sin licencia activa para un módulo invoca
cualquier endpoint de ese módulo -- la respuesta es 403 en el 100% de los
casos, y aparece una fila nueva en `compliance.log_auditoria` por cada
intento.

**Acceptance Scenarios**:

1. **Given** un tenant con `tenants.licencia` vigente para el módulo
   `billing` (`activa_desde` pasada, `activa_hasta` nula o futura),
   **When** invoca un endpoint de `billing`, **Then** la solicitud se
   procesa normalmente (la licencia no es la causa de ningún rechazo).
2. **Given** un tenant SIN fila de `tenants.licencia` para el módulo
   `billing`, **When** invoca cualquier endpoint de `billing`, **Then**
   la respuesta es HTTP 403 y se registra un evento en
   `compliance.log_auditoria`.
3. **Given** un tenant con una licencia ya vencida
   (`activa_hasta` en el pasado), **When** invoca el módulo
   correspondiente, **Then** la respuesta es HTTP 403 -- vencida se trata
   igual que ausente, no como un caso especial.

---

### User Story 2 - role_sre redacta y cierra un post-mortem con acciones de remediación (Priority: P1)

Como `role_sre`, necesito documentar la causa raíz y las acciones de
remediación de un incidente Sev1/Sev2 dentro de las 72 horas posteriores a
su resolución, con una línea de tiempo trazable, para que el incidente
quede cerrado de forma auditable sin depender de memoria institucional.

**Why this priority**: es el segundo elemento explícito del DoD del sprint
("post-mortem publicable < 72h con eventos correlacionados") y la única
excepción documentada a la regla de auditoría append-only (ADR-009) --
verificarla correctamente es tan crítica como la regla general que
excepciona.

**Independent Test**: crear un post-mortem en `estado='en_progreso'`,
agregar acciones de remediación, cerrarlas todas, transicionar el
post-mortem a `estado='publicado'` -- cada edición de `causa_raiz`/
`estado` queda reflejada en `compliance.log_auditoria`.

**Acceptance Scenarios**:

1. **Given** un incidente resuelto, **When** `role_sre` crea un
   post-mortem, **Then** se crea en `compliance.post_mortem` con
   `estado='en_progreso'` e `iniciado_en` poblado.
2. **Given** un post-mortem en progreso, **When** `role_sre` edita
   `causa_raiz`, **Then** el cambio se persiste (única tabla de
   `compliance` con UPDATE permitido) Y queda una fila nueva en
   `compliance.log_auditoria` documentando el cambio.
3. **Given** un post-mortem con acciones de remediación pendientes,
   **When** se marcan todas como `completada`, **Then** `role_sre` puede
   transicionar el post-mortem a `estado='publicado'` con
   `publicado_en` poblado.
4. **Given** un post-mortem con acciones de remediación SIN completar,
   **When** se intenta publicar, **Then** la operación se rechaza -- no
   se puede cerrar un post-mortem con remediación abierta.
5. **Given** un rol distinto de `role_sre` (p. ej. `role_support`),
   **When** intenta crear o editar un post-mortem, **Then** la operación
   se rechaza -- la excepción de mutabilidad es exclusiva de `role_sre`
   (ADR-009).

---

### User Story 3 - La auditoría append-only cubre las 5 tablas nuevas del esquema compliance (Priority: P2)

Como responsable de cumplimiento, necesito que ningún registro de
incidente de seguridad, reporte regulatorio, acceso de auditor o
evidencia SOC 2 pueda alterarse ni borrarse una vez creado, para que la
evidencia de cumplimiento sea confiable ante una auditoría externa.

**Why this priority**: es "PN-04 reforzada" del DoD del sprint -- ya
vigente para `compliance.log_auditoria` desde S0.2, esta historia la
extiende a las tablas nuevas de este sprint.

**Independent Test**: para cada una de `incidente_seguridad`,
`reporte_dgac`, `acceso_auditor`, `evidencia_soc2`, un intento de
UPDATE/DELETE a través de la capa de repositorio se rechaza -- no existe
ningún método de mutación expuesto para esas operaciones.

**Acceptance Scenarios**:

1. **Given** un `incidente_seguridad` ya creado, **When** se intenta
   modificarlo o borrarlo vía `aerohub_repository`, **Then** no existe
   ninguna función que lo permita (verificado por análisis estático,
   mismo criterio que PN-15).
2. **Given** un reporte DGAC ya emitido (`reporte_dgac`), **When** se
   intenta modificar `hash_contenido` o cualquier otra columna, **Then**
   no existe ninguna función que lo permita.
3. **Given** una fila de `acceso_auditor` o `evidencia_soc2` ya creada,
   **When** se intenta mutarla, **Then** no existe ninguna función que lo
   permita.
4. **Given** las 5 tablas append-only del esquema `compliance`
   (`log_auditoria`, `incidente_seguridad`, `reporte_dgac`,
   `acceso_auditor`, `evidencia_soc2`), **When** se audita el código de
   `aerohub_compliance.infrastructure`, **Then** ninguna expone
   `UPDATE`/`DELETE` -- solo `post_mortem`/`post_mortem_accion` los
   permiten, y exclusivamente para `role_sre`.

---

### User Story 4 - Rotación de API Keys con evento auditado (Priority: P3)

Como `role_platform_admin` o `role_tenant_admin`, necesito rotar una API
Key existente (generar un secreto nuevo, invalidar el anterior) sin
interrumpir el servicio del tenant, para cumplir con la política de
rotación periódica de credenciales sin coordinar una ventana de
mantenimiento.

**Why this priority**: RF-O12 cubre credenciales, API Keys y certificados
TLS -- certificados TLS y secretos de infraestructura ya están fuera de
alcance de este sprint (gestionados por el Vault del proveedor PaaS, ver
Assumptions); la porción aplicable al dominio de este repositorio (API
Keys ya modeladas en `tenants.api_key` desde S1.2) es la única con una
superficie de código real a implementar, y el DoD del sprint no la
menciona como compuerta bloqueante -- por eso P3, no P1.

**Independent Test**: rotar una API Key existente produce una fila nueva
en `compliance.log_auditoria` documentando el evento; la API Key anterior
dejaría de autenticar peticiones nuevas sin que el tenant pierda acceso al
sistema (la rotación no lo deja sin ninguna credencial válida).

**Acceptance Scenarios**:

1. **Given** una API Key activa, **When** `role_platform_admin` la rota,
   **Then** se emite un secreto nuevo y la fila anterior transiciona a
   `estado != 'activa'`, sin eliminar la fila (P5, sin DELETE físico).
2. **Given** una rotación de API Key, **When** se ejecuta, **Then** queda
   una fila en `compliance.log_auditoria` con `operacion='UPDATE'`
   documentando el evento (RF-O12: "evento registrado en auditoría").

### Edge Cases

- ¿Qué pasa si un tenant tiene licencia vigente para OTRO módulo pero no
  para el que está pidiendo? Se deniega igual -- la verificación es por
  `(tenant_id, modulo_id)`, no por tenant en general.
- ¿Qué pasa si `tenants.licencia.activa_hasta` es exactamente el instante
  de la solicitud? Se trata como vencida (no vigente) -- el intervalo de
  vigencia es cerrado por la izquierda y abierto por la derecha
  (`activa_desde <= ahora < activa_hasta`), consistente con cómo el resto
  del sistema trata intervalos de tiempo (p. ej. `asignacion_puerta`).
- ¿Qué pasa si `role_sre` intenta publicar un post-mortem sin haber
  documentado `causa_raiz`? Se rechaza -- un post-mortem publicado sin
  causa raíz no cumple el propósito blameless-pero-trazable del CU-O13.
- ¿Qué pasa si dos post-mortems distintos referencian el mismo
  `incidente_ref`? No está prohibido por ningún CU/RF fuente -- un
  incidente grande puede generar seguimiento en más de un post-mortem
  (p. ej. un post-mortem inicial y uno de seguimiento); no se agrega una
  restricción `UNIQUE` que el modelo fuente no exige.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE verificar, en cada solicitud a un módulo
  con licenciamiento aplicable, que el tenant tiene una fila vigente en
  `tenants.licencia` para ese módulo (`activa_desde <= ahora <
  activa_hasta`, o `activa_hasta` nula) -- aplicado en el API Gateway
  (ADR-014), antes de que la solicitud llegue al módulo de negocio.
- **FR-002**: El sistema DEBE denegar con HTTP 403 toda solicitud a un
  módulo sin licencia vigente, en el 100% de los casos, sin excepción por
  rol (ni siquiera `role_platform_admin` evade la verificación de
  licencia -- es un control de plataforma, no de autorización por rol).
- **FR-003**: El sistema DEBE registrar en `compliance.log_auditoria` todo
  intento denegado por falta de licencia.
- **FR-004**: `role_sre` DEBE poder crear un `post_mortem` en estado
  `en_progreso`, editar `causa_raiz`, y transicionarlo a `publicado` --
  única excepción de mutabilidad del esquema `compliance` (ADR-009).
- **FR-005**: El sistema DEBE impedir publicar un `post_mortem` mientras
  tenga alguna `post_mortem_accion` en estado distinto de `completada`.
- **FR-006**: Ningún rol distinto de `role_sre` DEBE poder crear ni editar
  un `post_mortem` o sus `post_mortem_accion`.
- **FR-007**: El sistema DEBE registrar en `compliance.log_auditoria` toda
  edición de `causa_raiz`/`estado` de un `post_mortem`, preservando
  trazabilidad pese a la excepción de mutabilidad.
- **FR-008**: `incidente_seguridad`, `reporte_dgac`, `acceso_auditor` y
  `evidencia_soc2` DEBEN ser append-only -- la capa de repositorio NO
  DEBE exponer ningún método de UPDATE/DELETE sobre ellas.
- **FR-009**: El sistema DEBE permitir rotar una API Key existente
  (`tenants.api_key`), emitiendo un secreto nuevo sin eliminar la fila
  anterior (P5, sin DELETE físico), y registrando el evento en
  `compliance.log_auditoria`.

### Key Entities

- **`Licencia`**: `(tenant_id, modulo_id, activa_desde, activa_hasta)` --
  ya modelada en `tenants.licencia` desde S0.2/S1.1; este sprint agrega la
  verificación de acceso en el Gateway, no el modelo de datos.
- **`PostMortem`** + **`PostMortemAccion`**: causa raíz, línea de tiempo,
  estado de ciclo de vida hasta publicación; acciones de remediación como
  entidad separada (1NF respecto a v5.1).
- **`IncidenteSeguridad`**: incidente de seguridad física/digital,
  distinto de `PostMortem` (que cubre caídas de servicio en general).
- **`ReporteDgac`**: reporte regulatorio emitido con hash SHA-256 de
  integridad.
- **`AccesoAuditor`**: ventana temporal de acceso otorgada a un
  `role_regulatory_auditor` con alcance explícito.
- **`EvidenciaSoc2`**: artefacto de evidencia de un control SOC 2,
  opcionalmente referenciando una fila de `log_auditoria`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una solicitud a un módulo sin licencia vigente recibe HTTP
  403 en el 100% de los casos, con el evento auditado (PN-09).
- **SC-002**: Un post-mortem puede publicarse en menos de 72 horas desde
  el inicio del incidente, con línea de tiempo de eventos correlacionados
  (meta OP16 del CU-O13) -- medido explícitamente, no solo asumido.
- **SC-003**: Ningún endpoint expuesto permite mutar
  `incidente_seguridad`, `reporte_dgac`, `acceso_auditor` ni
  `evidencia_soc2` -- verificado por análisis estático y por prueba de
  integración negativa.
- **SC-004**: Toda rotación de API Key produce exactamente un evento
  nuevo en `compliance.log_auditoria`.
- **SC-005**: Regresión completa de las pruebas negativas PN-01 a PN-11 ya
  existentes en verde tras agregar el módulo de licenciamiento y las
  tablas nuevas de `compliance`.

## Assumptions

- La validación de licencia (FR-001/002) se implementa como middleware o
  dependencia del Gateway que se ejecuta DESPUÉS de la autenticación JWT
  (ya sabe `tenant_id`) y ANTES de despachar al router del módulo --
  mismo punto de intercepción que `AutenticacionJWTMiddleware`, no una
  verificación repetida en cada endpoint individual.
- El mapeo endpoint→módulo licenciable se resuelve por prefijo de ruta
  (`/billing/*` → módulo `billing`, `/rampa/*` → módulo `rampa`, etc.),
  ya que no existe otro mecanismo de metadatos de router en el código
  fuente para asociar un endpoint a un `modulo_id` de `catalogo.modulo`.
- La columna `estado` sugerida por el hallazgo M-05 del SDD para
  `tenants.licencia` (distinguir suspendida de vencida) NO se agrega en
  este sprint -- es una mejora de modelo de datos documentada como
  hallazgo, no un requisito de ningún RF/CU fuente de S1.7; el modelo
  actual (`activa_desde`/`activa_hasta`) es suficiente para RF-O18/CU-O20
  tal como están especificados.
- RF-O12 se implementa solo para API Keys (`tenants.api_key`, ya modelada
  desde S1.2) -- rotación de certificados TLS y secretos de
  infraestructura general es responsabilidad del Vault del proveedor PaaS
  (SDD hallazgo M-07, estrategia v6.0 línea 1186) y no tiene una tabla ni
  caso de uso propio en el modelo de datos de este repositorio.
- `compliance.log_auditoria` YA EXISTE desde S0.2 (DDL fundacional) y ya
  se usa transversalmente vía `aerohub_repository.registrar_auditoria` --
  este sprint no la recrea, solo verifica/extiende su cobertura (PN-04
  reforzada) a las tablas nuevas.
- El "sistema de observabilidad (Grafana/PagerDuty)" que CU-O13 menciona
  como fuente de la línea de tiempo automática de alertas está fuera del
  alcance de este repositorio (M8 Observability no tiene módulo propio
  todavía) -- la línea de tiempo se modela como el propio historial de
  `log_auditoria` correlacionado por `tenant_id`/ventana de tiempo, no
  como una integración real con un sistema externo.
