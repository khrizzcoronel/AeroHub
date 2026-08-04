# Feature Specification: Compliance Hub (M9)

**Feature Branch**: `021-compliance-hub`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "S1.19 -- Fase 1.5, sprint 5: Compliance Hub (docs/PLAN_IMPLEMENTACION_v3.0.md §8-bis.5). Dar superficie a los 11 endpoints de M9 construidos en S1.7 -- role_regulatory_auditor y role_sre tienen rol asignado y ninguna pantalla. Entregables: vista de incidentes de seguridad (alta y consulta), vista de post-mortems con acciones y publicacion, emision/consulta de reportes DGAC con verificacion de hash, consulta de evidencia SOC2, registro de accesos de auditor. Compuerta: PN-04 reforzada (ninguna pantalla ofrece mutacion sobre las tablas append-only), integridad por hash verificada, post-mortem publicable con eventos correlacionados."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Investigar un incidente de seguridad hasta su post-mortem (Priority: P1)

Un ingeniero de guardia (`role_sre`) registra un incidente de seguridad
apenas lo detecta, y más tarde abre un post-mortem para ese incidente:
documenta la causa raíz, agrega acciones de remediación con
responsable y fecha límite, y lo publica cuando está completo.

**Why this priority**: Es el flujo central del módulo (CU-O13) y el que
motiva el sprint -- hoy los 2 endpoints de post-mortem existen desde
S1.7 pero ningún rol humano puede alcanzarlos (hallazgo de scopes,
ver más abajo).

**Independent Test**: Se puede probar por completo creando un
incidente, creando un post-mortem para él, agregando una acción,
completándola, y publicando el post-mortem -- sin salir de la
aplicación.

**Acceptance Scenarios**:

1. **Given** un incidente de seguridad ya registrado, **When** el
   ingeniero de guardia crea un post-mortem referenciándolo, **Then**
   el post-mortem queda en estado abierto, editable.
2. **Given** un post-mortem abierto, **When** el ingeniero edita la
   causa raíz y agrega una o más acciones de remediación, **Then**
   cada acción queda visible con su responsable y fecha límite.
3. **Given** un post-mortem con sus acciones ya completadas, **When**
   el ingeniero lo publica, **Then** el post-mortem pasa a estado
   publicado y ya no admite más ediciones de causa raíz.
4. **Given** un post-mortem publicado, **When** cualquier intento
   (directo, sin pasar por la interfaz) de modificarlo llega al
   backend, **Then** el sistema lo rechaza -- ninguna pantalla ofrece
   esa mutación, y el backend tampoco la permite (PN-04 reforzada).

---

### User Story 2 - Emitir y verificar un reporte regulatorio DGAC (Priority: P1)

Un responsable de cumplimiento emite un reporte DGAC para un período,
y más tarde puede consultarlo junto con su hash de contenido, para
confirmar que lo que se presentó a la autoridad no fue alterado desde
la emisión.

**Why this priority**: Es el segundo caso de uso central (RF-T11) --
sin listado ni verificación, "emisión" es una escritura ciega sin
forma de auditar después qué se emitió.

**Independent Test**: Se puede probar emitiendo un reporte DGAC nuevo
y verificando que aparece en el listado con su hash de contenido
visible e inalterado.

**Acceptance Scenarios**:

1. **Given** un tipo de reporte regulatorio del catálogo, **When** el
   responsable de cumplimiento emite un reporte para un período,
   **Then** el reporte queda registrado con su hash de contenido.
2. **Given** varios reportes ya emitidos, **When** el responsable abre
   el listado, **Then** ve todos los reportes con su tipo, período y
   hash, sin tener que consultar la base de datos.

---

### User Story 3 - Auditor externo revisa evidencia SOC 2 y accesos otorgados (Priority: P2)

Un auditor externo (`role_regulatory_auditor`), con acceso temporal ya
otorgado, consulta la evidencia SOC 2 disponible para el período de su
revisión, sin poder modificar nada.

**Why this priority**: Es el DoD explícito del sprint ("un auditor
externo completa su revisión sin que nadie ejecute SQL en su nombre")
-- pero depende de que exista al menos un acceso otorgado (US4), así
que es P2 frente al flujo de post-mortem/DGAC que no tiene esa
dependencia.

**Independent Test**: Se puede probar listando la evidencia SOC 2 de
un control y período conocidos, verificando que el auditor solo puede
leer, nunca escribir (ningún botón de mutación visible ni alcanzable).

**Acceptance Scenarios**:

1. **Given** evidencia SOC 2 ya registrada para un control y período,
   **When** el auditor la consulta, **Then** ve la referencia del
   artefacto y su hash, sin poder editarla ni borrarla.

---

### User Story 4 - Otorgar y ver un acceso de auditor con ventana temporal (Priority: P2)

Un administrador de tenant otorga acceso temporal a un auditor
externo, con fecha de inicio y fin explícitas y un motivo, y luego
puede ver el listado de accesos otorgados con su ventana vigente.

**Why this priority**: Habilita US3 (el auditor necesita el acceso
otorgado primero) y cierra el flujo de auditoría -- P2 porque en sí
mismo es una operación de administración, no la revisión regulatoria
en sí.

**Independent Test**: Se puede probar otorgando un acceso con una
ventana de fechas válida y verificando que aparece en el listado con
esa ventana visible.

**Acceptance Scenarios**:

1. **Given** un auditor identificado por su usuario, **When** el
   administrador otorga acceso con inicio, fin y motivo, **Then** el
   acceso queda registrado y visible en el listado con su ventana.

---

### Edge Cases

- ¿Qué pasa si alguien intenta editar la causa raíz de un post-mortem
  ya publicado? El backend ya lo rechaza (`RolNoAutorizado`/estado
  inválido, S1.7) -- la interfaz no ofrece la acción para un
  post-mortem publicado, y aunque se forzara la llamada, el backend
  reafirma el rechazo (PN-04 reforzada).
- ¿Qué pasa si el hash de contenido de un reporte DGAC no coincide con
  lo esperado tras la emisión? El sistema no recalcula el hash -- lo
  muestra tal cual quedó registrado en el momento de la emisión, para
  que quien audite compare contra el artefacto real por fuera del
  sistema.
- ¿Qué pasa con `role_sre`, que hoy no tiene ningún scope `compliance:*`
  pese a que el dominio exige exactamente ese rol para post-mortems
  (`_exigir_role_sre`, S1.7)? Es el hallazgo crítico de este sprint --
  ver Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir registrar un incidente de
  seguridad (tipo, descripción, severidad, fecha de detección) desde
  la aplicación.
- **FR-002**: El sistema DEBE listar los incidentes de seguridad del
  tenant.
- **FR-003**: El sistema DEBE permitir crear un post-mortem referenciando
  un incidente, exclusivamente para `role_sre` (ADR-009).
- **FR-004**: El sistema DEBE permitir editar la causa raíz y agregar
  acciones de remediación a un post-mortem no publicado.
- **FR-005**: El sistema DEBE permitir marcar una acción de remediación
  como completada.
- **FR-006**: El sistema DEBE permitir publicar un post-mortem,
  transición que el backend ya trata como definitiva (S1.7).
- **FR-007**: El sistema DEBE listar los post-mortems del tenant, con
  acceso a su detalle (acciones incluidas).
- **FR-008**: El sistema DEBE permitir emitir un reporte DGAC (tipo,
  período, referencia de contenido, hash) desde la aplicación.
- **FR-009**: El sistema DEBE listar los reportes DGAC emitidos, con su
  hash de contenido visible.
- **FR-010**: El sistema DEBE permitir otorgar un acceso temporal de
  auditor (usuario, ventana de fechas, alcance, motivo).
- **FR-011**: El sistema DEBE listar los accesos de auditor otorgados,
  con su ventana vigente visible.
- **FR-012**: El sistema DEBE listar la evidencia SOC 2 registrada, de
  solo lectura para cualquier rol que la consulte.
- **FR-013**: El sistema DEBE aplicar el mismo aislamiento por tenant
  que el resto de la aplicación a las 5 entidades de este módulo.
- **FR-014**: El sistema DEBE asegurar que `role_sre` puede efectivamente
  alcanzar los endpoints de post-mortem e incidentes que el dominio ya
  le exige en exclusiva -- corrige el hallazgo crítico de scopes.

### Key Entities *(include if feature involves data)*

- **Incidente de seguridad**: evento detectado, con tipo, severidad y
  estado; puede dar origen a un post-mortem.
- **Post-mortem**: análisis de un incidente, con causa raíz, estado
  (abierto/publicado) y una lista de acciones de remediación. Único
  registro de `compliance.*` que admite UPDATE controlado (S1.7);
  inmutable una vez publicado.
- **Acción de remediación**: tarea derivada de un post-mortem, con
  responsable, fecha límite y estado.
- **Reporte DGAC**: documento regulatorio emitido para un período, con
  referencia de contenido y hash -- append-only.
- **Acceso de auditor**: ventana temporal otorgada a un usuario auditor
  externo, con alcance y motivo -- append-only.
- **Evidencia SOC 2**: artefacto de evidencia para un control y
  período -- append-only, de solo lectura para todos los roles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los 11 endpoints de M9 ya existentes desde S1.7 tienen
  al menos un punto de consumo real en `apps/web` al cierre de este
  sprint.
- **SC-002**: `role_sre` puede crear, editar y publicar un post-mortem
  de punta a punta desde la aplicación (hoy imposible por el hallazgo
  de scopes).
- **SC-003**: Ninguna de las 5 tablas append-only de `compliance.*`
  admite una mutación desde ninguna pantalla nueva de este sprint,
  verificado por inspección de la interfaz y por regresión contra el
  backend.
- **SC-004**: Un post-mortem se puede crear, documentar y publicar en
  menos de 5 minutos desde la aplicación, sin ninguna consulta SQL
  manual.

## Assumptions

- **Hallazgo crítico de scopes (verificar antes de implementar, no
  asumir resuelto)**: `role_sre` no tiene ningún scope `compliance:*`
  en `packages/contracts/aerohub_contracts/roles_modulos.py` pese a que
  `_exigir_role_sre()` (S1.7, `gestionar_post_mortem.py`) exige
  exactamente ese rol para crear/editar/publicar post-mortems -- mismo
  patrón que el hallazgo de FIDS en S1.16. Se corrige agregando
  `compliance:leer`/`compliance:escribir` y el módulo `M9` a
  `role_sre`.
- Los 5 tipos de dato de este módulo son de solo lectura para
  `role_regulatory_auditor` (`compliance:leer` únicamente) -- ningún
  botón de creación/edición se muestra para ese rol.
- No se modifica la lógica de negocio de M9 (S1.7) -- este sprint
  cierra superficie de usuario, igual que S1.15/S1.16/S1.17/S1.18.
- La verificación de integridad del hash del reporte DGAC (mencionada
  en la compuerta de pruebas del plan) se interpreta como "el hash
  queda visible e inalterado tras la consulta", no como un recálculo
  automático contra un artefacto externo -- el sistema no almacena el
  contenido real del reporte, solo su referencia y hash.
