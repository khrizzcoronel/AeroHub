# Research: Informes operativos (S1.18)

## Decisión 1 — Un componente Angular compartido, no 6

**Decisión**: `apps/web/src/app/informes/panel-informe/` es el único
componente de presentación de informes -- recibe su configuración
(título, columnas, endpoint del backend, filtros disponibles) como
`@Input()`, y cada módulo lo instancia en su propia ruta con su propia
config.

**Razón**: los 6 informes comparten EXACTAMENTE la misma forma de
respuesta (`parametros`/`generado_en`/`filas`/`grupos[].subtotal`/`total`)
por diseño del plan (regla 3 de §8-bis.0) -- construir 6 componentes
sería duplicar el mismo HTML/TS con distinto texto. Rompe el patrón "una
vista por módulo" de S1.15-S1.17 deliberadamente: ese patrón aplicaba a
vistas con interacciones y datos distintos (formularios de alta,
acciones de fila); un informe es de solo lectura y su única variación
real es de qué endpoint lee y qué columnas muestra.

**Alternativas consideradas**: 6 componentes por módulo (mismo patrón
que el resto de `apps/web`) -- rechazado, duplicaría ~200 líneas de
TS/HTML 6 veces; un componente completamente genérico sin config
tipada (`any`) -- rechazado, pierde el chequeo de tipos de TS sin
necesidad, la config tipada por módulo no cuesta más que un objeto
literal.

## Decisión 2 — Forma de respuesta común (RF-I03) sin contrato compartido en `packages/`

**Decisión**: cada módulo define su propio Pydantic response model con
la misma FORMA (`parametros: dict`, `generado_en: str`, `filas: list`,
y para compuestos `grupos: list[{clave, subtotal, filas?}]` + `total`),
pero como una clase Pydantic propia de cada `api/router.py` -- no se
crea un tipo compartido en `packages/contracts`.

**Razón**: `packages/contracts` hoy solo contiene el mapeo rol→módulo/
scope (dato de configuración, no un contrato de API) -- introducir un
tipo de respuesta HTTP compartido ahí mezclaría dos responsabilidades
distintas. Repetir la forma (no el código) en 6 Pydantic models
pequeños es más barato que la alternativa y no viola ADR-017 (los
módulos siguen sin importarse entre sí). El frontend sí comparte un
único `interface InformeCompuesto<TFila>` en `informe.service.ts`
porque ahí no hay problema de independencia de módulos de negocio.

**Alternativas consideradas**: paquete nuevo `packages/informes` con el
contrato Pydantic compartido -- rechazado, sobre-ingeniería para 6
formas idénticas que ya se pueden expresar como Pydantic models locales
sin ningún acoplamiento real entre módulos.

## Decisión 3 — CSV se construye en el endpoint, reutilizando la misma consulta que el JSON

**Decisión**: cada endpoint de informe acepta `?formato=csv|json`
(default `json`); cuando es `csv`, arma el CSV en memoria (`io.StringIO`
+ `csv.writer`) a partir del MISMO objeto de respuesta ya calculado --
nunca una consulta separada.

**Razón**: regla 4 de §8-bis.0, textual -- "nunca un endpoint paralelo
que pueda divergir de lo mostrado". Construir el CSV desde el objeto ya
armado (no desde una query nueva) hace estructuralmente imposible que
diverja.

## Decisión 4 — RF-I04 (auditoría) solo en M5 (facturación) y M9 (DGAC)

**Decisión**: únicamente `application/informes.py` de `aerohub_billing`
(informe compuesto de facturación) y `aerohub_compliance` (informe
compuesto de DGAC) llaman a `registrar_auditoria(...)` al emitir el
informe. Los otros 4 módulos no escriben auditoría por esta causa.

**Razón**: spec.md Assumptions -- "validez externa" se acota
explícitamente a esos 2 en este sprint; agregar auditoría a los otros 4
sin que el plan lo pida sería alcance no solicitado.

## Decisión 5 — Informe compuesto de M9 generaliza `reporte_dgac`, no lo reemplaza

**Decisión**: el informe compuesto de M9 (emisión de `reporte_dgac`)
lee la tabla `compliance.reporte_dgac` ya existente desde antes de este
sprint (S1.7) y la agrupa por `tipo_reporte_id`, con subtotal de
reportes emitidos por tipo y total general -- no se toca el mecanismo
de emisión real del reporte (fuera de alcance, spec.md Assumptions:
"cero cambios a la lógica de negocio").

**Razón**: el plan pide explícitamente "generalizando el caso especial
ya existente en backend" -- el caso especial (emisión real) sigue
intacto, el informe es una vista agregada nueva sobre datos que ya se
producían.

## Decisión 6 — Dimensión de agrupación de cada informe compuesto

| Módulo | Entidad simple | Agrupación del compuesto | Métrica agregada |
|---|---|---|---|
| M1 AODB | `ops.vuelo` + último `vuelo_estado` | `aerolinea_id` | conteo de vuelos, % con `ata_utc <= sta_utc + tolerancia` (puntualidad) |
| M3 Gates | `ops.asignacion_puerta` | `puerta_id` | conteo de asignaciones, % de solapamiento (conflicto) sobre el período |
| M4 Ground Ops | `rampa.tarea_turnaround` | `tipo_tarea_id` | conteo de tareas, desviación media (`fin_real - inicio_real` vs `duracion_estandar_min`), conteo de incidencias por severidad |
| M5 Billing | `billing.factura_linea` (vía `factura`) | `concepto_cargo_id` (a través de `cargo_aeronautico`) | suma de `monto` |
| Tenancy | `tenants.tenant` | `(plan_id, estado)` | conteo de tenants, conteo de usuarios activos, conteo de licencias vigentes |
| M9 Compliance | `compliance.reporte_dgac` | `tipo_reporte_id` | conteo de reportes emitidos en el período |

**Razón**: cada dimensión ya es la que el propio módulo usa en sus
vistas/tests existentes (p. ej. `aerolinea_id` en `billing`/`aodb`,
`estado` en `gates`/`ramp`) -- no se inventa una dimensión nueva sin
precedente en el módulo.

**Hallazgo empírico de MonetDB (post-verificación, Principio III)**: todo
`GROUP BY` de este sprint debe agrupar sobre un **alias de tabla**
(`tabla.alias("v")`), no sobre `tabla.c.columna` directamente -- MonetDB
rechaza el `GROUP BY` cuando SQLAlchemy compila la columna en su forma
completa `esquema.tabla.columna` (3 partes), incluso para la consulta
más simple posible, con `42000!SELECT: cannot use non GROUP BY column
... without an aggregate function`. Con un alias, SQLAlchemy compila
`v.columna` (2 partes) y MonetDB lo acepta. Verificado reproduciendo el
error con SQL directo antes de aplicar el fix. Documentado también en
`CLAUDE.md`.
