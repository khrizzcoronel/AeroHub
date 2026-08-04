# Research: Administración de FIDS (S1.16)

## Decisión 1 — Hallazgo crítico: ningún rol tiene los scopes `fids:*` en absoluto

**Decisión**: agregar `fids:leer` y `fids:administrar` a los scopes de
`role_tenant_admin` en `packages/contracts/aerohub_contracts/roles_modulos.py`.

**Razón**: verificado por lectura directa — `role_tenant_admin` ya tiene
`M2` en su conjunto de módulos (`frozenset(MODULOS) - {"M7", "M8"}`), pero
su lista de scopes **no incluye ningún `fids:*`**. Una búsqueda completa
del repo confirma que **ningún rol, en ningún lugar**, tiene `fids:leer`,
`fids:administrar` ni `fids:heartbeat` — los 3 endpoints de escritura de
S1.3 son literalmente inalcanzables por cualquier sesión humana desde que
se construyeron. `apps/fids-player` nunca lo necesitó porque no autentica
como un rol humano — pega un JWT a mano (documentado en S1.14: "no hay
login real todavia... el token JWT se pega a mano", mecanismo real de
configuración de una pantalla física, no deuda técnica). Sin este cambio,
la vista de este sprint quedaría construida pero devolviendo 403 a
cualquiera que la abra — el mismo tipo de hallazgo que motivó la
corrección del scope de aeropuertos en S1.15.

**Alternativas consideradas**: crear un rol nuevo dedicado a FIDS —
rechazado, fuera de alcance (cambiar el catálogo de roles es una decisión
de RBAC mayor, no de superficie); dejarlo para un sprint de "arreglar
permisos" separado — rechazado, sin esto FR-008 de `spec.md` no se puede
cumplir en absoluto.

## Decisión 2 — `GET /fids/plantillas` devuelve solo la última versión por nombre

**Decisión**: el listado de plantillas agrupa por `nombre` y devuelve
únicamente la fila de `version` más alta de cada una.

**Razón**: `publicar_plantilla` (S1.3) nunca actualiza una fila — cada
publicación es un INSERT inmutable con `version` autoincremental por
`nombre` (una pantalla que apunta a una versión antigua sigue siendo
resoluble, decisión ya tomada). Sin esta agrupación, publicar "Llegadas"
tres veces mostraría 3 filas casi idénticas en la tabla y en el `<select>`
de asignación de pantalla, y la persona no tendría forma de saber cuál es
la vigente. Listar solo la última versión no pierde nada: el historial
completo sigue en la tabla, la UI solo expone lo publicable de nuevo.

**Corrección post-verificación empírica (Principio III)**: la primera
implementación construyó esto como `JOIN` contra una subconsulta con
`GROUP BY nombre, max(version)` — patrón SQL estándar, pero MonetDB real
lo rechazó: `42000!SELECT: cannot use non GROUP BY column
'plantilla_fids.nombre' in query results without an aggregate function`,
a pesar de que el `GROUP BY` vive enteramente dentro de la subconsulta.
Verificado con `tests/integration/test_fids_administracion.py` contra
MonetDB real en Docker. Se reescribió como un anti-join (`NOT EXISTS`
correlacionado contra un alias de la misma tabla, sin subconsulta
agregada) — funciona en MonetDB y es además más portable entre motores.
Documentado aquí para no volver a tropezar con el mismo patrón en un
sprint futuro que necesite "última fila por grupo".

**Alternativas consideradas**: listar todas las versiones con la vigente
marcada — rechazado, agrega una columna/estado nuevo (¿"vigente"
respecto a qué? una plantilla no tiene un `vigente_hasta`, "vigente" es
un concepto de la pantalla, no de la plantilla) sin necesidad real para
este sprint.

## Decisión 3 — `GET /fids/pantallas` es el tablero de telemetría, sin cálculo nuevo

**Decisión**: el listado expone directamente `estado` y `ultima_senal_en`
tal como ya los mantiene el backend (`registrar_heartbeat` los actualiza
en cada latido, `marcar_pantalla_sin_senal` los corrige el monitor de
señal de RNF-R04) — sin duplicar esa lógica en la consulta ni en el
frontend.

**Razón**: `spec.md` describe esto como "el tablero de telemetría que
pide el plan" — y ya existe como dato, solo le faltaba una consulta de
listado y una tabla que lo muestre. Semáforo de presentación (mapeo
puro, sin lógica de negocio): `en_linea` → `.ah-pill--ok`, `sin_senal` →
`.ah-pill--critico`, `mantenimiento` → neutro — mismo criterio de 3-4
tonos que el resto del sistema.

**Alternativas consideradas**: recalcular "sin señal" en el frontend
comparando `ultima_senal_en` contra la hora actual (como hace
`apps/fids-player` del lado del reproductor) — rechazado, esta vista es
administrativa, no el reproductor; el campo `estado` que el backend ya
mantiene es la fuente de verdad correcta para un panel de gestión.

## Decisión 4 — Catálogo de terminales: tenant-scoped, a diferencia de aeropuertos

**Decisión**: `ops.terminal` se redeclara en `aerohub_fids/infrastructure/`
como solo lectura, **filtrada por `contexto_tenant_id()`** (no como
`alcance_global()`).

**Razón**: a diferencia de `catalogo.aeropuerto`/`aerolinea`/`aeronave`/
`tipo_vuelo` (S1.15, tablas verdaderamente globales sin `tenant_id`),
`ops.terminal` SÍ tiene `tenant_id` (`db/ddl/monetdb/10_ops.sql`) — cada
tenant tiene sus propias terminales. Filtrar por tenant es el
comportamiento correcto y consistente con el resto de `ops.*`, no una
elección nueva.

**Riesgo de datos conocido**: `ops.terminal` nunca se sembró formalmente
en `db/seeds/generate.py` — los datos que existen hoy en desarrollo son
artefactos de una suite de pruebas anterior (`tests/integration/
test_pn05_asignacion_puertas.py`, terminales con códigos como
`PN05-...`). Este sprint expone el catálogo tal cual está; poblarlo
formalmente queda fuera de alcance (`spec.md` Assumptions) — es un gap
de seeds, no de este sprint.

## Decisión 5 — El código de pantalla se presenta en un aviso copiable tras el alta

**Decisión**: al registrar una pantalla, el modal de éxito muestra el
`codigo` (el que la persona escribió, no un id generado) dentro de un
`.ah-alerta--aviso` con estilo de dato copiable — mismo patrón que
`tenant-creation` mostró la contraseña temporal en S1.10/S1.13.

**Razón**: `spec.md` FR-006 exige que el código quede "visible y fácil de
copiar" porque es el dato que se transcribe a mano al dispositivo físico
— perderlo entre el resto del formulario sería repetir el error que
`tenant-creation` ya corrigió.

## Decisión 6 — Una sola vista con dos tablas, no dos rutas

**Decisión**: `fids/pantalla-list` es la única ruta nueva, con la tabla
de plantillas arriba y la de pantallas abajo, cada una con su propio
panel de búsqueda, paginación y modal de alta — mismo componente para
ambas secciones, reutilizando el mismo patrón dos veces dentro de un
componente.

**Razón**: el mapeo `modulosConVista` del shell asigna **una** ruta por
módulo (`modulo.ruta`), y M2 es un solo módulo — no hay un segundo lugar
en el menú donde poner "Plantillas" por separado de "Pantallas". Además
están fuertemente acopladas: no tiene sentido gestionar plantillas sin
poder ver a qué pantallas están asignadas, ni viceversa.

**Alternativas consideradas**: dos rutas con navegación interna (tabs) —
rechazado por complejidad innecesaria; ambas tablas caben en una sola
vista con scroll, mismo criterio que ya usa `puertas/tablero-puertas`
(tabla de puertas + modal de asignación, todo en una vista).
