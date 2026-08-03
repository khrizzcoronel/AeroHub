# Research: Vistas administrativas + consolidación (S1.13)

## Decisión 1 — Semáforo de estado de factura: 5 valores reales, mapeo completo

**Decisión**: `borrador` → neutro; `emitida` → `atencion` (pendiente de
pago, requiere seguimiento); `pagada` → `ok`; `vencida` → `critico`;
`disputada` → `critico`.

**Razón**: `chk_factura_estado` (`db/ddl/monetdb/12_billing.sql`) fija
exactamente estos 5 valores — mapeo exhaustivo, sin caso ambiguo.
`emitida` se marca `atencion` (no neutro) porque es el estado que
requiere que alguien la cobre — comunicar "sin urgencia" ahí sería
engañoso; `vencida` y `disputada` comparten rojo porque ambas son
excepciones que requieren intervención humana, coherente con el mismo
criterio de 4 niveles ya usado en S1.11/S1.12 (no se introduce un quinto
tono).

**Alternativas consideradas**: mapear solo por si está pagada o no (2
niveles) — rechazado, pierde la distinción operativa entre "por cobrar
normal" (emitida) y "por cobrar con problema" (vencida/disputada), que
es justamente la que el color debe comunicar de un vistazo (spec.md
SC-001).

## Decisión 2 — La tira de factura usa `.ah-tira`, igual criterio que las otras 3 vistas de negocio

**Decisión**: cada factura en la lista se presenta como `.ah-tira` (id,
aerolínea, período, monto en mono; barra con el color de Decisión 1),
igual que vuelos/puertas/rampa.

**Razón**: `DIRECCION_VISUAL.md` §2.4 ya define "M5 Billing: una tira =
una factura, la barra marca estado de conciliación" — este sprint solo
ejecuta esa fila de la tabla ya aprobada, no decide nada nuevo. Las
líneas de cargo del detalle van en `.ah-tabla` (son el contenido, no la
unidad estructural), mismo criterio que las tareas de un turnaround en
S1.12 (research.md S1.12, Decisión 4).

**Alternativas consideradas**: ninguna — decisión ya tomada en
S1.11, este sprint la ejecuta.

## Decisión 3 — El formulario de tenant no introduce ningún primitivo nuevo

**Decisión**: `tenants/tenant-creation` se resuelve enteramente con
`.ah-campo`/`.ah-btn`/`.ah-alerta`/`.ah-vacio` ya existentes, envuelto en
un contenedor simple (mismo criterio de `.stage-simple`/`.card` de las
vistas de auth para un formulario aislado, sin tabla ni tira).

**Razón**: es un formulario de alta frecuencia baja (crear un tenant es
una operación excepcional), sin necesidad de un componente "tira" (no
hay una lista de tenants que recorrer en esta vista) — forzar `.ah-tira`
aquí sería aplicar el patrón equivocado a un caso que no lo pide.

**El resultado de creación** (tenant_id, usuario_admin_id,
password_temporal) se presenta como una lista de pares clave-valor
dentro de un `.ah-alerta--aviso`, no una lista HTML plana — para que
resalte como la información crítica de un solo uso que es (la
contraseña temporal no se vuelve a mostrar).

**Alternativas consideradas**: reusar `.ah-tabla` para el resultado —
rechazado, una tabla implica múltiples filas comparables, y este es un
resultado singular de pares clave-valor; una lista de definición dentro
del aviso es más directa.

## Decisión 4 — La auditoría de las 8 vistas de S1.10 es de verificación, no de reconstrucción

**Decisión**: cada una de las 8 vistas (login, cambiar-password,
recuperar, restablecer, verificar-correo, aceptar-invitacion, invitar,
shell) se revisa contra los tokens/primitivos vigentes; se corrige en el
momento cualquier inconsistencia menor (un color hardcodeado en vez de
un token, un espaciado que no seguía la escala de 4px); una
inconsistencia mayor (que implicaría rediseñar la vista completa) se
documenta como hallazgo, no se resuelve aquí.

**Razón**: es exactamente el alcance que spec.md US3/Assumptions fija —
estas 8 vistas YA tienen identidad visual propia desde S1.10 (antes de
que S1.11 formalizara el sistema completo); es esperable que haya
pequeños desajustes (p. ej. `_auth-form.scss` ya se consolidó sobre los
primitivos en S1.11, pero las vistas individuales podrían tener un color
o medida propia que no se tocó en esa consolidación).

**Verificación concreta realizada** (documentada aquí, no repetida en
tasks.md): grep de las 6 plantillas de auth confirmó que todas usan
`class="card"`/`class="stage-simple"` consistentemente (ninguna quedó
con HTML suelto fuera del patrón); el shell usa sus propias clases
(`side`, `content`) que ya son consistentes con los tokens navy/paper
desde S1.10.

**Alternativas consideradas**: rediseñar las 8 vistas desde cero con
`.ah-*` — rechazado explícitamente por spec.md Assumptions, sería
trabajo no pedido y fuera de la división de sprints ya acordada.
