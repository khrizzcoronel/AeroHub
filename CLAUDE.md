# AeroHub — contexto persistente

Mapa de continuidad entre sesiones, para no tener que re-derivar el estado
del proyecto ni releer todo el historial cada vez que el contexto se
reinicia. La fuente de verdad de arquitectura/requisitos sigue siendo
`docs/PLAN_IMPLEMENTACION_v2.0.md`, `docs/srs/`, `docs/sdd/`, `docs/adr/`
y `docs/estrategia/` — este archivo no los duplica, apunta a ellos y
registra lo que esos documentos no capturan (progreso real, hallazgos
empíricos, reglas de trabajo).

**Al empezar una sesión nueva**: leer este archivo primero. Si el pedido
es "seguir con el siguiente sprint", ir directo a `docs/PLAN_IMPLEMENTACION_v2.0.md`
§8.`<N+1>` (la sección del sprint siguiente al último completado abajo) en
vez de re-explorar el repo entero.

## Metodología: Spec-Driven Development (GitHub Spec Kit) -- OBLIGATORIA desde S1.6

El proyecto usa Spec Kit (`.specify/`, skills `speckit-*` en
`.claude/skills/`). `specs/NNN-<slug>/{spec.md,plan.md,tasks.md}` documenta
cada sprint -- S0.1 a S1.5 se documentaron RETROACTIVAMENTE
(`specs/001-` a `specs/007-`, pedido explícito del usuario el 2026-08-01).

**A partir de S1.6, todo sprint nuevo sigue el flujo Spec Kit ANTES/DURANTE
la implementación, nunca después**: `/speckit-specify` (spec.md a partir de
la sección correspondiente de `docs/PLAN_IMPLEMENTACION_v2.0.md` §8) →
`/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Esto es una
regla de trabajo tan firme como "verificar contra MonetDB real" o "todo
servicio en Docker" -- no es opcional ni se retoma "cuando convenga".

**S1.9 cerrado**: `/speckit-implement` corrió sobre
`specs/011-continuidad-rto-rpo/` -- los 4 componentes de ADR-018
(C1 ya existía desde S0.2, este sprint le agregó retención/purga; C2
snapshot programado + volcado lógico diario catalogados y verificados;
C3 *shipper* idempotente con métrica de atraso; C4 conmutación guiada +
prueba de restauración semanal automatizada), en un paquete nuevo
`packages/continuidad/aerohub_continuidad` (deliberadamente fuera de
`services/`, no es un módulo de negocio) + `tools/continuidad_agente.py`
+ `tools/continuidad_conmutar.py` + 2 contenedores Docker nuevos
(`monetdb-restore-test`, `continuidad-agente`), verificados
empíricamente contra los 3 motores MonetDB reales + MinIO en Docker (23
tests nuevos, 333 unit/negative/cross_tenant totales, todos en verde;
ruff/mypy/bandit/import-linter en verde). **RNF-R01 sigue como riesgo
abierto** (no se cierra en este sprint, por diseño de ADR-018/SRS §2.7 --
requiere 4 semanas consecutivas en verde + 1 *game day* en la Fase 4,
S4.2): el mecanismo ya opera y publica métricas
(`aerohub_standby_lag_seconds`, `aerohub_snapshot_edad_segundos`,
`aerohub_prueba_restauracion_rto_segundos`/`_rpo_segundos`), pero su
observación sostenida todavía no empezó.

**S1.10 cerrado**: `/speckit-implement` corrió sobre
`specs/012-identidad-y-acceso/` -- login real por correo/contraseña con
bloqueo por fuerza bruta, verificación de sesión revocable en cada
petición (`tenants.sesion`, JWT con `sesion_id`), cambio de contraseña
obligatorio en el primer acceso, invitaciones/verificación de
correo/recuperación de contraseña por SMTP real (`mailpit` en
desarrollo, adaptador inyectado vía puerto `EnviarCorreo`), y el
frontend completo de `apps/web` (login, shell con menú dinámico por
rol × licencia, AuthService/interceptor/guard) -- la aplicación deja de
pedir un JWT pegado a mano por primera vez desde S1.1. Documentado en
ADR-020. **Hallazgo real de verificación empírica**: `iniciar_sesion`
insertaba el intento de login fallido y lanzaba la excepción dentro del
mismo `with sesion()`, así que el rollback de la transacción (P8)
borraba el intento junto con la excepción -- el bloqueo por fuerza
bruta y la auditoría de intentos fallidos nunca funcionaron hasta que
un test de integración lo hizo evidente; corregido capturando la
excepción dentro del bloque y relanzándola después de que cierra en
commit. 33 tests nuevos (unitarios + integración contra MonetDB real +
mailpit real, sin mocks de `smtplib`), 480 tests totales, todos en
verde; ruff/mypy/bandit/import-linter en verde. DDL de identidad
verificado contra los 3 motores (primario, `monetdb-standby`,
`monetdb-restore-test`) -- las 75 tareas de `specs/012-identidad-y-acceso/tasks.md`
cerradas.

Hallazgos empíricos nuevos de S1.9 (detalle completo en
`docs/runbooks/monetdb.md`): `sys.hot_snapshot()` exige que el volumen
destino sea escribible por el uid del proceso MonetDB (no por defecto en
un volumen Docker nuevo); `sqlalchemy-monetdb` ya deserializa columnas
JSON a `dict`/`list` en la lectura (no volver a declarar `Column(...,
JSON)` del lado de lectura); un standby/réplica nueva necesita el
checkpoint del *shipper* inicializado al `lsn` máximo actual, no en `0`,
si se siembra por separado en vez de restaurarse desde un snapshot real.

La constitución del proyecto vive en `.specify/memory/constitution.md`
(v1.0.0, ratificada 2026-08-01) y formaliza principios ya vigentes desde
S0.1 (aislamiento fail-closed, arquitectura modular, verificación empírica,
calidad en verde, aprobación explícita) -- no inventa reglas nuevas, y ante
cualquier discrepancia con este archivo, la constitución prevalece.

## Estado del plan (`docs/PLAN_IMPLEMENTACION_v2.0.md` §8)

| Sprint | Contenido | Commit |
|---|---|---|
| S0.1 | Fundación del monorepo: arquitectura, workspace, CI | `181b610` |
| S0.2 | Capa de repositorio: guardián de tenant, roles, DDL fundacional | `0cdc813` |
| S1.1 | AODB backend + Angular mínimo (alta de tenant, alta de vuelo) | `72488fe` |
| S1.2 | API Keys, scopes JWT, rate limiting, WS de estado de vuelo | `14d75ab` |
| S1.3 | M2 FIDS: plantillas/pantallas en tiempo real, sin-señal | `55a9e95` |
| S1.4 | M3 Gate Manager: asignación de puertas, PuLP, tablero Angular | `dbe3b23` |
| S1.5 | M4 Ground Operations (turnaround) + dockerización del stack | `0d95b2e` |
| S1.6 | M5 Billing (motor de facturación, tarifarios, conciliación) + M6 Passenger Experience (tiempos de espera sin PII) | `b4c619f` |
| S1.7 | Licenciamiento por módulo (gateway) + M9 Compliance Hub (post-mortem, incidentes, reportes DGAC, SOC2) + rotación de API Keys | `c0ec739` |
| S1.8 | Soporte D6 (tickets/SLA, KB, changelog) + observabilidad (uptime, error budget, bloqueo de despliegue) | `7f77acf` |
| S1.9 | Continuidad operacional RTO/RPO (ADR-018): snapshot verificado, réplica caliente (shipper), conmutación guiada, prueba de restauración semanal -- RNF-R01 sigue como riesgo abierto (mecanismo + métrica, cierre formal en Fase 4/S4.2) | `0d8b766` |
| S1.10 | Identidad y acceso (ADR-020): login real, sesión revocable, cambio de contraseña obligatorio, invitaciones/verificación/recuperación por correo, frontend completo de auth | `666b660` |
| S1.11 | Rediseño: sistema de diseño (tokens + primitivos `.ah-*`) + quitar JWT manual de 4 vistas/3 servicios + `vuelos/estado-tiempo-real` como vista canónica | `738a44b` |
| S1.12 | Rediseño: `puertas/tablero` (ocupación/conflicto) + `rampa/turnaround` (desviación, tareas, incidencias) | `738a44b` |
| S1.13 | Rediseño: `billing/facturas` (semáforo de estado) + `tenants/nuevo` + auditoría de las 8 vistas de S1.10 (1 inconsistencia real corregida en `login.scss`) | `738a44b` |
| S1.14 | Rediseño: `fids-player/pantalla-player` (3 modos: configuración/reproducción/sin señal) -- cierra el rediseño de interfaz S1.11-S1.14 | pendiente de commit |

Actualizar esta tabla (fila + commit) cada vez que un sprint se cierra con
commit. Es la única fuente de "dónde vamos" que hace falta leer antes de
retomar.

## Rediseño de interfaz (S1.11–S1.14)

La capa operativa (S0.1–S1.10) está **completa y commiteada**. Lo siguiente
acordado con el usuario NO es la Fase 2 del plan de implementación, sino
4 sprints de rediseño de interfaz: de las 14 vistas existentes, 6 quedaron
sin ningún estilo (HTML crudo, renderizado por defecto del navegador)
porque S1.1–S1.6 se construyeron como "Angular mínimo funcional" a
propósito, y el skill `frontend-design` recién se aplicó en S1.10.

**S1.11 implementado** (`specs/013-diseno-sistema-jwt/`, pendiente de
commit): tokens de semáforo operacional + tipografía mono para dato en
`apps/web/src/styles.scss`; primitivos compartidos nuevos
`apps/web/src/app/_primitivos.scss` (`.ah-tira`, `.ah-tabla`, `.ah-campo`,
`.ah-btn`, `.ah-alerta`, `.ah-vacio`); `_auth-form.scss` de S1.10
consolidado sobre esos mismos primitivos (sin cambiar clases en las 6
plantillas HTML de auth); `vuelos/estado-tiempo-real` (M1) rediseñada por
completo como la vista canónica del componente "tira" —verificada en
navegador real contra el WebSocket del gateway en Docker con 3 cambios de
estado reales del vuelo canario MEC—; las 4 vistas que pedían JWT manual
(estado de vuelos, facturas, turnaround, tablero de puertas) y sus 3
servicios HTTP ya no lo requieren — el WebSocket de vuelos lee
`AuthService.token()` en vez de un textarea, ya que no pasa por
`HttpClient`/`authInterceptor`. **Hallazgo empírico**: `apps/web/Dockerfile`
copia el código en build-time (`COPY apps apps`, sin volumen) — un cambio
de frontend no se refleja en el contenedor `web` corriendo hasta
`docker compose up -d --build web`; un simple `restart` sirve el bundle
viejo. También se detectó que IBM Plex Sans/Mono nunca se enlazaron de
verdad desde S1.10 (solo declaradas en `--ah-font-*`, sin `<link>` en
`index.html`) — corregido en este sprint. **Hallazgo adicional**: el
mapeo rol→módulos de S1.10 (`packages/contracts/aerohub_contracts/roles_modulos.py`)
listaba `role_platform_admin` con acceso a M1-M9, pero ese rol no tiene
tenant propio ni scopes de negocio (`vuelos:*`, `billing:*`, etc.) --
el menú ofrecía pantallas que producían 403 al primer clic. Corregido:
`role_platform_admin` ahora ve el menú vacío de módulos operativos (solo
administra tenants/API Keys, que no depende de `modulos_visibles`).

**S1.12 implementado** (`specs/014-tableros-operativos-densos/`,
pendiente de commit): `puertas/tablero-puertas` (M3) rediseñada con
`.ah-tira` por puerta -- el color de la barra refleja ocupación/conflicto,
calculado en el frontend por solapamiento de intervalos de las
asignaciones ya cargadas (sin endpoint nuevo); `rampa/panel-turnaround`
(M4) rediseñada con `.ah-tira` por turnaround (color = desviación
aproximada por `estado`, con refinamiento para "en curso" vencido) y
`.ah-tabla` para tareas e incidencias; primitivo nuevo `.ah-punto`
(`apps/web/src/app/_primitivos.scss`) para semáforo dentro de una celda
de tabla (severidad de incidencia, estado de tarea) -- distinto de
`.ah-tira__barra`, que colorea el borde de una fila completa. Verificado
en navegador real contra datos reales del backend en Docker: ocupación
de puertas correcta (verde/gris, lógica de solapamiento trazada
manualmente sobre datos sembrados reales), tareas completadas en verde,
incidencias de severidad alta/crítica en rojo, sin scroll horizontal en
móvil, sin errores de consola, build de producción en verde.

**S1.13 implementado** (`specs/015-vistas-administrativas-consolidacion/`,
pendiente de commit): `billing/panel-facturas` (M5) rediseñada con
`.ah-tira` por factura (color = estado, mapeo exhaustivo de los 5
valores reales: `vencida`/`disputada`→crítico, `emitida`→atención,
`pagada`→ok, `borrador`→neutro) y `.ah-tabla` para líneas de cargo;
`tenants/tenant-creation` rediseñado con `.ah-campo`/`.ah-btn`, sin
componente "tira" (no hay lista que recorrer en esa vista). **Auditoría
de las 8 vistas de S1.10**: encontró y corrigió una inconsistencia
real -- `auth/login/login.scss` era la única de las 6 vistas de auth que
nunca se consolidó sobre `_auth-form.scss` en S1.11, con una copia
duplicada completa de `.field`/`.btn`/`.alert`/`.card__link`; corregida
importando el archivo compartido, dejando en `login.scss` solo sus
reglas exclusivas (el riel navy decorativo). Las otras 5 vistas y el
shell ya estaban consistentes -- verificado por grep antes de tocar
nada. Con S1.11+S1.12+S1.13, las 5 áreas de negocio de `apps/web` y el
formulario de tenant comparten un mismo sistema visual de punta a punta.

**S1.14 implementado** (`specs/016-fids-player-rediseno/`, pendiente de
commit): única vista de `apps/fids-player` (`pantalla-player`)
reestructurada en 3 modos mutuamente excluyentes derivados de un solo
signal `modoActual` -- `configuracion` (el formulario de código+token
existente, sin login real: NO es deuda técnica en esta app -- no tiene
`AuthService`, es el mecanismo real de configuración de una pantalla
física, con composición visual propia inspirada en `apps/web/auth/login`),
`reproduccion` (contenido de la plantilla activa en tipografía
monoespaciada gigante vía `clamp()`, mínimo 3rem, cero
botones/formularios/tablas visibles) y `sin_senal` (nuevo -- antes solo
había un texto de error genérico superpuesto sobre el último contenido).
**Hallazgo/decisión de diseño**: "sin señal" se infiere enteramente en el
cliente, sin backend nuevo -- cierre de WebSocket con código de rechazo
≥4000 dispara el modo de inmediato, 2 heartbeats fallidos consecutivos
(30s en el peor caso) lo disparan por corte de red silencioso; un solo
fallo NO alcanza, evita parpadeo ante un corte intermitente muy breve;
recuperación automática al primer heartbeat exitoso o mensaje de
plantilla nuevo, sin intervención manual. Tokens de color/tipografía
(navy/semáforo/IBM Plex Sans-Mono) copiados -- no compartidos como
paquete -- de `apps/web/src/styles.scss` a
`apps/fids-player/src/styles.scss`, sin el paquete de primitivos de
consola (`.ah-btn`/`.ah-tabla`, que no aplica a una pantalla sin
interacción); fuentes enlazadas en su `index.html` (mismo hallazgo de
S1.11 replicado en esta segunda app). Respaldo legible para
`definicion_json` que no sigue la convención `filas: [{texto}]`,
reemplazando el `<pre>` de JSON crudo anterior. Cero cambios en
`pantalla.service.ts` ni en el backend. **Con S1.11+S1.12+S1.13+S1.14, no
queda ninguna vista sin estilo en `apps/web` ni en `apps/fids-player` --
el rediseño de interfaz queda completo.**

**Extensión post-S1.13 (pedido directo del usuario, fuera de ciclo Spec
Kit -- revisión rol por rol de accesos/vistas)**: al revisar
`role_platform_admin` se detectó que su único formulario
(`tenants/nuevo`) pedía `aeropuerto_id`/`plan_id` de memoria y no existía
ninguna forma de listar/editar/dar de baja un tenant -- CU-O18 (S1.1)
solo cubría "crear". Se agregó el workpanel completo: `GET
/catalogo/aeropuertos`, `GET /catalogo/planes` (para los `<select>` del
formulario de creación, ya no texto libre), `GET /tenants` (lista, alcance
'interno', sin filtro de tenant), `GET /tenants/{id}`, `PATCH
/tenants/{id}` y `POST /tenants/{id}/estado` (usa por primera vez
`domain/tenant.py::validar_transicion_estado`, existente desde S1.1 sin
ningún llamador real hasta ahora). Nueva vista `apps/web` `tenants/tenant-
list` (ruta `/tenants`, ahora el destino por defecto tras login) con
`.ah-tira` por tenant (semáforo de `estado`) y edición/cambio de estado
inline. El shell ahora muestra el nombre de la vista actual en la barra
lateral (`data.title` de la ruta) -- notorio antes en roles con menú de
módulos vacío, como `role_platform_admin`, que no tenía ninguna señal de
ubicación. **Hallazgo empírico de MonetDB**: `.where(columna.is_(True))`
genera `IS true`, que MonetDB rechaza (`42000!syntax error, esperando
sqlNULL o DISTINCT o NOT` -- solo acepta `IS NULL`/`IS NOT NULL`, no `IS
<booleano>`); corregido con `columna == True` (comparación de igualdad,
no el operador `IS`). Sin spec.md/plan.md propio -- alcance acordado
directamente con el usuario en la sesión, documentado aquí en vez de en
`specs/`.

**Iteración siguiente del workpanel** (mismo día, pedido directo):
paginación de 20 en 20 sobre la lista ya cargada (presentación pura, sin
paginación del lado del backend todavía -- si la cantidad real de
tenants crece, esto se mueve a query params `page`/`page_size` en `GET
/tenants`); crear y editar tenant dejan de navegar/expandir inline y
pasan a un modal (`TenantCreation` se volvió un componente embebible con
`@Output() cerrar`, ya no tiene ruta propia -- se eliminó
`tenants/nuevo` de `app.routes.ts`). Primitivos nuevos en
`_primitivos.scss`: `.ah-modal-fondo`/`.ah-modal` (diálogo superpuesto,
reutilizable por cualquier vista futura) y `.ah-paginacion`. Verificado
en navegador real: el modal abre y cierra sin cambiar la URL (sigue en
`/tenants`), la paginación pasa de página 1 a 2 correctamente sobre
datos reales, build de producción en verde.

**Segunda iteración de estilo del workpanel** (mismo día, pedido
directo): la lista de tenants pasa de `.ah-tira` a una tabla real
(`.ah-tabla` con columnas Código/Razón social/Plan/Estado/Acciones),
distribución pedida explícitamente por el usuario. Primitivo nuevo
`.ah-pill` en `_primitivos.scss` — insignia de estado sólida y
redondeada (mismos 4 tonos de semáforo), para cuando el estado ES la
columna principal, distinto de `.ah-punto` (acompaña un texto ya
existente) y de `.ah-tira__barra` (borde de una fila completa). Botones
de acción de fila reducidos a `.ah-btn--sm` (10 en 10 por página, con
2-3 botones cada una, el tamaño completo se veía desproporcionado).
Paginación bajada de 20 a 10 registros por página (pedido directo).
Verificado en navegador real: colores de pill correctos por estado
(activo=verde, suspendido=ámbar, en_onboarding=gris), scroll horizontal
contenido en `.tabla-envoltorio` (nunca en la página completa) en
viewport móvil, build de producción en verde.

**Tercera iteración: panel de búsqueda + barra de acciones** (mismo día,
pedido directo con referencia visual externa). Antes de implementar se
preguntó explícitamente y el usuario confirmó **mantener los botones de
acción por fila** (no adoptar el patrón "seleccionar fila → botón de
barra actúa sobre ella" de la referencia) — decisión documentada para no
tener que re-derivarla. Primitivos nuevos en `_primitivos.scss`:
`.ah-panel` (card contenedora con título, para agrupar el filtro) y
`.ah-barra-acciones` (fila de botones tipo píldora, más redondeados que
`.ah-btn` normal, para diferenciar "acción de barra de herramientas" de
"acción de formulario"). `tenant-list` gana un filtro en vivo por
código (substring, sin distinguir mayúsculas) y estado (select), 100%
client-side sobre la lista ya cargada (mismo criterio que la paginación
-- si el volumen real de tenants crece, se mueve a query params del
backend). Estado vacío distingue explícitamente "sin tenants" de
"ningún tenant coincide con el filtro". Verificado en navegador real:
filtro por código y por estado combinados funcionan correctamente sobre
datos reales, sin errores de consola, build de producción en verde.

**Cuarta iteración: ancho, acciones consolidadas y formato de estado**
(mismo día, pedido directo, cierre de esta ronda de iteración del
workpanel). Ancho de `.consola` en `tenant-list` iterado varias veces
(960px → 1200px → 1500px → **sin `max-width`**, `width: 100%`) hasta
quedar sin tope fijo -- cualquier número concreto siempre deja espacio
libre en pantallas más anchas que ese número, así que se resolvió de
raíz en vez de seguir subiendo el valor. La columna "Acciones" pasa de
3 botones por fila (Editar/Activar-Suspender/Dar de baja) a **un solo
botón "Ver detalles"** que abre el mismo modal de edición, ahora con la
pill de estado actual en la cabecera y las transiciones válidas
(`transicionesDisponibles`) debajo del formulario -- `cambiarEstado` se
reemplaza por `cambiarEstadoDesdeModal`, que cierra el modal después
(el snapshot `t` con el que se abrió queda desactualizado en cuanto el
estado cambia). Los valores crudos de estado (`en_onboarding`,
`dado_de_baja`) dejan de mostrarse tal cual -- `etiquetaEstadoTenant()`
nueva en `tenant.service.ts` los traduce a texto legible ("En
onboarding", "Dado de baja"), usada en el filtro, la pill de la tabla y
la del modal. Los botones "Nuevo"/"Actualizar" vuelven al radio
estándar del sistema (`var(--ah-radius)`, 6px) en vez del estilo
píldora de `.ah-barra-acciones` -- se dejó de usar esa clase en esta
vista para que los botones se vean consistentes con el resto del
diseño (el primitivo sigue disponible para quien sí quiera esa
variante). `.ah-tabla` gana `table-layout: auto` explícito en
`_primitivos.scss` (documentado como el patrón de distribución
automática de columnas a reutilizar cuando se toquen las demás
vistas). Verificado en navegador real: pills muestran las etiquetas
formateadas, botón único por fila abre el modal con la pill de estado +
las transiciones correctas para ese estado puntual, columnas de la
tabla con anchos distintos según su contenido, sin errores de consola,
build de producción en verde.

**Quinta iteración (backend): correo de bienvenida al crear un tenant**
(mismo día, pedido directo -- "esa credencial debería enviarse al
correo"). `aprovisionar_tenant` (CU-O18, S1.1) ahora envía un correo real
al admin del tenant recién creado con su contraseña temporal, reusando el
puerto `EnviarCorreo`/adaptador SMTP ya construido en S1.10 -- plantilla
nueva `mensaje_bienvenida_tenant()` en `plantillas_correo.py`. **Decisión
de diseño explícita**: a diferencia de `invitar_usuario` (S1.10), que
envía el correo ANTES de persistir (el correo ES la entrega), acá el
envío ocurre DESPUÉS de que la transacción confirma, y un
`EnvioDeCorreoFallo` se traga en silencio en vez de propagarse -- el
tenant y su admin YA son el valor entregado en el momento del envío; un
fallo de SMTP no debe destruir un aprovisionamiento real, y propagar un
502 le ocultaría `password_temporal` (que la pantalla de resultado sigue
mostrando, sin cambios) a quien crea el tenant justo cuando más la
necesita. El correo es un canal adicional, no reemplaza la pantalla.
Verificado contra `mailpit` real (sin mock de `smtplib`): tenant creado
por API, correo con asunto "Tu acceso a &lt;razón social&gt; en AeroHub"
**Sexta iteración: integración SMTP de Gmail real y eliminación de Mailpit**
(mismo día, pedido directo): Se reemplazó el contenedor `mailpit` por configuración real de Gmail SMTP en `infra/docker-compose.yml` (`smtp.gmail.com:587`, TLS) y se actualizó `correo_smtp.py` para limpiar automáticamente espacios en blanco de contraseñas de aplicación de Google. Se detuvo y eliminó el servicio `aerohub-mailpit` del stack Docker para liberar recursos del sistema.

**Séptima iteración: validación en tiempo real de disponibilidad, CORS y mensajes legibles**
(mismo día, pedido directo): Se implementó el endpoint `GET /tenants/validar` (`validar_disponibilidad.py`) que consulta MonetDB en tiempo real bajo `alcance_global`. En `tenant-creation.ts` se conectó validación asíncrona con debounce que resalta en rojo e indica mensajes inline si un código o correo ya existen, deshabilitando el botón de envío. Se ajustó la función global `mensajeDeError()` en `auth.service.ts` para traducir todos los nombres de campos técnicos (`aeropuerto_id y plan_id son obligatorios` → *"Debe seleccionar un aeropuerto y un plan válidos de la lista."*). Se corrigió la intercepción de peticiones preflight HTTP `OPTIONS` en `AutenticacionJWTMiddleware` permitiendo el paso limpio a `CORSMiddleware`.

**Novena iteración: Suite de Workpanels de Tenant Admin y navegación dinámica en Shell**
(mismo día, pedido directo): Se implementó la suite completa de administración del tenant (`role_tenant_admin`). En backend (`aerohub_tenancy`) se expusieron los endpoints `GET /usuarios` (`consultar_usuarios.py`), `GET /api-keys` (`consultar_api_keys_del_tenant()`) y `GET /licencias/mi-tenant` (`consultar_licencias.py`) con aislamiento por tenant estricto. En frontend (`apps/web`) se construyeron los tres workpanels: `UsuarioList` (`/usuarios`) con tabla `.ah-tabla`, paginación e invitación modal por correo (`Invitar`); `ApiKeyList` (`/api-keys`) con rotación, revocación y modal de secreto en claro en `IBM Plex Mono` con botón de copiado al portapapeles; `LicenciaList` (`/licencias`) con lista de módulos contratados (`M1`-`M5`) e insignias de vigencia. Se actualizó la barra lateral del shell (`shell.ts`/`shell.html`) con los condicionales `puedeVerUsuarios()`, `puedeVerApiKeys()` y `puedeVerLicencias()` para desplegar dinámicamente el menú administrativo según la identidad y scopes del usuario logueado.

**La dirección estética completa vive en `docs/diseno/DIRECCION_VISUAL.md`**
— tokens, tipografía, el componente "tira de progreso de vuelo" como
unidad estructural reutilizada en los 5 módulos, la decisión de densidad
sobre aire, la autocrítica del plan, y la división exacta de los 4
sprints. Leer ese archivo antes de tocar cualquier vista; no re-derivar
la dirección de diseño.

Tres decisiones ya tomadas por el usuario (no re-preguntarlas):

1. **M6/M8/M9 quedan fuera**: tienen backend pero ninguna vista Angular;
   crearlas sería construir funcionalidad, no rediseñar.
2. **Quitar el `<textarea>` de JWT manual iba incluido en S1.11 — ya
   hecho**: las 4 vistas (estado de vuelos, facturas, turnaround, tablero
   de puertas) y sus 3 servicios ya no reciben `tokenJwt` por parámetro;
   `grep -rn tokenJwt apps/web/src` solo encuentra comentarios que
   documentan que ya no se usa.
3. **Cada sprint corre su ciclo Spec Kit completo** (`specs/013-` a
   `specs/016-`), dividido así deliberadamente para no sobrecargar el
   contexto de una sola sesión.

## Reglas de trabajo establecidas (no releer el historial para redescubrirlas)

- Implementar cada sprint DE VERDAD (código real corriendo), no solo
  documentarlo.
- Verificar empíricamente contra MonetDB real (Docker) antes de dar una
  tarea por terminada — nunca confiar solo en tests unitarios/mocks para
  cerrar un sprint.
- Mantener ruff, mypy, bandit, import-linter y pytest en verde en todo
  momento; correrlos antes de reportar cualquier tarea como completa.
- Presentar el diff/resumen de cambios ANTES de commitear. Nunca commitear
  sin que el usuario lo pida explícitamente, aunque el trabajo esté listo.
- **Todo servicio que se use para verificar corre en Docker**
  (`infra/docker-compose.yml`, servicios `gateway`/`web`/`fids-player`),
  nunca suelto en el host (`uv run uvicorn` / `npx nx serve`). Ver
  "Entorno de desarrollo" abajo para los comandos.
- **Usar el skill `frontend-design` siempre que se vaya a desarrollar o
  rediseñar una vista** (`apps/web`, `apps/fids-player`) -- dirección
  estética deliberada, no defaults genéricos de framework.
- **Usar el skill `find-skills` cuando haga falta buscar/evaluar otro skill**
  del ecosistema abierto antes de instalarlo con `npx skills add`.
- Responder siempre en español.

## Patrones arquitectónicos establecidos

Referencia más completa y reciente: `services/ramp/aerohub_ramp/` (S1.5).

- Cada módulo de negocio: `services/<modulo>/aerohub_<modulo>/{domain,application,infrastructure,api}`.
  `domain/` puro (sin SQLAlchemy/FastAPI); `infrastructure/` es el ÚNICO
  subpaquete que importa `aerohub_repository`; `api/` solo traduce HTTP
  ↔ `application/`, ninguna regla de negocio ahí (verificado por
  `.importlinter`).
- Independencia de módulos (`.importlinter`, `sin-importacion-cruzada-entre-modulos`):
  ningún módulo importa `domain`/`application` de otro. Si un módulo
  necesita leer una tabla "propiedad" de otro (p. ej. `ops.vuelo` desde
  `gates`/`ramp`), se REDECLARA la `Table()` localmente en el propio
  `infrastructure/tablas.py` y se re-registra su alcance G1 de forma
  idempotente (ver `aerohub_gates/infrastructure/alcances.py` o
  `aerohub_ramp/infrastructure/alcances.py`).
- IDs: Snowflake de 64 bits (`aerohub_kernel.generar_id`) — SIEMPRE viajan
  como string en JSON (request y response), nunca como número JSON (pierde
  precisión en el navegador por encima de `Number.MAX_SAFE_INTEGER`).
- Mutaciones: domain valida primero (fail fast, antes de tocar la base) →
  `with sesion() as conn:` hace el INSERT/UPDATE + `escribir_journal` +
  `registrar_auditoria` en la MISMA transacción → los eventos de dominio
  se publican DESPUÉS de que la transacción confirma. Decorar con
  `@reintentar_en_conflicto()` toda mutación de negocio (ver hallazgos de
  MonetDB abajo).
- Tenant: nunca se acepta `tenant_id` del body/parámetro — siempre
  `contexto_tenant_id()` (poblado por el middleware del Gateway desde el
  JWT). El guardián G1/G2 (`aerohub_repository.guard`) aborta cualquier
  consulta sobre una tabla de alcance `'tenant'` sin filtro explícito.
  `alcance_global()` es la ÚNICA excepción nominal (procesos de plataforma
  sin tenant ambiente), siempre con `motivo`+`rol` explícitos y auditada.
- 404, nunca 403, cuando un recurso es de otro tenant/usuario (PN-01):
  nunca confirmar que el recurso ajeno existe.
- Mínimo privilegio dentro de un mismo tenant (p. ej. `role_ramp_agent`
  sobre sus propias tareas, S1.5): se implementa en `infrastructure/`
  filtrando por `contexto_usuario_id()` cuando el rol activo lo exige, no
  en el motor (MonetDB no tiene RLS).
- Frontend (`apps/web`): el estado de sesión y token se guarda en `localStorage`
  (`AuthService`). El interceptor HTTP (`auth.interceptor.ts`) intercepta 401 y
  403 (por "scope insuficiente") para forzar cierre de sesión y limpieza local si 
  el token caduca (15 min) o sus permisos quedaron obsoletos tras un cambio de rol.
  Patrón de componente: standalone, todo el estado en `signal()`, `inject()` para
  DI, manejo de error uniforme vía `mensajeDeError(err)`. `<input type="datetime-local">`
  no lleva zona horaria — convertir a UTC con un helper tipo `aUtcIso()` antes de
  enviar al backend.

## Hallazgos empíricos de MonetDB (ver también `docs/runbooks/monetdb.md`)

- No soporta `SELECT ... FOR UPDATE` ni `EXCLUDE USING gist`. El "bloqueo
  de fila" se simula con un `UPDATE` sin efecto sobre la fila a proteger
  (ver `aerohub_gates/infrastructure/comandos.py::bloquear_puerta_para_asignacion`).
- Concurrencia optimista: dos escrituras concurrentes reales pueden
  abortar con SQLSTATE `40001` ("...will ROLLBACK instead") **o** `42000`
  ("Update failed due to conflict with another transaction") — dos formas
  distintas del mismo fenómeno. `aerohub_repository.reintentar_en_conflicto`
  reconoce ambas.
- `mclient` (CLI) falla con "invalid multibyte sequence" en archivos con
  caracteres UTF-8 (§, acentos) pasados por argumento/heredoc. Para
  aplicar DDL nuevo con esos caracteres, usar `pymonetdb` directo desde
  Python, no `mclient`.
- `columna_booleana.is_(True)` de SQLAlchemy genera `IS true`, que MonetDB
  rechaza (`42000!syntax error, esperando sqlNULL o DISTINCT o NOT` --
  el operador `IS` solo acepta `NULL`/`NOT NULL`, no un literal booleano).
  Usar `columna_booleana == True` (comparación de igualdad, `= true`) en
  su lugar. Encontrado en `consultas_catalogo.py::listar_planes`.
- Permisos bajo `SET ROLE`: cualquier tabla leída durante una consulta 
  (incluso vía `JOIN` o subquery interna) requiere un `GRANT SELECT` 
  explícito al rol en MonetDB. Si falta, la base de datos lanza `access denied`
  (que en FastAPI llega como un `OperationalError` de SQLAlchemy y se traduce
  a `403 acceso denegado`).

## Entorno de desarrollo

- El binario `uv` **no** está en el PATH del host — dentro de la imagen
  Docker del gateway sí (`services/gateway/Dockerfile` lo instala). Si
  hace falta actualizar `uv.lock`, reconstruir la imagen del gateway y
  copiar el lock resultante (`docker cp aerohub-gateway:/app/uv.lock .`),
  no intentarlo en el host.
- Todo el stack corre en Docker:
  ```bash
  docker compose -f infra/docker-compose.yml up -d monetdb gateway web fids-player
  ```
  Gateway en `:8000`, `web` en `:4200`, `fids-player` en `:4300`.
- Seeds de desarrollo: `uv run python -m db.seeds.generate` (dentro de un
  entorno con `uv`, p. ej. el contenedor del gateway). Tenants canario
  fijos: `MEC` y `UIO` (código/email/vuelos estables, usados por
  `tests/cross_tenant/` y por los `datos_canario` de casi toda la suite de
  integración).
