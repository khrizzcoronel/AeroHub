# Research: Tarifarios y conciliación de pax (S1.17)

## Decisión 1 — Ruta nueva como enlace manual del shell, no como segunda ruta de M5

**Decisión**: `billing/tarifarios` se expone en el menú lateral vía un
computed nuevo `puedeVerTarifarios` en `shell.ts`, con el mismo mecanismo
ya usado para `usuarios`/`api-keys`/`licencias`/`tenants` -- no a través
de `modulosConVista`.

**Razón**: `modulosConVista` (`shell.ts`) filtra `perfil().modulos_visibles`
por `m.ruta !== null`, y cada módulo del backend (`MODULOS` en
`roles_modulos.py`) tiene **una sola** `ruta`. M5 ya tiene la suya
ocupada por `/billing/facturas` desde S1.13. Cambiarla o duplicarla
rompería el contrato de un módulo → una ruta que S1.16 estableció
explícitamente (research.md Decisión 6 de esa spec). El precedente ya
existe: `usuarios`, `api-keys`, `licencias` y `tenants` tampoco son
módulos M1-M9 y se muestran con un `computed` propio basado en scope/rol
directamente, sin pasar por `modulos_visibles`.

**Alternativas consideradas**: agregar un segundo campo `ruta_secundaria`
al modelo de módulo -- rechazado, cambia un contrato compartido por
`packages/contracts` para resolver un caso que el patrón ya existente
resuelve sin tocar nada del backend.

## Decisión 2 — Corrección de 2 suposiciones erróneas del spec inicial (Principio III)

**Hallazgo**: al leer `services/billing/aerohub_billing/application/conciliar_pax.py`
y `domain/conciliacion_pax.py` antes de implementar, dos suposiciones del
`spec.md` inicial resultaron incorrectas y se corrigieron ahí mismo antes
de proceder:

1. `conciliar()` **exige** que la diferencia sea cero (`puede_conciliar`
   devuelve `False` y se lanza `DiferenciaNoNula` si no lo es) -- lo
   opuesto de lo que decía el borrador original ("marcar como conciliada
   una conciliación con diferencia distinta de cero"). Es una compuerta
   de pruebas deliberada de S1.6 (comentario explícito en el dominio:
   "no existe forma de forzar una conciliación con diferencia distinta
   de cero").
2. `registrar_conciliacion()` recibe `pax_registrado_sistema` como
   parámetro de entrada -- el sistema NO lo calcula automáticamente a
   partir de otra tabla. El formulario de alta debe pedir ambos conteos
   (aerolínea y sistema), no solo el de aerolínea.

**Razón para documentarlo aquí**: mismo patrón que el hallazgo de
`JOIN`/`GROUP BY` de S1.16 -- verificar contra el código real antes de
construir sobre una suposición, y dejar constancia para que un sprint
futuro no repita el mismo error de lectura.

## Decisión 3 — `activar_tarifario` no valida que el tarifario tenga conceptos

**Decisión**: el aviso de "esto no altera cargos históricos" en la
pantalla de confirmación de activación es puramente informativo -- no se
agrega ninguna validación de "al menos un concepto" en el frontend, y no
se bloquea la activación de un tarifario sin conceptos.

**Razón**: `activar_tarifario` (`gestionar_tarifario.py`) solo valida
"a lo sumo un vigente por (tenant, moneda)" -- nunca revisa
`tarifario_concepto`. Agregar esa validación en el frontend sin que el
backend la aplique crearía una regla de negocio duplicada e inconsistente
(la misma acción sería posible vía API pero bloqueada solo en la UI).
Si el backend nunca la exigió, este sprint (cierre de superficie, no
cambio de reglas de negocio) no es el lugar para introducirla.

## Decisión 4 — Listados nuevos: reutilizar el mismo query builder que ya filtra por tenant

**Decisión**: `listar_tarifarios(conn)` (todos los estados, no solo
vigente) y `listar_conciliaciones(conn)` se agregan a
`infrastructure/consultas.py` siguiendo el mismo `select(tabla).where(tabla.c.tenant_id == contexto_tenant_id())`
que ya usan `listar_tarifarios_vigentes`/`obtener_conciliacion_por_id`.
`listar_conceptos_de_tarifario` (S1.6) ya existe y se reutiliza tal cual
para poblar los conceptos de cada tarifario en el listado -- sin query
nueva para eso. `listar_conceptos_cargo` (catálogo, sin filtro de
tenant, ya expuesto) se reutiliza tal cual para el `<select>` de alta de
concepto.

**Razón**: ningún patrón nuevo -- exactamente la misma forma que S1.15 y
S1.16 usaron para sus respectivos listados nuevos.

## Decisión 5 — Endpoint de listado de conciliaciones agrupa por vuelo+período, sin filtro adicional

**Decisión**: `GET /billing/conciliaciones` devuelve todas las
conciliaciones del tenant, sin paginar en el backend (mismo criterio que
`GET /fids/plantillas`/`GET /fids/pantallas` de S1.16 -- la paginación,
si hace falta, se resuelve client-side sobre la lista ya cargada, igual
que `tenant-list`).

**Razón**: no hay ningún Acceptance Scenario que pida filtrar por
vuelo/aerolínea en el listado -- mantenerlo simple hasta que el volumen
real lo justifique (mismo razonamiento que S1.16 Decisión 4 sobre
`ops.terminal`).
