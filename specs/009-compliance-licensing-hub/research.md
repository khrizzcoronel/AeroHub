# Fase 0 -- Investigación: S1.7 Licenciamiento, credenciales y Compliance Hub

**Feature**: [spec.md](./spec.md) | **Fecha**: 2026-08-02

No quedan `[NEEDS CLARIFICATION]` en `spec.md`. Esta fase documenta las
decisiones técnicas necesarias para diseñar `data-model.md`, partiendo de
lo que YA EXISTE en el código (verificado leyendo el repo, no asumido):

- `tenants.licencia` (`db/ddl/monetdb/02_tenants.sql`) YA EXISTE desde
  S0.2: `(id, tenant_id, modulo_id, activa_desde, activa_hasta)`, UQ
  `(tenant_id, modulo_id, activa_desde)`.
- `tenants.api_key` YA EXISTE con columna `rotada_en` sin usar todavía --
  `crear_api_key`/`revocar_api_key` existen en
  `services/tenancy/aerohub_tenancy/application/gestionar_api_key.py`
  (S1.2); `rotar_api_key` NO existe.
- `compliance.log_auditoria` YA EXISTE desde S0.2 y ya se usa
  transversalmente vía `aerohub_repository.registrar_auditoria`.
- `catalogo.modulo` (`(id, codigo VARCHAR(4), nombre, departamento_id)`)
  YA EXISTE **y YA está sembrado** desde el propio DDL fundacional
  (`01_catalogo.sql`, INSERT de S0.1) con los códigos `M1`..`M9` (M1=AODB,
  M2=FIDS Management, M3=Terminal & Gate Manager, M4=Ground Operations,
  M5=Revenue & Billing, M6=Passenger Experience) -- corrección respecto a
  una primera lectura de esta investigación que asumió, incorrectamente,
  que la tabla estaba vacía por no encontrar un `INSERT` en
  `db/seeds/generate.py` (el INSERT real vive en el DDL, no en el seed).
- `services/compliance` está scaffoldeado (`domain/application/
  infrastructure/api` vacíos); `services/tenancy` ya tiene código real
  (aprovisionamiento + gestión de API Keys, S1.1/S1.2).
- `AutenticacionJWTMiddleware`
  (`services/gateway/aerohub_gateway/api/middleware.py`) es el único
  punto donde el Gateway puebla `contexto_tenant_id()`/
  `contexto_rol_actor()` y aplica rate limiting DESPUÉS de autenticar,
  ANTES de despachar al router -- mismo patrón exacto que necesita la
  verificación de licencia (RF-O18: "aplicada por el API Gateway").

## Decisión 1: Verificación de licencia vive en `aerohub_gateway`, no en `aerohub_compliance`

- **Decisión**: la lógica de "¿esta ruta requiere licencia y el tenant la
  tiene vigente?" se implementa en `aerohub_gateway.application.
  verificar_licencia`, invocada desde `AutenticacionJWTMiddleware`
  inmediatamente después de `contexto_autenticado(identidad)`, en el
  mismo punto donde hoy se aplica `peticion_permitida` (rate limiting).
  El evento de denegación se escribe en `compliance.log_auditoria` vía
  `aerohub_repository.registrar_auditoria` (accesible desde cualquier
  módulo, no exclusivo de `aerohub_compliance`).
- **Racional**: RF-O18 dice literalmente "aplicada por el API Gateway
  como control de aplicación (ADR-014)" -- no es una regla de negocio de
  `compliance`, es un control transversal de enrutamiento, exactamente
  como el rate limiting que ya vive ahí. Poner esta lógica en
  `aerohub_compliance` obligaría a `aerohub_gateway` a importarlo,
  violando la independencia de módulos (.importlinter) del mismo modo
  que ya se evitó para `aerohub_contracts.requiere_scope`.
- **Alternativas consideradas**: middleware separado en
  `aerohub_compliance` -- rechazada, requeriría que `aerohub_gateway`
  importe otro módulo de negocio, exactamente el patrón que el ADR-017
  prohíbe.

## Decisión 2: Mapeo endpoint→módulo por prefijo de ruta, con catálogo sembrado en este sprint

- **Decisión**: `catalogo.modulo` se siembra (en `db/seeds/generate.py`,
  mismo patrón que `TIPOS_TAREA`/`CONCEPTO_CARGO`) con códigos de 4
  caracteres: `AODB`, `FIDS`, `GATE`, `RAMP`, `BILL`, `PASS`. El
  middleware resuelve el módulo de una petición tomando el primer
  segmento de `request.url.path` (`/billing/...` -> código `BILL`,
  `/rampa/...` -> `RAMP`, etc.) contra un diccionario estático
  `PREFIJO_A_CODIGO_MODULO` en `aerohub_gateway`. Rutas sin prefijo
  licenciable (`/tenants/*`, `/vuelos/*` de aprovisionamiento, `/metrics`)
  quedan exentas -- no tiene sentido exigir licencia para aprovisionar el
  tenant que la va a necesitar.
- **Racional**: no existe otro mecanismo de metadatos de router en el
  código fuente (los `APIRouter` de cada módulo no llevan un
  `modulo_id` adjunto) -- el prefijo de ruta es la única señal
  disponible sin rediseñar cada router existente, y ya es 1:1 con el
  módulo de negocio en los 6 módulos actuales.
- **Alternativas consideradas**: agregar un campo `modulo_codigo` a cada
  `APIRouter` -- rechazada, tocaría los 6 routers existentes (aodb,
  fids, gates, ramp, billing, passenger) para un sprint que no los tiene
  en su alcance de cambio; el diccionario estático logra lo mismo sin
  tocarlos.
- **AODB y aprovisionamiento de tenant quedan exentos**: `/tenants/*`
  (CU-O18, alta de tenant) no puede exigir una licencia que todavía no
  existe -- exento por diseño, no un descuido.

## Decisión 3: `post_mortem`/`post_mortem_accion` viven en `aerohub_compliance`, con mutabilidad controlada en `application/`, no en el motor

- **Decisión**: `aerohub_compliance.application.gestionar_post_mortem`
  valida `contexto_rol_actor() == "role_sre"` antes de cualquier
  INSERT/UPDATE sobre `post_mortem`/`post_mortem_accion` -- MonetDB no
  tiene RLS, así que la excepción de mutabilidad de ADR-009 se aplica en
  código de aplicación, mismo patrón que el mínimo privilegio de
  `role_ramp_agent` (S1.5).
- **Racional**: es exactamente el patrón ya establecido para
  restricciones por rol que la matriz de privilegios no puede expresar a
  nivel de motor.
- **Publicar exige remediación completa**: `emitir_post_mortem` (FR-005)
  consulta `post_mortem_accion` del post-mortem y rechaza si alguna fila
  tiene `estado != 'completada'` -- regla de dominio validada en
  `application/` (necesita consultar otras filas, domain/ puro no puede).

## Decisión 4: PN-04 reforzada se verifica por análisis estático, mismo criterio que PN-15

- **Decisión**: `incidente_seguridad`, `reporte_dgac`, `acceso_auditor`,
  `evidencia_soc2` reciben SOLO funciones `insertar_*` en
  `aerohub_compliance.infrastructure.comandos` -- nunca `actualizar_*` ni
  `eliminar_*`. La prueba que lo verifica (US3) recorre el módulo fuente
  y falla si aparece cualquier función de mutación fuera de la lista
  blanca (`post_mortem`/`post_mortem_accion`), mismo enfoque que
  `tests/negative/test_pn15_sql_fuera_del_repositorio.py` usa para PN-15.
- **Racional**: "ausencia de método expuesto" no se puede probar con una
  aserción de comportamiento (no hay nada que invocar para demostrar que
  no existe) -- análisis estático es la única forma correcta de
  verificarlo, coherente con cómo el propio SDD describe PN-04
  ("sin método de mutación expuesto por la capa de repositorio").

## Decisión 5: Rotación de API Key = nueva fila + fila anterior marcada, no UPDATE in place

- **Decisión**: `rotar_api_key` inserta una fila NUEVA en `tenants.
  api_key` (mismo mecanismo que `crear_api_key`) y actualiza la fila
  anterior con `estado='revocada'`, `rotada_en=ahora_utc()` -- nunca
  sobrescribe `hash_secreto` de la fila existente.
- **Racional**: P5 ("sin DELETE físico") y el propio hallazgo de RF-O12
  ("rotación sin interrupción del servicio") exigen que la key anterior
  siga siendo una fila auditable (con timestamp exacto de cuándo dejó de
  ser válida), no que desaparezca ni se sobrescriba -- mismo principio de
  denormalización deliberada / instantánea inmutable ya aplicado a
  `cargo_aeronautico` en S1.6, aplicado aquí a nivel de fila completa en
  vez de columna.
- **estado del `CHECK`**: `tenants.api_key.estado` ya solo admite
  `'activa'|'revocada'|'expirada'` (DDL de S0.2) -- la key rotada usa
  `'revocada'`, semánticamente correcta (fue invalidada, la razón exacta
  -- rotación vs. revocación manual -- queda en `log_auditoria`, no
  amerita un cuarto valor de `estado`).

## Stack técnico (sin alternativas nuevas -- hereda del proyecto)

- **Lenguaje/Runtime**: Python 3.12, FastAPI, SQLAlchemy Core.
- **Storage**: MonetDB -- `db/ddl/monetdb/13_compliance_hub.sql` nuevo
  (5 tablas: `tipo_incidente`, `incidente_seguridad`,
  `tipo_reporte_regulatorio`, `reporte_dgac`, `acceso_auditor`,
  `post_mortem`, `post_mortem_accion`, `control_soc2`, `evidencia_soc2`
  -- 9 tablas en total, `log_auditoria` ya existe).
- **Testing**: `pytest` unit (dominio: transición de estado de
  post-mortem, validación de remediación completa) + integration
  (PN-09 licenciamiento, ciclo de vida de post-mortem con rol correcto,
  PN-04 reforzada por análisis estático, rotación de API Key) vía
  `TestClient` contra MonetDB real en Docker.
