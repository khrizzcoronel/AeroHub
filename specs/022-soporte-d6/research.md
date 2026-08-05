# Research: Soporte D6

## Decisión 1 — Confirmación de scopes de tickets/KB, HALLAZGO real en changelog

**Decisión**: se agregan `support:leer`/`support:escribir` a
`role_platform_admin` en
`packages/contracts/aerohub_contracts/roles_modulos.py`. Los demás
roles (`role_sre`, `role_support`, `role_tenant_admin`) no se tocan.

**Rationale**: se leyó el mapeo real antes de implementar (regla de
verificación empírica, no asumir), y también el código de dominio de
cada caso de uso, no solo el router HTTP. Para tickets y KB, los 3
roles esperados ya alcanzan lo que necesitan:

| Rol | `support:leer` | `support:escribir` |
|---|---|---|
| `role_sre` | sí | sí |
| `role_support` | sí | sí |
| `role_tenant_admin` | sí | sí |

Pero `services/support/aerohub_support/application/gestionar_changelog.py`
(`_ROL_AUTORIZADO = "role_platform_admin"`, línea 27) exige
exactamente `role_platform_admin` para `publicar_changelog()` -- y ese
rol **no tenía ningún scope `support:*`**
(`packages/contracts/aerohub_contracts/roles_modulos.py`, antes de
este sprint). Como `api/router.py` exige `support:escribir` en la capa
HTTP *antes* de llegar al dominio, `POST /support/changelog` era
inalcanzable por **cualquier** rol del sistema desde que se construyó
en S1.8 -- mismo patrón exacto que el hallazgo de `fids:*` (S1.16) y
`compliance:*` en `role_sre` (S1.19). Se agrega `support:leer` junto
con `support:escribir` (no solo el segundo) para que quien publica una
entrada también pueda ver el listado resultante, igual criterio que el
resto de los pares leer/escribir del proyecto.

**Alternatives considered**: cambiar `_ROL_AUTORIZADO` en el dominio a
otro rol que ya tuviera `support:escribir` (p. ej. `role_support`).
Rechazado -- el changelog es contenido de plataforma sobre el catálogo
`M1-M9`, coherente con la autoridad de `role_platform_admin` (mismo
tipo de alcance que `tenants:administrar`), y cambiar la regla de
dominio sin necesidad real contradice el criterio ya usado en S1.16/
S1.19 de corregir el scope faltante, no la regla de negocio existente.

## Decisión 1-bis — `role_platform_admin` no tiene tenant: bandeja de tickets oculta para ese rol

**Decisión**: la sección "Tickets" del panel se oculta para
`role_platform_admin` (verificado por `rol_codigo` en el frontend);
las secciones "Base de conocimientos" y "Changelog" sí se muestran.

**Rationale**: `consultar_tickets()`/`crear_ticket()` para cualquier
rol que no sea `role_support` llaman a `listar_tickets_de_tenant()`,
que filtra por `contexto_tenant_id()` (`infrastructure/consultas.py`
línea 49). `role_platform_admin` tiene `tenant_id` NULL (mismo hallazgo
ya documentado en S1.11 para `/usuarios`/`/api-keys`) -- llamar a esos
endpoints con ese rol lanza `ContextoTenantAusente` sin capturar, 500.
`buscar_articulos`/`consultar_changelog` no tienen ese problema: KB y
changelog son alcance `'global'`, sin filtro de tenant en ningún
camino de código, se leen igual sin importar el tenant del actor.

**Alternatives considered**: excluir a `role_platform_admin` de
`puedeVerSoporte()` por completo. Rechazado -- le impediría publicar
changelog, que es exactamente el hallazgo que este sprint corrige;
ocultar solo la sección que realmente le produce un error (mismo
patrón granular ya usado en S1.19 para `role_support`/M9 en
`modulosConVista`, research.md de aquel sprint) preserva el resto de
la superficie.

## Decisión 1-ter — Cambio de estado de ticket: exclusivo de `role_support`

**Decisión**: los botones de cambio de estado en el detalle del ticket
se ocultan para cualquier rol que no sea `role_support` (verificado
por `rol_codigo`, igual criterio que la nota interna).

**Rationale**: descubierto al correr el test de integración de este
sprint contra MonetDB real (no en la lectura previa del código, un
recordatorio de por qué la verificación empírica es obligatoria):
`cambiar_estado_ticket()` (`gestionar_tickets.py`, línea 343-344)
lanza `RolNoAutorizado` para cualquier rol que no sea `role_support`,
aunque tenga `support:escribir` -- `role_tenant_admin` y `role_sre`
pueden crear tickets y responder, pero no mover la máquina de estados.
Coherente con el resto del módulo: `role_support` es quien opera el
ciclo de vida completo del ticket (mismo patrón que la restricción de
mensajes internos).

**Alternatives considered**: mostrar los botones a cualquiera con
`support:escribir` y dejar que el backend rechace con 403. Rechazado
-- mismo criterio ya aplicado a la nota interna y a la publicación de
KB/changelog: la UI no debe ofrecer una acción que el backend nunca
va a aceptar para ese rol.

## Decisión 2 — Ruta de la vista: enlace manual, no `modulosConVista`

**Decisión**: la vista se expone como enlace condicional en el shell
(`puedeVerSoporte()`, por scope `support:leer`), igual que
`puedeVerTarifarios`/`puedeVerInformes*` en sprints anteriores.

**Rationale**: `MODULOS` en `roles_modulos.py` cubre M1-M9; D6 (soporte)
no es un módulo de negocio licenciable, es -- según research.md
Decisión 7 del propio S1.8 -- una capacidad de plataforma sin
requisito de licencia. No existe (ni debe crearse) una entrada `M_D6`
en `MODULOS`. `modulosConVista` en `shell.ts` filtra específicamente
`perfil().modulos_visibles`, que no incluye D6 -- el mecanismo correcto
es el mismo condicional manual ya usado 4 veces en el proyecto.

**Alternatives considered**: agregar D6 como un M10 ficticio a
`MODULOS`. Rechazado -- rompería la invariante "M1-M9 son módulos
licenciables reales del catálogo `catalogo.modulo`" documentada desde
S1.1, y `modulosConVista` asume que cualquier entrada de
`modulos_visibles` tiene una fila real en `catalogo.modulo`.

## Decisión 3 — Cálculo del indicador de SLA: en el cliente, no en el backend

**Decisión**: el tiempo restante/vencido de SLA (FR-001) se calcula en
el frontend a partir de `creado_en` + `sla_objetivo_min` (o
`primera_respuesta_en` si ya existe), no se agrega un campo derivado
nuevo al backend.

**Rationale**: `TicketResponse` ya expone `creado_en`,
`sla_objetivo_min` y `primera_respuesta_en` -- toda la información
necesaria ya viaja en la respuesta existente. Es el mismo patrón ya
usado en S1.12 para el semáforo de ocupación de `puertas/tablero-puertas`
(calculado en el cliente por solapamiento de intervalos, sin endpoint
nuevo) y en S1.14 para "sin señal" del FIDS player. Agregar el cálculo
en el backend implicaría tocar `services/support` sin necesidad real.

**Alternatives considered**: exponer `tiempo_restante_sla_min` ya
calculado desde `api/router.py`. Rechazado por lo anterior -- además
un valor "restante" calculado en el momento de la respuesta HTTP queda
desactualizado apenas el usuario lo mira más de un segundo; recalcular
en el cliente con la hora actual del navegador es más correcto para
una UI que permanece abierta.

## Decisión 4 — Aviso de contenido compartido en la base de conocimientos

**Decisión**: un aviso visual fijo (no descartable) en la sección de
base de conocimientos del panel, señalando que los artículos son
visibles para todos los tenants.

**Rationale**: FR-008/SC-004 lo exigen explícitamente -- es un caso
donde el modelo de datos real (`articulo_kb` sin `tenant_id`,
confirmado en `services/support/aerohub_support/infrastructure/tablas.py`)
diverge del resto de la aplicación (todo lo demás es tenant-scoped por
defecto, Principio I). Mismo criterio que el aviso de inmutabilidad al
activar un tarifario en S1.17 -- informar de una propiedad real del
sistema en el punto donde el usuario podría asumir lo contrario.

**Alternatives considered**: agregar un ícono pequeño junto al título
de la sección. Rechazado -- insuficiente para SC-004 ("100% de las
pantallas... deja explícito"), un ícono se ignora con más facilidad
que un banner de texto.

## Decisión 5 — Observabilidad de uptime: sin vista, documentado como tal

**Decisión**: `GET /support/observabilidad/uptime` no tiene consumidor
en este sprint ni en ninguno futuro planeado.

**Rationale**: decisión de producto ya tomada por el usuario
(2026-08-04, texto literal del PLAN v3.0 §8-bis.6): "Grafana ya lo
resuelve y duplicarlo sería reconstruir una herramienta madura". Se
registra en `spec.md` (FR-012) y aquí para que ningún sprint futuro
lo reabra sin conocer la decisión.

**Alternatives considered**: ninguna -- decisión ya cerrada, no hay
ambigüedad que investigar.
