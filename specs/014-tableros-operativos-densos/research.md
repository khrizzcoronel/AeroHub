# Research: Tableros operativos densos (S1.12)

## Decisión 1 — "Conflicto" de una puerta se calcula en el frontend por solapamiento de intervalos

**Decisión**: una puerta se clasifica como `critico` (conflicto) si tiene
2 o más asignaciones cuyos intervalos `[inicio_previsto, fin_previsto)`
se solapan; `ok` si tiene exactamente una asignación vigente sin
solapamiento; `neutro` si no tiene ninguna asignación.

**Razón**: `TableroResponse` ya trae todas las asignaciones de todas las
puertas en una sola respuesta (`puertas.service.ts`) — el frontend ya
tiene todo lo necesario para detectar el solapamiento sin pedir nada
nuevo al backend. El algoritmo es el clásico de intervalos: ordenar por
`inicio_previsto` y comparar cada par consecutivo (`fin_previsto` del
anterior > `inicio_previsto` del siguiente ⇒ se solapan). Es una función
de PRESENTACIÓN pura (mismo criterio que `claseDeEstado` en
`estado-tiempo-real.ts`, S1.11) — no repite ninguna regla de negocio del
backend, que ya rechaza conflictos reales al asignar (PN-05); esto solo
hace visible en el tablero una condición que, si aparece, generalmente
es transitoria (una asignación cancelada que aún no se depuró, o datos
de prueba) y merece atención visual inmediata.

**Alternativas consideradas**: (a) pedirle al backend un endpoint nuevo
que devuelva el estado de conflicto ya calculado — rechazado, es
presentación pura y el spec (Assumptions) exige no tocar el backend en
este sprint; (b) marcar conflicto solo si el `estado` de alguna
asignación es explícitamente un valor de error — rechazado, no existe tal
valor en el catálogo (`planificada`/`activa`/`finalizada`/`cancelada`,
`10_ops.sql`); el solapamiento temporal es la señal real y disponible.

## Decisión 2 — "Desviación" de un turnaround se aproxima con su `estado`, igual criterio que S1.11

**Decisión**: mapeo directo de `Turnaround.estado` a semáforo:
`completado` → `ok`; `en_curso` → `ok` (transcurriendo con normalidad,
por defecto); `interrumpido` → `critico`; `planificado` → `neutro`.

**Razón**: el frontend no recibe hoy ninguna señal más fina (comparación
de tiempos reales vs. previstos con precisión de minutos) — el
`Turnaround` que expone `rampa.service.ts` solo trae
`inicio_previsto`/`fin_previsto` (el plan, no lo real) y `estado`. Una
comparación de "ahora > fin_previsto y estado != completado" SÍ es
calculable con lo disponible y se incluye como refinamiento (ver
implementación), pero la base del semáforo es el `estado` explícito —
mismo criterio ya usado para `codigo_estado` de vuelo en S1.11
(mapeo de presentación, sin lógica de negocio nueva).

**Refinamiento incluido** (calculable con datos ya presentes, sin pedir
nada nuevo): un turnaround `en_curso` cuyo `fin_previsto` ya pasó se
reclasifica a `atencion` (ámbar) — es la aproximación más simple y
honesta a "se está pasando de lo previsto" que los datos actuales
permiten, sin inventar un campo que el backend no expone.

**Alternativas consideradas**: pedir al backend tiempos reales de cada
hito (calzos, puertas, catering) para una "carta de hitos" literal —
explícitamente fuera de alcance (spec.md Assumptions): esa granularidad
pertenece a una capacidad de M4 que hoy no existe, y construirla sería
agregar funcionalidad, no redizañar una vista existente.

## Decisión 3 — Severidad de incidencia mapea directo a semáforo, sin ambigüedad

**Decisión**: `baja` → `neutro`; `media` → `atencion`; `alta`/`critica` →
`critico`.

**Razón**: `db/ddl/monetdb/11_rampa.sql` fija exactamente 4 valores
posibles (`chk_incidencia_rampa_severidad`) — el mapeo es exhaustivo y
no requiere un caso por defecto ambiguo. `alta` y `critica` comparten
color porque el semáforo del sistema (S1.11) solo define 4 niveles, no
5 — separarlas en visual distinto exigiría un quinto tono que
`DIRECCION_VISUAL.md` no contempla; ambas ya comunican urgencia con el
mismo rojo, la palabra `severidad` en la tabla sigue mostrando el texto
exacto para quien necesite la distinción fina.

**Alternativas consideradas**: un quinto tono para `critica` —
rechazado, fuera del sistema de 4 colores ya cerrado en S1.11; introducir
una escala nueva rompería la coherencia visual que este mismo sprint
busca reforzar.

## Decisión 4 — Las tareas del turnaround usan `.ah-tabla`, no `.ah-tira`

**Decisión**: dentro del detalle de un turnaround seleccionado, las
tareas se listan como filas de `.ah-tabla` (con la columna `estado`
resaltada por color), no como tiras individuales.

**Razón**: la unidad "tira" de esta vista es el turnaround (una tira =
un ciclo de tierra completo, coherente con la tabla de
`DIRECCION_VISUAL.md` §2.4: "M4 Ground Ops: una tira = un turnaround").
Las tareas son el detalle DENTRO de esa unidad, no una unidad
estructural propia — tratarlas como tiras produciría dos niveles de
"tira" en la misma pantalla y confundiría la jerarquía visual que el
sistema busca (una tira = un recurso/evento de primer nivel).

**Alternativas consideradas**: tratar cada tarea como una mini-tira —
rechazado por la razón anterior; mantenerlas como `<table>` sin estilo —
rechazado, rompería la coherencia visual exigida por FR-011/SC-005.
