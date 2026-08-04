# Research: Compliance Hub (S1.19)

## Decisión 1 — Hallazgo crítico: `role_sre` no tiene ningún scope `compliance:*`

**Decisión**: agregar `M9` a los módulos de `role_sre` y
`compliance:leer`/`compliance:escribir` a sus scopes en
`packages/contracts/aerohub_contracts/roles_modulos.py`.

**Razón**: `_exigir_role_sre()` (`gestionar_post_mortem.py`, S1.7) exige
exactamente `role_sre` para crear/editar/publicar post-mortems y agregar
acciones -- pero `role_sre` hoy solo tiene `{M7, M8}` y
`{support:leer, support:escribir}`. El `Depends(requiere_scope(
"compliance:escribir"))` del endpoint rechaza la petición con 403 ANTES
de que la aplicación llegue a evaluar `_exigir_role_sre()` -- los
endpoints de post-mortem son inalcanzables por el único rol que el
dominio autoriza, exactamente el mismo patrón que el hallazgo de FIDS en
S1.16. `role_tenant_admin` sí tiene `compliance:escribir`, pero sería
rechazado por `RolNoAutorizado` al intentar post-mortems (el dominio
exige el rol exacto) -- puede sí crear incidentes, reportes DGAC,
accesos de auditor y evidencia SOC2 (esos no exigen `role_sre`).

**Alternativas consideradas**: relajar `_exigir_role_sre()` para aceptar
también `role_tenant_admin` -- rechazado, cambiaría una decisión de
dominio de S1.7 (ADR-009) fuera del alcance de un sprint de cierre de
superficie.

## Decisión 2 — 4 listados nuevos + 3 catálogos, mismo patrón que S1.15-S1.18

**Decisión**: `listar_post_mortems`, `listar_reportes_dgac`,
`listar_accesos_auditor`, `listar_evidencia_soc2` en
`infrastructure/consultas.py` (mismo filtro `tenant_id ==
contexto_tenant_id()` que las consultas ya existentes); catálogos de
solo lectura `listar_tipos_incidente`, `listar_tipos_reporte_regulatorio`,
`listar_controles_soc2` en `infrastructure/consultas_catalogo.py`
nuevo -- ya existen `insertar_tipo_incidente`/etc. en `comandos.py`
(sembrados, sin endpoint de alta -- mismo patrón que
`concepto_cargo`/`tipo_tarea` de otros módulos).

**Razón**: sin estos, el formulario de alta de incidente/reporte/
evidencia obligaría a pegar ids Snowflake a mano, y los 4 listados son
prerequisito directo de FR-002/FR-007/FR-009/FR-011.

## Decisión 3 — Una vista con 5 secciones, no 5 rutas

**Decisión**: `compliance/panel-compliance` es la única ruta nueva de
M9, con 5 secciones apiladas (incidentes, post-mortems, reportes DGAC,
accesos de auditor, evidencia SOC2).

**Razón**: mismo razonamiento que S1.16 (Decisión 6) y S1.18 -- M9 es
un solo módulo con una sola ruta en `modulosConVista`, y las 5
entidades están fuertemente relacionadas conceptualmente (todas viven
bajo "cumplimiento").

## Decisión 4 — Evidencia SOC2 es de solo lectura para todos los roles en este sprint

**Decisión**: aunque `registrar_evidencia_soc2` existe desde S1.7, el
formulario de alta de evidencia se muestra solo si el rol activo tiene
`compliance:escribir` (mismo criterio de visibilidad condicional que el
resto de `apps/web`) -- no se introduce ninguna regla de autorización
nueva en el backend, solo se refleja en la UI la que ya existe.

**Razón**: `role_regulatory_auditor` solo tiene `compliance:leer` -- la
interfaz debe reflejar fielmente esa realidad (spec.md US3: "el auditor
solo puede leer, nunca escribir").
