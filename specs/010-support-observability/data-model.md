# Data Model: Soporte D6 y observabilidad (S1.8)

Transcrito de `docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md` §11
(esquema `support`), con las decisiones de alcance G1/G2 de esta
feature (ver [research.md](./research.md) Decisión 4).

## `support.categoria_ticket`

Alcance G1: **global**.

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `codigo` | VARCHAR(30) | NO | UQ |
| `nombre` | VARCHAR(100) | NO | |

## `support.ticket`

Alcance G1: **tenant**.

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `tenant_id` | BIGINT | NO | FK → `tenants.tenant.id` |
| `categoria_id` | BIGINT | NO | FK → `categoria_ticket.id` |
| `creado_por_usuario_id` | BIGINT | NO | FK → `tenants.usuario.id` |
| `asignado_a_usuario_id` | BIGINT | SÍ | FK → `tenants.usuario.id` (rol `role_support`) |
| `severidad` | VARCHAR(10) | NO | CHK IN ('baja','media','alta','critica') |
| `estado` | VARCHAR(20) | NO | CHK IN ('abierto','en_progreso','esperando_cliente','resuelto','cerrado') |
| `asunto` | VARCHAR(200) | NO | |
| `creado_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `primera_respuesta_en` | TIMESTAMPTZ | SÍ | Se fija una única vez (FR-003) |
| `resuelto_en` | TIMESTAMPTZ | SÍ | |
| `sla_objetivo_min` | INTEGER | NO | Derivado del módulo afectado al crear (FR-002) |

**Transición de estado válida**: `abierto` → `en_progreso` →
(`esperando_cliente` ↔ `en_progreso`) → `resuelto` → `cerrado`. No se
permite saltar directamente de `abierto` a `resuelto`/`cerrado` sin
pasar por `en_progreso` (invariante de dominio, valida el patrón ya
usado para `etl_ejecucion` — ver Plan §9.1).

## `support.ticket_mensaje`

Alcance G1: **interno** (hereda tenant vía `ticket_id`; ver
research.md Decisión 4).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `ticket_id` | BIGINT | NO | FK → `ticket.id` |
| `autor_usuario_id` | BIGINT | NO | FK → `tenants.usuario.id` |
| `cuerpo` | TEXT | NO | |
| `enviado_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `es_interno` | BOOLEAN | NO | DEFAULT FALSE |

## `support.articulo_kb`

Alcance G1: **global** (sin `tenant_id`, SDD §11.4).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `titulo` | VARCHAR(200) | NO | UQ (titulo, version) |
| `cuerpo` | TEXT | NO | |
| `version` | INTEGER | NO | |
| `estado` | VARCHAR(20) | NO | CHK IN ('borrador','publicado','archivado') |
| `publicado_en` | TIMESTAMPTZ | SÍ | |
| `autor_usuario_id` | BIGINT | NO | FK → `tenants.usuario.id` |
| `embedding_ref` | VARCHAR(200) | SÍ | Puntero reservado, no usado en S1.8 (research.md Decisión 6) |

## `support.etiqueta`

Alcance G1: **global**.

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `nombre` | VARCHAR(50) | NO | UQ |

## `support.articulo_kb_etiqueta`

Alcance G1: **global** (asociación entre dos entidades globales).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `articulo_id` | BIGINT | NO | PK compuesta; FK → `articulo_kb.id` |
| `etiqueta_id` | BIGINT | NO | PK compuesta; FK → `etiqueta.id` |

## `support.changelog`

Alcance G1: **global**.

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `version_producto` | VARCHAR(20) | NO | UQ |
| `resumen` | VARCHAR(500) | NO | |
| `publicado_en` | TIMESTAMPTZ | NO | |

## `support.changelog_item`

Alcance G1: **global**.

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `changelog_id` | BIGINT | NO | FK → `changelog.id` |
| `modulo_id` | BIGINT | NO | FK → `catalogo.modulo.id` (redeclarado localmente, patrón ya usado en `aerohub_gates`/`aerohub_ramp`/`aerohub_gateway`) |
| `tipo_cambio` | VARCHAR(20) | NO | CHK IN ('nuevo','mejora','correccion','obsolescencia') |
| `descripcion` | VARCHAR(500) | NO | |

## Observabilidad (sin tabla nueva)

Uptime, consumo de error budget y estado de bloqueo de despliegue son
**derivados** de Prometheus en tiempo de consulta — no hay entidad
persistida nueva (research.md Decisión 1 y 2). El único rastro
persistido es el evento de auditoría de un *override* manual del
bloqueo, escrito en `compliance.log_auditoria` (esquema/tabla
sintéticos `"observabilidad"`/`"bloqueo_despliegue"`, mismo mecanismo
que la denegación de licencia de S1.7) — no requiere DDL nuevo.
