# Fase 1 -- Modelo de Datos: S1.7 Licenciamiento, credenciales y Compliance Hub

**Feature**: [spec.md](./spec.md) | **Fuente de verdad del esquema**:
`docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md` §10, transcrito fielmente.
Las tablas marcadas "YA EXISTE" no se tocan en este sprint -- se listan
solo para contexto de FK.

## Ya existentes (sin cambios de DDL)

- **`tenants.licencia`** (`id, tenant_id, modulo_id, activa_desde,
  activa_hasta`) -- S0.2.
- **`tenants.api_key`** (`id, tenant_id, prefijo, hash_secreto,
  creada_en, rotada_en, expira_en, estado`) -- S1.2.
- **`compliance.log_auditoria`** (`id, tenant_id, esquema, tabla,
  registro_id, operacion, usuario_id, rol_codigo, ocurrido_en,
  valores_anteriores, valores_nuevos, ip_origen`) -- S0.2, append-only.
- **`catalogo.modulo`** (`id, codigo VARCHAR(4), nombre,
  departamento_id`) -- DDL de S0.1, sin filas sembradas hasta este
  sprint (ver research.md Decisión 2).

## Nuevas -- esquema `compliance` (propiedad de `aerohub_compliance`)

### `tipo_incidente` (catálogo global)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| codigo | VARCHAR(30) | NO | UQ |
| descripcion | VARCHAR(200) | NO | |
| categoria | VARCHAR(50) | NO | |

### `incidente_seguridad` (append-only)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| tenant_id | BIGINT | NO | |
| tipo_incidente_id | BIGINT | NO | FK → `tipo_incidente.id` |
| descripcion | VARCHAR(500) | NO | |
| severidad | VARCHAR(10) | NO | CHK IN ('baja','media','alta','critica') |
| detectado_en | TIMESTAMPTZ | NO | |
| reportado_por_usuario_id | BIGINT | NO | FK → `tenants.usuario.id` |
| estado | VARCHAR(20) | NO | CHK IN ('abierto','en_investigacion','contenido','cerrado') |

**Nota de append-only**: `estado` avanza mediante INSERT de una fila
nueva referenciando el mismo incidente conceptualmente por
`(tenant_id, tipo_incidente_id, detectado_en)` -- el modelo fuente no
define una FK de "incidente padre" para encadenar transiciones de estado
sin mutar la fila original; fuera de alcance de este sprint modelar esa
cadena (no la exige ningún FR/CU fuente).

### `tipo_reporte_regulatorio` (catálogo global)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| codigo | VARCHAR(30) | NO | UQ |
| nombre | VARCHAR(150) | NO | |
| periodicidad | VARCHAR(20) | NO | |
| autoridad | VARCHAR(20) | NO | CHK IN ('DGAC','OACI') |

### `reporte_dgac` (append-only)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| tenant_id | BIGINT | NO | |
| tipo_reporte_id | BIGINT | NO | FK → `tipo_reporte_regulatorio.id` |
| periodo_inicio | DATE | NO | |
| periodo_fin | DATE | NO | CHK ≥ periodo_inicio |
| contenido_ref | VARCHAR(500) | NO | URI al artefacto exportado |
| hash_contenido | CHAR(64) | NO | SHA-256 |
| emitido_por_usuario_id | BIGINT | NO | FK → `tenants.usuario.id` |
| emitido_en | TIMESTAMPTZ | NO | DEFAULT now() |

### `acceso_auditor` (append-only)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| tenant_id | BIGINT | NO | |
| auditor_usuario_id | BIGINT | NO | FK → `tenants.usuario.id` (rol `role_regulatory_auditor`) |
| otorgado_por_usuario_id | BIGINT | NO | FK → `tenants.usuario.id` |
| inicio | TIMESTAMPTZ | NO | |
| fin | TIMESTAMPTZ | NO | CHK > inicio |
| alcance_json | JSON | NO | |
| motivo | VARCHAR(300) | NO | |

### `post_mortem` (única tabla del esquema con UPDATE, exclusivo `role_sre`)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| tenant_id | BIGINT | SÍ | |
| incidente_ref | VARCHAR(100) | NO | |
| severidad | VARCHAR(10) | NO | CHK IN ('baja','media','alta','critica') |
| causa_raiz | TEXT | SÍ | Editable -- excepción ADR-009 |
| estado | VARCHAR(20) | NO | CHK IN ('en_progreso','publicado') |
| iniciado_en | TIMESTAMPTZ | NO | |
| publicado_en | TIMESTAMPTZ | SÍ | Meta OP16: ≤ 72h desde `iniciado_en` |
| tiempo_resolucion_min | INTEGER | SÍ | CHK ≥ 0 |

**Invariante de dominio (FR-005)**: `publicado_en` solo se puebla si
TODAS las `post_mortem_accion` de este `post_mortem` están en
`estado='completada'` -- validado en `application/`, no expresable como
CHECK de MonetDB (requiere agregación sobre otra tabla).

### `post_mortem_accion`

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| post_mortem_id | BIGINT | NO | FK → `post_mortem.id` |
| descripcion | VARCHAR(300) | NO | |
| responsable_usuario_id | BIGINT | NO | FK → `tenants.usuario.id` |
| ticket_ref | VARCHAR(50) | SÍ | |
| estado | VARCHAR(20) | NO | CHK IN ('pendiente','en_progreso','completada','vencida') |
| vence_en | TIMESTAMPTZ | NO | |
| completada_en | TIMESTAMPTZ | SÍ | |

### `control_soc2` (catálogo global)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| codigo_control | VARCHAR(20) | NO | UQ -- p. ej. CC6.1, CC7.2 |
| nombre | VARCHAR(200) | NO | |
| categoria | VARCHAR(50) | NO | |

### `evidencia_soc2` (append-only)

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| id | BIGINT | NO | PK |
| control_soc2_id | BIGINT | NO | FK → `control_soc2.id` |
| tenant_id | BIGINT | SÍ | |
| periodo_inicio | DATE | NO | |
| periodo_fin | DATE | NO | |
| referencia_log_id | BIGINT | SÍ | FK → `log_auditoria.id` |
| ruta_artefacto | VARCHAR(500) | NO | |
| hash_artefacto | CHAR(64) | NO | |
| generado_en | TIMESTAMPTZ | NO | DEFAULT now() |

## Alcances G1/G2 (guardián de tenant)

| Tabla | Alcance | Notas |
|:---|:---|:---|
| `tipo_incidente` | global | catálogo |
| `incidente_seguridad` | tenant | |
| `tipo_reporte_regulatorio` | global | catálogo |
| `reporte_dgac` | tenant | |
| `acceso_auditor` | tenant | |
| `post_mortem` | tenant | `tenant_id` nullable -- un incidente de plataforma sin tenant específico usa `alcance_global()` (ADR-019 G3), mismo patrón que el monitor de señal FIDS |
| `post_mortem_accion` | interno | sin `tenant_id` propio -- aislado transitivamente vía `post_mortem_id`, mismo patrón que `tarifario_concepto` en S1.6 |
| `control_soc2` | global | catálogo |
| `evidencia_soc2` | tenant | `tenant_id` nullable, mismo motivo que `post_mortem` -- evidencia de plataforma agregada, no por tenant |

## Catálogo sembrado en este sprint (`db/seeds/generate.py`)

- `catalogo.modulo`: `AODB`, `FIDS`, `GATE`, `RAMP`, `BILL`, `PASS` (ver
  research.md Decisión 2).
- `compliance.tipo_incidente`: al menos un código de ejemplo para pruebas
  (`acceso_no_autorizado`).
- `compliance.tipo_reporte_regulatorio`: al menos un código de ejemplo
  (`informe_mensual_operaciones`, autoridad `DGAC`).
- `compliance.control_soc2`: al menos un código de ejemplo (`CC6.1`).
