# Data Model: Soporte D6

Sin cambios de esquema -- las 5 tablas de `support.*` ya existen desde
S1.8 (`services/support/aerohub_support/infrastructure/tablas.py`).
Este documento describe las entidades tal como las consume el
frontend nuevo, no una migración.

## Ticket

Caso de soporte, tenant-scoped.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string (Snowflake) | |
| `tenant_id` | string (Snowflake) | tenant dueño del ticket |
| `categoria_id` | string (Snowflake) | referencia a `support.categoria_ticket` |
| `creado_por_usuario_id` | string (Snowflake) | |
| `asignado_a_usuario_id` | string \| null | |
| `severidad` | `baja` \| `media` \| `alta` \| `critica` | |
| `estado` | `abierto` \| `en_progreso` \| `esperando_cliente` \| `resuelto` \| `cerrado` | máquina de estados, ver `domain/ticket.py::transicion_valida` |
| `asunto` | string | |
| `creado_en` | datetime ISO | |
| `primera_respuesta_en` | datetime ISO \| null | usado junto con `sla_objetivo_min` para el indicador de SLA (research.md Decisión 3) |
| `resuelto_en` | datetime ISO \| null | |
| `sla_objetivo_min` | int | calculado por el backend al crear el ticket, no editable |

**Transiciones válidas** (`domain/ticket.py`):
`abierto → en_progreso`, `en_progreso ↔ esperando_cliente`,
`en_progreso → resuelto`, `resuelto → cerrado`. Cualquier otra
combinación es rechazada por el backend con 409.

## Mensaje de ticket

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string (Snowflake) | |
| `autor_usuario_id` | string (Snowflake) | |
| `cuerpo` | string | |
| `enviado_en` | datetime ISO | |
| `es_interno` | boolean | si es `true`, no debe presentarse como visible al tenant (FR-003) |

## Artículo de base de conocimientos

**Sin `tenant_id`** -- contenido compartido entre todos los tenants
(research.md Decisión 4, FR-008).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string (Snowflake) | |
| `titulo` | string | |
| `cuerpo` | string | |
| `version` | int | cada publicación nueva es una versión, nunca sobrescribe |
| `publicado_en` | datetime ISO \| null | |
| `etiquetas` | string[] | usadas para el filtro de búsqueda |

## Entrada de changelog

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string (Snowflake) | |
| `version_producto` | string | |
| `resumen` | string | |
| `publicado_en` | datetime ISO | |
| `items` | `ItemChangelog[]` | |

### Item de changelog

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string (Snowflake) | |
| `modulo_id` | string (Snowflake) | referencia a `catalogo.modulo` (M1-M9) |
| `tipo_cambio` | `nuevo` \| `mejora` \| `correccion` \| `obsolescencia` | |
| `descripcion` | string | |
