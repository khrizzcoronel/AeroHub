# AeroHub — contexto persistente

Mapa de continuidad entre sesiones, para no tener que re-derivar el estado
del proyecto ni releer todo el historial cada vez que el contexto se
reinicia. La fuente de verdad de arquitectura/requisitos sigue siendo
`docs/PLAN_IMPLEMENTACION_v3.0.md`, `docs/srs/`, `docs/sdd/`, `docs/adr/`
y `docs/estrategia/` — este archivo no los duplica, apunta a ellos y
registra lo que esos documentos no capturan (progreso real, hallazgos
empíricos, reglas de trabajo).

**Al empezar una sesión nueva**: leer este archivo primero. Si el pedido
es "seguir con el siguiente sprint", ir directo a `docs/PLAN_IMPLEMENTACION_v3.0.md`
§8.`<N+1>` (la sección del sprint siguiente al último completado abajo) en
vez de re-explorar el repo entero.

## Metodología: Spec-Driven Development (GitHub Spec Kit) -- OBLIGATORIA desde S1.6

El proyecto usa Spec Kit (`.specify/`, skills `speckit-*` en
`.claude/skills/`). `specs/NNN-<slug>/{spec.md,plan.md,tasks.md}` documenta
cada sprint -- S0.1 a S1.5 se documentaron RETROACTIVAMENTE
(`specs/001-` a `specs/007-`, pedido explícito del usuario el 2026-08-01).

**A partir de S1.6, todo sprint nuevo sigue el flujo Spec Kit ANTES/DURANTE
la implementación, nunca después**: `/speckit-specify` (spec.md a partir de
la sección correspondiente de `docs/PLAN_IMPLEMENTACION_v3.0.md` §8) →
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

## Estado del plan (`docs/PLAN_IMPLEMENTACION_v3.0.md` §8)

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
| S1.14 | Rediseño: `fids-player/pantalla-player` (3 modos: configuración/reproducción/sin señal) -- cierra el rediseño de interfaz S1.11-S1.14 | `2285ced` |
| S1.15 | Fase 1.5: contrato de API generado + superficie del AODB (alta de vuelo, registro de estado) + 2 endpoints huérfanos (cancelar asignación, reenviar verificación) | `b6fb8df` |
| S1.16 | Fase 1.5: administración de FIDS (plantillas, pantallas, telemetría) -- corrige además el hallazgo crítico de que ningún rol tenía scopes `fids:*` | `afd9ad4` |
| S1.17 | Fase 1.5: tarifarios (RF-T10) y conciliación de pax -- historial completo de tarifarios con conceptos, activación con aviso de inmutabilidad, conciliación con diferencia derivada | `f23bb3e` |
| S1.18 | Fase 1.5: informes operativos (familia RF-I nueva) -- 6 informes (simple+compuesto) en M1/M3/M4/M5/Tenancy/M9, primitivo `.ah-informe`, exportación CSV, auditoría de emisión en M5/M9 | `3e066ba` |
| S1.19 | Fase 1.5: Compliance Hub (M9) -- listados/catálogos nuevos, vista `compliance/panel`, hallazgo de scopes de `role_sre` corregido | `7b0cc68` |
| S1.20 | Fase 1.5: D6 Soporte (tickets con SLA, KB, changelog) -- cierra la Fase 1.5 completa (S1.15-S1.20) | `0a23e2d` |
| **Iteración post-S1.18** | **Dashboard de informes consolidado (1 vista en vez de 6) + panel táctico demo sobre ClickHouse (M7) + 3 arreglos de autocarga -- ver sección propia más abajo, sin sprint number formal, trabajo directo del usuario 2026-08-05** | **pendiente de commit -- retomar aquí** |
| S2.1 | Fase 2 -- retomar en `docs/PLAN_IMPLEMENTACION_v3.0.md` §8, sprint siguiente a S1.20 (después de cerrar la iteración de arriba) | pendiente |

Actualizar esta tabla (fila + commit) cada vez que un sprint se cierra con
commit. Es la única fuente de "dónde vamos" que hace falta leer antes de
retomar.

## Fase 1.5 -- Cierre de superficie de usuario (PLAN v3.0, §8-bis)

**El plan pasó a v3.0 el 2026-08-04.** `docs/PLAN_IMPLEMENTACION_v2.0.md`
quedó supersedido y se retiró el 2026-08-08 (pedido explícito del
usuario); la línea base vigente es `docs/PLAN_IMPLEMENTACION_v3.0.md`, que
conserva las Fases 2-4 textualmente y agrega la Fase 1.5.

**Por qué existe esta fase**: al cerrar la Fase 1, un inventario
automático encontró que **38 de los 83 endpoints del backend (46 %) no
tenían ningún consumidor en el frontend**, y 12 de ellos bloqueaban
casos de uso con actor humano confirmado. No fue un fallo de ejecución
--cada sprint cumplió su DoD-- sino de especificación: los DoD de la v2.0
se redactaban como criterios verificables por API, nunca como "el actor
puede hacerlo desde la aplicación". La v3.0 corrige la DoD genérica
(§6.5 punto 9) para que eso no vuelva a pasar.

Evidencia completa en `docs/estrategia/ANALISIS_RUMBO_Y_BRECHAS_2026-08.md`.
La matriz endpoint↔vista completa y el triaje de las 38 brechas en clases
A/B/C/D vivía en `docs/diseno/PLAN_REVISION_ENDPOINTS_FRONT.md`, retirado
2026-08-08 tras cerrarse la Fase 1.5 que resolvió las 38 brechas (ver la
fila S1.15-S1.20 más abajo).

**Los 3 casos más graves** (los que motivan el orden de los sprints):
`POST /vuelos` no existe en la UI --M1, el módulo núcleo, muestra cambios
de estado pero no permite producirlos--; `POST /fids/pantallas` tampoco
--el player pide un código de pantalla que ninguna interfaz crea--; y los
3 endpoints de tarifarios tampoco, lo que vuelve inoperable a RF-T10, que
promete "variantes de tarifario sin despliegue de código" y hoy exige un
INSERT a mano en MonetDB.

| Sprint | Contenido |
|---|---|
| S1.15 | Contrato: `openapi.yaml` **generado** desde FastAPI + CI que falla si difiere · superficie de M1 AODB · 2 endpoints huérfanos (cancelar asignación, reenviar verificación) |
| S1.16 | Administración de FIDS: plantillas, pantallas, asignación, tablero de telemetría |
| S1.17 | Tarifarios (RF-T10) y conciliación de pax |
| S1.18 | **Informes operativos** (familia RF-I nueva): 6 informes simples + compuestos, primitivo `.ah-informe` |
| S1.19 | M9 Compliance Hub: post-mortems, incidentes, reportes DGAC, evidencia SOC2 |
| S1.20 | D6 Soporte: tickets con SLA, KB, changelog |

**Decisiones tomadas por el usuario el 2026-08-04 (no re-preguntar)**:

1. **M9 y D6 SÍ llevan interfaz** -- se descartó declararlos "solo API".
2. **Los informes se implementan en la Fase 1.5**, no solo se especifican.
3. **Se generó un v3 completo** en vez de enmendar v2 o hacer un anexo.

**Hallazgo que bloquea a los demás sprints** (tarea R0 del extinto plan de
revisión de endpoints): `docs/api/openapi.yaml` tiene 60
rutas y el backend real ~72 -- le faltan **todas** las del workpanel
construido después del 2026-08-02. CI corre
`spectral lint docs/api/openapi.yaml` y pasa en verde porque el archivo
es *válido*, no porque describa la API. RF-T02 está cumplido en la forma
y vacío en el fondo. Por eso S1.15 empieza por regenerarlo desde
`app.openapi()` y agregar la compuerta que falla ante la divergencia.

**Regla de motor para informes** (v3.0 §8-bis.0), para no romper ADR-016:
informes de **horizonte operativo** (período en curso, necesarios para
operar o para emitir un documento con validez) van sobre **MonetDB** en
la Fase 1.5, amparados por la excepción textual de §3.5 del Análisis v6.0
(OP4/facturación mensual opera sobre dato vivo); informes de **horizonte
táctico** (comparativas multi-período, tendencias) esperan a
**ClickHouse `ah_tactico`** en S2.4. Se divide por horizonte de la
pregunta, no por complejidad de la consulta.

**S1.15 implementado** (`specs/017-contrato-api-superficie-aodb/`,
pendiente de commit): `tools/generar_openapi.py` (existía desde S1.2,
nunca se había vuelto a correr) regenerado -- `docs/api/openapi.yaml`
pasa de 60 a 72 rutas; `.github/workflows/ci.yml` gana un paso en el job
`contrato-api` que regenera el esquema y compara contra el comiteado,
fallando ante cualquier divergencia futura. Superficie nueva de M1 AODB
en `vuelos/estado-tiempo-real`: modal "Nuevo vuelo" y modal "Cambiar
estado" por fila, consumiendo los 3 endpoints REST que solo existían por
API (`POST /vuelos`, `GET /vuelos/{id}`, `POST /vuelos/{id}/estados`).
**Hallazgo/decisión**: el formulario de alta necesitaba catálogos de
aerolínea/aeronave/tipo de vuelo que no tenían endpoint -- se agregaron
`GET /vuelos/catalogo/{aerolineas,aeronaves,tipos-vuelo}` en
`aerohub_aodb`, redeclarando las tablas de `catalogo.*` de solo lectura
(mismo patrón que `catalogo.aeropuerto` en tenancy; ya estaban
registradas como alcance `'global'` en el guardián central, sin DDL
nuevo). El cambio de estado no sintetiza una fila local tras el POST --
se apoya en que el WebSocket ya conectado entrega el evento real en
<1s (RNF-P01), evitando una fila duplicada. Se cerraron además los 2
endpoints huérfanos de bajo costo: botón "Cancelar" en el modal de
asignaciones de `puertas/tablero-puertas`, y un banner en el shell
(`perfil().email_verificado === false`) con reenvío de verificación --
**no** en la vista pública `/verificar-correo`, porque
`POST /auth/solicitar-verificacion` opera sobre la sesión ya autenticada
y esa vista es alcanzable sin sesión. Verificado: ruff/mypy/bandit/
import-linter en verde sobre `aerohub_aodb`; 3 tests de integración
nuevos contra MonetDB real (`tests/integration/test_aodb_catalogos.py`);
build de producción de `apps/web` en verde.

**S1.16 implementado** (`specs/018-administracion-fids/`, pendiente de
commit): superficie completa de M2 FIDS, hasta ahora sin ninguna vista en
`apps/web` (`ruta: null` en `roles_modulos.py`). **Hallazgo crítico**:
ningún rol tenía ningún scope `fids:*` -- los 3 endpoints de escritura de
S1.3 eran literalmente inalcanzables por cualquier sesión humana desde
que se construyeron; corregido agregando `fids:leer`/`fids:administrar` a
`role_tenant_admin`. 3 endpoints GET nuevos en `aerohub_fids`
(`/fids/plantillas`, `/fids/pantallas`, `/fids/catalogo/terminales`,
todos `fids:leer`, tenant-scoped) que no existían -- antes solo había
altas/heartbeat, ningún listado. Vista nueva `fids/pantalla-list`
(`/fids/pantallas`) con dos tablas (plantillas, pantallas) en el mismo
componente -- `modulosConVista` asigna una ruta por módulo y M2 es un
solo módulo; alta de plantilla, alta de pantalla (con selects reales de
terminal/plantilla, nunca ids pegados a mano), acción "Asignar plantilla"
por fila, y el código de pantalla recién registrada en un aviso copiable
(mismo patrón que la contraseña temporal de `tenant-creation`). Catálogo
de terminales (`ops.terminal`) redeclarado en `aerohub_fids/infrastructure/`
-- a diferencia de los catálogos globales de S1.15, este SÍ es
tenant-scoped (tiene `tenant_id` real); riesgo de datos conocido: nunca
se sembró formalmente en `db/seeds/generate.py`, los datos actuales son
artefactos de tests de integración anteriores (fuera de alcance de este
sprint). **Hallazgo empírico de MonetDB** (ver también la sección de
hallazgos más abajo): `listar_plantillas` (última versión por nombre)
falló como `JOIN` contra una subconsulta `GROUP BY` -- reescrito como
anti-join `NOT EXISTS`. Verificado: ruff/mypy/bandit/import-linter en
verde sobre `aerohub_fids` (contra la imagen reconstruida, no solo el
contenedor parcheado en caliente); 3 tests de integración nuevos contra
MonetDB real (`tests/integration/test_fids_administracion.py`); build de
producción de `apps/web` en verde. **No verificado en navegador real**
(regla vigente desde esta sesión: no probar automáticamente en el
navegador salvo pedido explícito) -- pendiente si el usuario lo solicita.

**S1.17 implementado** (`specs/019-tarifarios-conciliacion-pax/`,
pendiente de commit): superficie completa de tarifarios (RF-T10) y
conciliación de pax (RF-O15) en M5 Billing, hasta ahora sin ningún
consumidor en `apps/web` pese a existir desde S1.6. A diferencia de
S1.15/S1.16, **sin hallazgo de scopes** -- `role_tenant_admin` y
`role_billing_officer` ya tenían `billing:escribir`, verificado antes de
implementar. 3 endpoints GET nuevos en `aerohub_billing`
(`/billing/tarifarios` con historial completo y conceptos anidados,
`/billing/conciliaciones`, `/billing/catalogo/conceptos-cargo`), todos
`billing:leer`. Vista nueva `billing/panel-tarifarios` con dos
secciones (tarifarios, conciliaciones) -- expuesta como enlace manual
del shell (`puedeVerTarifarios`, por scope `billing:escribir`), no como
segunda ruta de M5: `modulosConVista` solo admite una ruta por módulo y
`/billing/facturas` ya la ocupa desde S1.13, mismo mecanismo que
`usuarios`/`api-keys`/`licencias`. **Corrección de 2 suposiciones
erróneas del spec inicial tras leer el código real (Principio III)**:
`conciliar()` EXIGE diferencia cero para marcar conciliada (no al
revés, como decía el borrador -- compuerta de pruebas deliberada de
S1.6), y `pax_registrado_sistema` es un dato de entrada al registrar
una conciliación, no algo que el sistema calcula solo. El aviso de
inmutabilidad al activar un tarifario es puramente informativo -- el
backend (`activar_tarifario`) nunca validó "al menos un concepto", así
que el frontend tampoco introduce esa regla. Verificado: ruff/mypy/
bandit/import-linter en verde sobre `aerohub_billing`; 3 tests de
integración nuevos contra MonetDB real vía `TestClient`
(`tests/integration/test_billing_tarifarios_conciliacion.py`), suite
existente `test_billing_facturacion.py` sin regresiones (11/11 verde);
build de producción de `apps/web` en verde. No verificado en navegador
real (misma regla vigente).

**S1.18 implementado** (`specs/020-informes-operativos/`, commit
`3e066ba`): formaliza la familia de requisitos RF-I01-RF-I04 (informes
simples/compuestos, totales calculados en el servidor, parámetros
declarados en el artefacto exportado, auditoría de emisión) con 6
informes -- uno simple y uno compuesto por módulo dueño de su tabla
raíz: M1 AODB (vuelos por aerolínea, puntualidad), M3 Gates
(asignaciones por puerta, conflictos), M4 Ground Ops (turnarounds por
tipo de tarea, incidencias), M5 Billing (facturación por concepto de
cargo, cierra RF-E02), Tenancy (tenants por plan×estado, usuarios/
licencias), M9 Compliance (eventos de auditoría, emisión de
`reporte_dgac` por tipo). **Decisión de diseño explícita**: un único
componente Angular reutilizable `informes/panel-informe` configurado
por `@Input()` en vez de 6 vistas casi idénticas -- los 6 módulos
solo aportan una configuración declarativa (`informes-config.ts`) más
un componente de una línea cada uno (sin `withComponentInputBinding()`
habilitado en el router, hacía falta ese paso intermedio). Primitivo
CSS nuevo `.ah-informe` (cabecera de parámetros/fecha de generación,
filas de subtotal/total diferenciadas). CSV se construye en el mismo
endpoint que el JSON (`?formato=csv`) a partir del mismo objeto ya
calculado, nunca una consulta paralela. RF-I04 (auditoría de emisión)
solo en los informes compuestos de M5 y M9, los únicos con validez
externa en este sprint. **2 hallazgos empíricos nuevos de MonetDB**
(detalle en la sección de hallazgos más abajo): `GROUP BY` sobre una
columna en su forma completa `esquema.tabla.columna` es rechazado
incluso para la consulta agregada más simple -- se resuelve con
`tabla.alias("v")`; y `select(tabla)` completo sobre una tabla con
columna `JSON` (aquí `compliance.log_auditoria`) vuelve a fallar el
patrón ya documentado en S1.9 si se seleccionan también las columnas
JSON sin necesitarlas. Verificado: ruff/mypy/bandit/import-linter en
verde sobre los 6 servicios (incluye 3 hallazgos de deuda preexistente
en `aerohub_tenancy` corregidos de paso porque bloqueaban un run
limpio: un `type: ignore` de mypy en `correo_smtp.py`, un `Row` sin
importar en `licencia.py`, una variable ambigua `l` en `router.py`);
15 tests de integración nuevos contra MonetDB real (uno por módulo,
más SC-002/SC-003/RF-I04), suite `test_billing_facturacion.py` y
`test_aplicacion_s1_1.py` sin regresiones; build de producción de
`apps/web` en verde. No verificado en navegador real (regla vigente).

**S1.19 implementado** (`specs/021-compliance-hub/`, pendiente de
commit): superficie completa de M9 Compliance Hub, hasta ahora sin
ninguna vista en `apps/web` (`ruta: null` en `roles_modulos.py`).

1. **Hallazgo crítico** (`packages/contracts/aerohub_contracts/roles_modulos.py`):
   `role_sre` no tenía ningún scope `compliance:*` pese a que
   `_exigir_role_sre()` (`gestionar_post_mortem.py`, S1.7/ADR-009) exige
   exactamente ese rol para post-mortems -- mismo patrón que el hallazgo
   de `fids:*` en S1.16. Se agregó `M9` a sus módulos y
   `compliance:leer`/`compliance:escribir` a sus scopes. **Verificado
   empíricamente contra MonetDB real vía `TestClient`**: `role_sre` ya
   puede `POST /compliance/incidentes` y `POST /compliance/post-mortems`
   (201, antes 403). Ojo con un hallazgo *distinto* encontrado de paso,
   **sin tocar**: `role_tenant_admin` tiene `compliance:leer`/`escribir`
   a nivel de scope de aplicación desde S1.7, pero **no tiene ningún
   `GRANT` de motor** sobre `compliance.*` (`db/ddl/monetdb/93_grants_compliance.sql`/
   `99_grants_compliance_hub.sql` solo otorgan a `role_platform_admin`,
   `role_sre`, `role_data_engineer`, `role_regulatory_auditor`,
   `role_elt_reader`) -- cualquier query de `role_tenant_admin` sobre
   `compliance.*` falla con `403 acceso denegado` a nivel de motor,
   pre-existente desde S1.7, fuera de alcance de este sprint (usar
   `role_sre`/`role_regulatory_auditor` para probar M9, nunca
   `role_tenant_admin`).
2. **Backend completo y verificado en verde** (`ruff`/`mypy` pasan sobre
   `services/compliance` y `packages/contracts`): 4 listados nuevos
   (`listar_post_mortems`, `listar_reportes_dgac`, `listar_accesos_auditor`,
   `listar_evidencia_soc2` en `infrastructure/consultas.py`), 3 catálogos
   nuevos (`infrastructure/consultas_catalogo.py`: tipos de incidente,
   tipos de reporte regulatorio, controles SOC2), sus casos de uso en
   `application/consultar.py`/`consultar_catalogos.py` (nuevo), y 7
   endpoints GET nuevos en `api/router.py` (`/compliance/post-mortems`,
   `/reportes-dgac`, `/accesos-auditor`, `/evidencia-soc2`,
   `/catalogo/{tipos-incidente,tipos-reporte,controles-soc2}`). Probado
   uno por uno con `TestClient` real (crear incidente → crear post-mortem
   con `role_sre` → listar; emitir reporte DGAC con `role_sre` → listar
   con hash visible; catálogos con `role_regulatory_auditor`) -- todos
   200/201 según corresponda.
3. **Frontend completo**: `apps/web/src/app/compliance/compliance.service.ts`
   (11 métodos) y `apps/web/src/app/compliance/panel-compliance/`
   (`.ts`/`.html`/`.scss`, 5 secciones: incidentes, post-mortems con
   detalle+acciones+publicar, reportes DGAC, accesos de auditor,
   evidencia SOC2 -- esta última con alta condicionada a
   `puedeEscribir()`, que lee `AuthService.perfil()?.scopes`, research.md
   Decisión 4). Ruta `compliance/panel` → `PanelCompliance` agregada en
   `app.routes.ts`. **Hallazgo corregido en `shell.ts`**: `role_support`
   tiene M9 en `modulos_visibles` (opera tickets, no compliance) pero
   ningún scope `compliance:*` -- sin filtro adicional habría visto el
   enlace del menú y cada llamada del panel habría devuelto 403 al
   cargar. `modulosConVista` ahora excluye M9 específicamente cuando el
   perfil no trae `compliance:leer` (exclusión por módulo, no por rol
   completo -- distinto del mecanismo de `role_platform_admin` en S1.11,
   que excluye TODOS los módulos).
4. **Verificado**: `docker cp` de los 6 archivos backend + 3 frontend al
   contenedor, `ruff check --fix`/`mypy` en verde sobre
   `services/compliance` + `packages/contracts`; `npx nx build web
   --configuration=production` en verde dentro de `aerohub-web` (2
   warnings preexistentes de `informes/panel-informe`, sin relación con
   este sprint, más el warning de presupuesto de bundle ya conocido).
   `tests/integration/test_compliance_hub.py` nuevo (T021, 5 tests:
   ciclo incidente→post-mortem con `role_sre`, reporte DGAC con hash
   visible, catálogos con `role_regulatory_auditor`, evidencia SOC2
   escrita por `role_sre`/leída por auditor, aislamiento de tenant
   MEC/UIO) -- los 5 en verde contra MonetDB real; suites existentes
   `test_compliance_post_mortem.py` y `test_compliance_informes.py` sin
   regresiones (6/6 verde). No verificado en navegador real (regla
   vigente desde S1.16 -- no probar automáticamente salvo pedido
   explícito).

**S1.20 implementado** (`specs/022-soporte-d6/`, pendiente de commit):
superficie completa de D6 Soporte (tickets con SLA, base de
conocimientos, changelog), hasta ahora sin ninguna vista en `apps/web`
pese a que los 11 endpoints existen desde S1.8. **Cierra la Fase 1.5
completa (S1.15-S1.20)**.

1. **Hallazgo crítico** (`packages/contracts/aerohub_contracts/roles_modulos.py`):
   `publicar_changelog()` (`gestionar_changelog.py::_ROL_AUTORIZADO`)
   exige exactamente `role_platform_admin`, pero ese rol no tenía
   ningún scope `support:*` -- `POST /support/changelog` era
   inalcanzable por cualquier rol del sistema desde S1.8 (mismo patrón
   que `fids:*` en S1.16 y `compliance:*` en S1.19). La suite de tests
   original de S1.8 (`test_kb_changelog.py`) nunca lo detectó porque
   fabrica el JWT con `codificar_jwt(scopes=[...])` a mano en vez de
   derivarlo de `roles_modulos.py` -- enmascaraba el hallazgo real de
   producción. Corregido agregando `support:leer`/`support:escribir` a
   `role_platform_admin`.
2. **Segundo hallazgo, revelado por el test de integración (no por la
   lectura de código)**: `cambiar_estado_ticket()` es exclusivo de
   `role_support` -- `role_tenant_admin`/`role_sre` pueden crear
   tickets y responder (con `support:escribir`), pero no mover la
   máquina de estados. No es un bug -- es la regla de negocio real de
   S1.8 -- pero el frontend debía ocultar esos botones para cualquier
   rol que no fuera `role_support`, no solo dejar que el backend
   devolviera 403.
3. **Endpoint nuevo**: `GET /support/catalogo/categorias-ticket`
   (`support:leer`) -- el formulario de alta de ticket necesitaba
   `categoria_id` y no existía ningún catálogo, mismo patrón de brecha
   ya corregido para aerolíneas/aeronaves en S1.15.
4. **Frontend completo**: `apps/web/src/app/soporte/soporte.service.ts`
   (10 métodos) y `apps/web/src/app/soporte/panel-soporte/`
   (`.ts`/`.html`/`.scss`, 3 secciones: tickets con indicador de SLA
   calculado en el cliente -- research.md Decisión 3, no un campo
   nuevo de backend --, base de conocimientos con aviso fijo de
   contenido compartido entre tenants, changelog). Ruta `soporte/panel`
   → `PanelSoporte`; enlace manual del shell (`puedeVerSoporte()`, por
   scope `support:leer` -- D6 no es un módulo M1-M9 licenciable, mismo
   mecanismo que tarifarios/informes). La sección de tickets se oculta
   por completo para `role_platform_admin` (sin tenant propio,
   `listar_tickets_de_tenant` lanzaría `ContextoTenantAusente`/500 --
   mismo hallazgo de S1.11 para usuarios/API Keys). Los controles de
   escritura se condicionan no solo por scope sino por rol específico
   donde el dominio lo exige (nota interna y cambio de estado:
   `role_support`; publicar KB: `role_support`/`role_platform_admin`;
   publicar changelog: `role_platform_admin`).
5. **Verificado**: `docker cp` de los 6 archivos backend + 5 frontend
   al contenedor, `ruff`/`mypy` en verde sobre `services/support` +
   `packages/contracts`; `bandit`/`import-linter` en verde sobre el
   repo completo; `npx nx build web --configuration=production` en
   verde (mismos 2 warnings preexistentes de `informes/panel-informe`).
   `tests/integration/test_soporte_hub.py` nuevo (8 tests: catálogo de
   categorías, ciclo de ticket con `role_tenant_admin`, nota interna
   403/visibilidad por rol, transición de estado 403 por rol + 409 por
   transición inválida, KB visible entre tenants + 403 para tenant,
   changelog publicado por `role_platform_admin` + 403 para
   `role_support`) -- 12/12 en verde junto con la suite existente
   `test_kb_changelog.py`; sin regresiones en
   `test_ticket_sla.py`/`test_pn01_tickets_cross_tenant.py`/
   `tests/unit/support` (30/30 en total). No verificado en navegador
   real (regla vigente desde S1.16).

## Fase 1.5 -- cerrada (S1.15-S1.20)

Los 38 endpoints huérfanos detectados en el inventario de brechas (extinto
plan de revisión de endpoints, retirado 2026-08-08) quedaron resueltos:
contrato de API regenerado + superficie de M1 AODB (S1.15),
administración de FIDS/M2 (S1.16), tarifarios/conciliación de M5
(S1.17), informes operativos RF-I01-04 en 6 módulos (S1.18), M9
Compliance Hub (S1.19), D6 Soporte (S1.20). Retomar en
`docs/PLAN_IMPLEMENTACION_v3.0.md` §9, Fase 2 (S2.1 -- `etl_control` e
ingesta a bronce), la primera fase que la v3.0 deliberadamente puso
DESPUÉS de cerrar esta superficie (§8-bis, "por qué la Fase 1.5 va
antes de la Fase 2 y no en paralelo").

## Iteración post-S1.18: dashboard de informes + panel táctico demo (2026-08-05, pendiente de commit)

**Trabajo hecho directamente por el usuario** (fuera de una sesión de
Claude Code), sin ciclo Spec Kit propio -- documentado aquí para que la
sesión siguiente retome desde el estado real del working tree, no desde
el último commit (`0a23e2d`, S1.20). **Punto de partida obligatorio de
la próxima sesión**: correr `git status`/`git diff` antes de asumir que
el árbol coincide con el último commit.

1. **Consolidación del dashboard de informes (3er pase de rediseño de
   S1.18)**: los 6 enlaces sueltos del menú ("Informes · AODB",
   "Informes · Gates", etc., cada uno con su propia ruta/componente en
   `informes/rutas/informes-rutas.ts`, **ahora eliminado**) se
   reemplazaron por una vista única `informes/dashboard-informes/`.
   Arma dinámicamente una sección por módulo según los scopes del
   perfil (`vuelos:leer`, `puertas:leer`, `rampa:leer`, `billing:leer`,
   `tenants:administrar`, `compliance:leer`), con un layout fijo
   calcado de una referencia visual que aportó el usuario: 4 tarjetas
   KPI arriba, abajo 2 columnas -- gráfico de barras horizontales
   (**compuesto**, badge "Compuesto · ClickHouse") a la izquierda,
   tabla (**simple**, badge "Simple · MonetDB") a la derecha. El menú
   lateral (`shell.ts`) pasó de 6 computed (`puedeVerInformesVuelos`,
   etc.) a un único `puedeVerInformes` -- el enlace solo decide si HAY
   algo que mostrar, el dashboard decide qué.
2. **Servicio nuevo `aerohub_analytics_api` (M7) -- panel "táctico"
   DEMO sobre ClickHouse, explícitamente temporal**: endpoint
   `GET /analytics/tactico/{modulo}` que lee un snapshot pre-calculado
   en ClickHouse (`ah_tactico_demo.compuesto_informe`), NO una consulta
   en vivo contra MonetDB. El propio código (`infrastructure/__init__.py`
   y el docstring de `tools/sincronizar_analytics_demo.py`) deja
   explícito que esto **no** es `ah_tactico`, la capa analítica real que
   la Fase 2/S2.4 construye sobre ADR-016 -- es una demo mínima que se
   retira cuando esa fase exista. El snapshot se llena corriendo
   `uv run python tools/sincronizar_analytics_demo.py --tenant-codigo MEC`
   dentro del contenedor gateway: el script llama por HTTP real a los 6
   endpoints `/X/informes/compuesto` ya existentes desde S1.18 (respeta
   la independencia de módulos -- no importa `domain`/`application` de
   ningún módulo de negocio) y vuelca el resultado a ClickHouse.
   **Reutiliza el hallazgo de grants de S1.19**: `role_tenant_admin` no
   tiene `GRANT` de motor sobre `compliance.*`, así que el script usa
   `role_sre` solo para ese módulo. `infra/docker-compose.yml` ahora
   depende de un contenedor `clickhouse` con healthcheck
   (`AEROHUB_CLICKHOUSE_HOST=clickhouse`).
3. **3 arreglos de autocarga (hallazgo de UX, pedido directo)**:
   `billing/panel-facturas`, `puertas/tablero-puertas` y
   `rampa/panel-turnaround` no mostraban nada hasta presionar un botón
   "Cargar..." -- sus métodos de listado no reciben parámetros (el
   filtro es 100% client-side), así que no había motivo para no cargar
   al entrar. Los 3 ganaron un `constructor()` que llama al listado de
   entrada, mismo criterio que `panel-tarifarios`/`panel-compliance`/
   `panel-soporte` desde su propio sprint.
4. **Utilidad nueva `tools/crear_usuarios_demo_roles.py`** (no forma
   parte de ningún sprint ni de `db/seeds/generate.py`): crea un usuario
   demo por cada rol tenant-scoped en el tenant canario MEC
   (`role_operations_controller`, `role_airline_coordinator`,
   `role_ramp_agent`, `role_billing_officer`, `role_tenant_analyst`,
   `role_regulatory_auditor`), contraseña fija `aerohub-demo-2026`,
   idempotente por email -- para poder iniciar sesión y probar la
   aplicación con cualquier rol sin pasar por el flujo de invitación.

**Cierre de la iteración (misma sesión, 2026-08-05)**: el diseño del
dashboard pasó por 3 rechazos explícitos del usuario antes de este
layout final -- vale la pena registrarlo para no repetir los mismos
intentos en una sesión futura:

1. Primer intento: secciones apiladas verticalmente, un `.ah-panel`
   compacto de filtros/tabla oculto detrás de un botón "Consultar
   detalle" por módulo. Rechazado -- "no parece un dashboard real...
   no hay gráficos ni métricas".
2. Segundo intento: grilla de tarjetas 2-3 columnas con gráfico de
   barras + KPI total, patrón de lectura en F (justificado como mejor
   ajuste para contenido informativo denso repetido). Rechazado --
   "no aplicaste el patrón Z... no hay KPIs" (el usuario quería Z, no
   F, y 4 tarjetas KPI explícitas, no un solo total).
3. Tercer intento (el que quedó): el usuario adjuntó 2 capturas de
   referencia de otro proyecto (dashboard de flota tipo "UrbanFleet
   TaxiFlow") mostrando el patrón exacto -- 4 tarjetas KPI arriba, 2
   columnas debajo (gráfico con badge de origen a la izquierda, tabla
   con badge de origen a la derecha). Ese patrón reveló además que el
   badge de la referencia ("Compuesto · ClickHouse" / "Simple ·
   MongoDB") no era decorativo: exigía que el compuesto viniera
   realmente de una capa analítica distinta a la operativa. De ahí
   salió la decisión de construir `aerohub_analytics_api`/ClickHouse
   real en vez de simular el badge sobre datos de MonetDB.

**Verificado tras el tercer pase**: `ruff`/`mypy`/`bandit`/
`import-linter` en verde sobre `services/analytics_api` (contra la
imagen reconstruida del gateway, con `clickhouse-connect` agregado a
`services/analytics_api/pyproject.toml`); `npx nx build web
--configuration=production` en verde (mismo warning de presupuesto de
bundle ya conocido). Contenedor `aerohub-clickhouse` levantado y sano;
`tools/sincronizar_analytics_demo.py` corrido con éxito (6/6 módulos,
confirmado con `SELECT ... FROM ah_tactico_demo.compuesto_informe`
directo contra ClickHouse). Verificado en navegador real (sesión
logueada como `canario@mec.aerohub.test`, `role_tenant_admin`): los 6
módulos renderizan con datos reales, sin errores de consola, badges
"Compuesto · ClickHouse"/"Simple · MonetDB" correctos, grilla en 2
columnas confirmada por estilos computados. `Compliance Hub` sigue
mostrando `acceso denegado` en su lado simple -- mismo hallazgo
pre-existente de S1.7/S1.19 (sin `GRANT` de motor de
`role_tenant_admin` sobre `compliance.*`), no introducido por esta
iteración.

**Sin commitear todavía** -- pendiente de pedido explícito del
usuario, igual que el resto del proyecto (Principio V).

## Iteración post-S1.20: clasificación de roles + corrección transversal de módulos (2026-08-06/07, pendiente de commit)

Trabajo directo del usuario tras cerrar la Fase 1.5, sin ciclo Spec Kit
propio (revisión funcional de la aplicación completa) -- documentado
aquí para que la sesión siguiente retome desde el estado real, no
desde el último commit (`0a23e2d`, S1.20). **Seguir corriendo
`git status`/`git diff` antes de asumir que el árbol coincide con el
último commit.**

1. **Reset completo de las 3 instancias de MonetDB** (primaria,
   standby, restore-test) a pedido del usuario, para poder probar con
   una base limpia. Volúmenes `infra_monetdata{,-standby,-restore-test}`
   borrados y recreados, DDL reaplicado a las 3, seeds corridos solo en
   la primaria, `tools/crear_usuarios_demo_roles.py` re-ejecutado.
   **Hallazgo real corregido**: `db/ddl/monetdb/99_grants_identidad.sql`
   duplicaba un `GRANT SELECT, INSERT, UPDATE ON tenants.invitacion TO
   role_tenant_admin` que `92_grants_tenants.sql` ya otorgaba -- rompía
   `db/migrations/apply.py` contra un motor recién creado con
   `01007!GRANT: ... already has this privilege` (nunca se había vuelto
   a aplicar el DDL completo desde cero desde que ese archivo se creó
   en S1.10). Corregido eliminando el duplicado -- ver también la
   sección de hallazgos empíricos de MonetDB más abajo.
2. **`docs/diseno/ROLES_POR_CAPA.md`** (nuevo): clasifica los 16 roles
   del sistema en capa operativa / táctica / estratégica / plataforma,
   usando la misma taxonomía RF-O/RF-T/RF-E que ya usa
   `docs/PLAN_IMPLEMENTACION_v3.0.md`. El usuario decidió trabajar
   **solo con la capa operativa** (`role_tenant_admin`,
   `role_operations_controller`, `role_ramp_agent`,
   `role_airline_coordinator`, `role_billing_officer`) hasta nuevo
   aviso -- las credenciales demo de esos 5 roles ya existen (tenant
   MEC, `tools/crear_usuarios_demo_roles.py`).
3. **`docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md`** (nuevo, **plan sin
   implementar**): reemplaza el dashboard único módulo-céntrico actual
   (que mezcla compuesto/ClickHouse con simple/MonetDB) por un
   dashboard **por rol operativo**, alimentado solo por informes
   simples de MonetDB -- un compuesto es horizonte táctico, no le sirve
   a quien opera el día de hoy. Documenta 2 brechas reales (M2 FIDS y
   M6 Passenger sin endpoint de informe) y 5 decisiones abiertas con
   recomendación por defecto. **No implementado** -- a la espera de que
   el usuario lo pida.
4. **`docs/diseno/PLAN_CORRECCION_MODULOS.md`** (nuevo): revisión
   funcional de toda la aplicación (CRUD, errores HTTP, comprensibilidad).
   Encontró que la mayoría de los "errores de servidor" reportados se
   explican por **4 causas raíz**, no por decenas de defectos sueltos:
   (A) `role_tenant_admin` tenía scopes de aplicación de escritura
   (`vuelos:escribir`/`puertas:escribir`/`rampa:escribir`/`billing:escribir`)
   que el motor nunca le concedió (la matriz de roles los reserva a
   los roles operativos reales) -- 500 opaco al escribir; (B) el
   traductor de errores de permisos (`_manejador_acceso_denegado_motor`)
   solo reconocía la frase de MonetDB para `SELECT` denegado
   (`"access denied"`), no la de `INSERT`/`UPDATE`/`DELETE` denegado
   (`"insufficient privileges"`) -- una escritura sin permiso llegaba
   como 500 en vez de 403; (C) los seeds no siembran datos operativos
   (terminales, puertas, turnarounds, facturas, pantallas FIDS,
   artículos de KB) -- módulos vacíos tras cualquier reset; (D) M1 AODB
   no tiene `GET /vuelos` (405) -- la vista núcleo no puede listar nada
   al entrar. También aclara 2 cosas reportadas como bug que son reglas
   de negocio reales sin explicar en la UI: el límite de 3 caracteres
   en moneda de tarifario (ISO 4217, correcto, falta ser un selector) y
   que un ticket de soporte solo cambia de estado si lo opera
   `role_support` (regla de S1.8, el control se ocultaba sin decir por
   qué). El plan deja **D1** (qué hacer con los scopes de
   `role_tenant_admin`) como la decisión que condiciona todo lo demás,
   con 4 más de menor impacto.

   **D1(a) decidido por el usuario -- respetar la matriz de roles.**
   **Fase 1 implementada y verificada**:
   - `services/gateway/main.py::_manejador_acceso_denegado_motor`
     reconoce ahora `"insufficient privileges"` además de
     `"access denied"` -- cualquier escritura sin `GRANT` de motor
     responde 403 legible, nunca 500.
   - `packages/contracts/aerohub_contracts/roles_modulos.py`:
     `role_tenant_admin` perdió `vuelos:escribir`/`puertas:escribir`/
     `rampa:escribir`/`billing:escribir` -- es "configuración", no
     "operación", según la matriz del Análisis v6.0 §4.3.1. **Ajuste
     acordado explícitamente con el usuario**: esto rompe también el
     botón "Cancelar" de `puertas/tablero-puertas` (una acción que hoy
     SÍ funcionaba, por ser un `UPDATE` que el motor sí permite) --
     aceptado a propósito ("cancelar una asignación también es
     operar"), en vez de partir el scope en dos más finos.
   - `tests/negative/test_escritura_permisos_motor.py` (nuevo, 6
     tests): confirma que ninguna escritura llega a 500, que
     `role_tenant_admin` ya no puede escribir en M1/M3/M4/M5, y que
     `role_operations_controller`/`role_billing_officer` siguen
     pudiendo (sin regresión). Verificado: ruff/mypy/bandit/
     import-linter en verde; suite completa **184 tests, 0 fallos**
     (excluidos 6 tests con dependencia externa ya conocida y ajena a
     este cambio: 3 de `test_continuidad_shipper.py` con un problema de
     hostname de conexión pre-existente, y 3 que dependían de
     `mailpit`, retirado del stack en la sexta iteración post-S1.13).
   - **Botones de escritura ocultos en el frontend** para
     `role_tenant_admin` en los 4 módulos afectados -- nuevo computed
     `puedeEscribir()` (mismo patrón ya usado en `panel-compliance`/
     `panel-soporte`) en `vuelos/estado-tiempo-real` ("Nuevo vuelo",
     "Cambiar estado"), `puertas/tablero-puertas` ("Asignar puerta
     manualmente", "Ejecutar asignación automática", "Cancelar"),
     `rampa/panel-turnaround` ("Crear turnaround", "Iniciar tarea",
     "Finalizar") y `billing/panel-facturas` +
     `billing/panel-tarifarios` ("Calcular facturación", "Emitir
     factura", "Disputar factura", "Nuevo tarifario", "Agregar
     concepto", "Activar", "Nueva conciliación", "Conciliar"). Primitivo
     `.accion-inactiva` local de `tablero-puertas` promovido a
     `.ah-accion-inactiva` en `_primitivos.scss` (el mismo patrón se
     repite en los 5 módulos). **Hallazgo del proceso**: copiar
     `roles_modulos.py` al contenedor con `docker cp` no alcanza para
     que la API lo tome -- el proceso `uvicorn` ya lo tenía cargado en
     memoria, hace falta `docker restart aerohub-gateway`. Verificado
     en navegador real: `role_tenant_admin` ya no ve ningún control de
     escritura en los 4 módulos; `role_operations_controller` sigue
     viendo "Nuevo vuelo" sin regresión; build de producción en verde.
   - **Fases 2-6 del plan (sembrar datos, cerrar huecos de API,
     estandarizar CRUD, comprensibilidad) siguen sin implementar** --
     retomar ahí cuando el usuario lo pida.

**Fase 2 implementada** (2026-08-07, pendiente de commit): `db/seeds/generate.py`
ampliado con siembra operativa idempotente por tenant canario (MEC/UIO) --
1 terminal + 3 puertas (2 contacto/1 remota), 1 plantilla FIDS + 2 pantallas
(en_linea/sin_senal), un segundo vuelo (sentido `L`) emparejado con el
existente (sentido `S`) en 1 turnaround `en_curso` con 2 tareas (completada/
en_curso) y 1 incidencia, 1 tarifario vigente con 3 conceptos + 1 cargo
aeronautico + 3 facturas en 3 estados (borrador/emitida/vencida) -- y, fuera
del loop por tenant (estas 2 tablas no tienen `tenant_id`), 2 articulos de
KB con etiquetas y 1 entrada de changelog con 2 items. Cada helper nuevo
sigue el patron `_obtener_o_crear_X` ya establecido en el archivo (lookup
por la clave UNIQUE real de cada tabla antes de insertar) -- confirmado
idempotente corriendo el script dos veces seguidas sin duplicar filas.
**Hallazgo de bug real durante la escritura** (no de MonetDB, de copiar mal
los codigos del propio archivo): los primeros borradores de las tareas de
turnaround e incidencia usaban codigos que no existen en `TIPOS_TAREA`
(`"desembarque"`, `"reabastecimiento_combustible"`) ni en
`TIPOS_INCIDENCIA_RAMPA` (`"dano_equipo"`) -- los unicos reales son
`"combustible"/"catering"/"limpieza"/"equipaje"` y
`"desviacion_estandar"` (unica entrada del catalogo); corregido antes de
correr el script contra MonetDB real. Verificado: sintaxis (`ast.parse`),
`ruff`/`mypy`/`bandit` en verde sobre `db/seeds/generate.py` (6 errores de
longitud de linea E501 corregidos), `lint-imports` en verde sobre el repo
completo (no rompe ningun contrato); corrida real contra `monetdb`
primario dentro de `aerohub-gateway` sin errores, dos veces seguidas
(prueba de idempotencia); conteos de filas confirmados por tenant via
`pymonetdb` directo. **Verificado en navegador real** (`canario@mec.aerohub.test`,
`role_tenant_admin`): Terminal & Gate Manager, Ground Operations, Revenue &
Billing, FIDS Management y Soporte (KB + changelog) ya muestran datos --
ningun modulo operativo se abre vacio. Un 500 transitorio visto una vez en
`GET /support/kb/articulos` ("connection closed" en el pool de SQLAlchemy/
MonetDB, ver traceback en logs de `aerohub-gateway`) se confirmo como
artefacto de una conexion inactiva del pool, no una regresion -- 3
reintentos consecutivos por `curl` devolvieron 200 con los 2 articulos
sembrados incluidos, y una recarga de la vista los mostro correctamente.
**Fase 3 implementada** (2026-08-07, pendiente de commit): cierra los 3
huecos de API identificados en el plan (items 6-9).

1. **`GET /vuelos` con filtros de fecha y estado** (item 6, causa raiz D):
   `aerohub_aodb` no tenia ningun listado -- la vista nucleo solo recibia
   datos por WebSocket. `infrastructure/consultas.py::listar_vuelos` hace
   `LEFT JOIN` contra el estado mas reciente (mismo patron de subconsulta
   correlacionada `MAX(registrado_en)` que `obtener_estado_vuelo_actual_por_id`,
   nunca contra `ops.v_vuelo_estado_actual` por el hallazgo ya documentado
   de columnas a 3 partes en vistas). **Hallazgo empirico nuevo**: el
   guardian G2 (`packages/repository/guard.py::_tiene_filtro_tenant`) solo
   inspecciona la clausula `WHERE` de un `SELECT`, no las condiciones `ON`
   de un `JOIN` -- un filtro de tenant puesto solo en el `ON` del
   `outerjoin` contra `vuelo_estado` no alcanza, hace falta repetirlo en
   `WHERE` (`(vuelo_estado.c.tenant_id == tenant_id) | (vuelo_estado.c.tenant_id.is_(None))`,
   el `OR` con `NULL` preserva la semantica del `LEFT JOIN` para vuelos sin
   ningun estado registrado). Nuevo caso de uso
   `aerohub_aodb/application/listar_vuelos.py` y endpoint `GET /vuelos`.
2. **CRUD de terminal y puerta en M3** (item 7): antes de este sprint no
   existia ningun alta/edicion, solo el tablero de solo lectura y el flujo
   de asignacion. Nuevo `domain/puerta.py` (`validar_terminal`/
   `validar_puerta`, mismos 2 valores del CHECK de motor para `tipo`),
   nuevo caso de uso `application/gestionar_puertas.py`
   (`crear_terminal`/`listar_terminales_del_tenant`/`crear_puerta`/
   `actualizar_puerta`, con deteccion de codigo duplicado -> 409 antes del
   INSERT, mismo patron que `CorreoYaRegistrado` en tenancy), y 4
   endpoints nuevos (`POST/GET /puertas/terminales`, `POST /puertas`,
   `PATCH /puertas/{id}`). Sin `estado` en el DDL de `ops.puerta`/
   `ops.terminal` -- no hay accion de suspender/activar para estas 2
   tablas, el CRUD real es crear+editar. **Sin cambio de GRANT
   necesario**: `role_operations_controller`/`role_airline_coordinator`
   ya tenian `INSERT`/`UPDATE` de motor sobre ambas tablas desde
   `96_grants_ops.sql` (S1.4), verificado antes de escribir codigo.
3. **Trazabilidad de transiciones de ticket** (item 8, D6): el dato ya se
   registraba desde S1.8 (`cambiar_estado_ticket` -> `registrar_auditoria`
   -> `compliance.log_auditoria`), pero no habia ningun GRANT de motor que
   permitiera leerlo desde un rol operativo (solo roles de plataforma).
   **Decision explicita del usuario** (`AskUserQuestion`, opcion
   recomendada): otorgar `GRANT SELECT ON compliance.log_auditoria` a los
   2 roles que hoy tienen el scope de aplicacion `support:leer` fuera de
   los roles de plataforma ya otorgados (`role_tenant_admin`,
   `role_support`) -- no a los 5 roles operativos que carecen de ese
   scope. La consulta (`listar_transiciones_estado_ticket`) siempre filtra
   por `esquema='support' AND tabla='ticket' AND registro_id=<ticket
   puntual>`; el GRANT es table-wide (MonetDB no tiene seguridad de fila)
   pero la aplicacion nunca ejecuta nada mas amplio contra esa tabla.
   Nuevo `consultar_transiciones_ticket` en `gestionar_tickets.py` (mismo
   patron de 2 ramas que `consultar_ticket`: `role_support` ve
   transiciones de cualquier tenant via `alcance_global`, el resto solo
   las de su propio tenant) y endpoint
   `GET /support/tickets/{id}/transiciones`. **Verificado empiricamente
   que seleccionar columnas JSON individuales** (`valores_anteriores`/
   `valores_nuevos`) **no dispara el hallazgo de doble-decodificacion de
   S1.9/S1.18** -- ese bug es especifico de `select(tabla_completa)`, no
   de seleccionar columnas JSON puntuales junto a otras escalares.
4. **`docs/api/openapi.yaml` regenerado** (item 9): pasa de 72 a 97 rutas.
   `npx spectral lint --fail-severity=error` en verde (0 errores, 66
   warnings preexistentes de descripciones faltantes en todo el archivo,
   no introducidos por este sprint).
5. **Verificado**: ruff/mypy/bandit/import-linter en verde sobre
   `aerohub_aodb`/`aerohub_gates`/`aerohub_support` (un hallazgo de
   `UP017` preexistente en `aerohub_gates/infrastructure/consultas_informe.py`,
   archivo no tocado por este sprint, dejado intacto). Probado uno por uno
   con `curl`+JWT real contra los 3 roles relevantes (`role_tenant_admin`,
   `role_operations_controller`, `role_support`): `GET /vuelos` con y sin
   filtros, ciclo completo crear-terminal/crear-puerta/editar-puerta,
   duplicado -> 409, tipo invalido -> 422, sin scope -> 403, ciclo
   cambiar-estado-ticket + `GET .../transiciones` con el detalle correcto
   de estado anterior/nuevo. Nuevo `tests/integration/test_fase3_cierre_huecos_api.py`
   (10 tests contra MonetDB real via `TestClient`, confirmado idempotente
   en 2 corridas seguidas). Suite completa: **211 tests pasando** (187
   previos + 10 nuevos + 16 de una suite de aislamiento re-verificada
   aparte + 1 test de latencia RNF-P01, ver hallazgo de entorno abajo),
   los 6 fallos ya documentados de `mailpit`/`test_continuidad_shipper.py`
   sin cambios. **Hallazgo de entorno nuevo** (no de codigo): correr la
   suite COMPLETA de una sola vez agota el limite de 64 conexiones
   concurrentes de MonetDB hacia el final de la corrida -- en aislamiento
   cada test afectado pasa sin problema; es presion de recursos del
   entorno de este sprint (300+ tests + 2 subprocesos `uvicorn` reales de
   los tests de latencia RNF-P01/RNF-P02, que ademas tardan >10s en
   terminar en `proceso.wait()` durante el teardown, sin afectar el
   resultado del test en si -- ambos "pasan" y solo el teardown erroa),
   no una regresion introducida por este sprint.

**Fase 4 implementada parcialmente** (2026-08-07, pendiente de commit):
items 10 y 12 completos; item 11 avanzado en los 2 módulos con el hueco
más grande (M3 Gates, M5 Billing/tarifarios) -- M1 AODB, M2 FIDS, D6 y M9
quedan pendientes.

1. **Item 10 -- borrado físico retirado de `tenant-list`**: se quitó el
   botón "Borrar físicamente", su modal de confirmación y los métodos
   `solicitarEliminacionFisica`/`confirmarEliminacionFisica`/
   `cancelarEliminacionFisica` (+ signals `tenantAEliminar`/`eliminando`)
   de `tenant-list.ts`, y `eliminarTenantFisico()` de `tenant.service.ts`
   (sin otro consumidor). **Decisión D2(b)** (recomendación por defecto
   del plan, no se volvió a preguntar): el endpoint `DELETE /tenants/{id}`
   del backend se deja intacto, sin consumidor de interfaz.
2. **Item 12 -- Licencias y API Keys**: `licencia-list` gana "Ver
   detalles" (módulo, vigencia, estado, y un origen textual -- no existe
   columna `origen` en `tenants.licencia`, se explica que la licencia la
   otorga el aprovisionamiento del tenant según su plan, sin edición
   posible, tal como ya documentaba §5 del plan). `api-key-list` mueve
   "Rotar"/"Revocar" de botones de fila a un modal "Ver detalles" (sin
   edición -- una llave no se edita).
3. **Item 11 -- M3 Gates**: UI completa para el CRUD de terminal/puerta
   que Fase 3 dejó sin ningún consumidor. `puertas.service.ts` gana
   `listarTerminales`/`crearTerminal`/`crearPuerta`/`editarPuerta`.
   `tablero-puertas` gana botones "Nueva terminal"/"Nueva puerta"
   (condicionados a `puedeEscribir()`), y el botón de fila pasa de "Ver
   asignaciones" (solo si había alguna) a "Ver detalles" siempre visible
   -- el modal ahora muestra terminal/tipo/envergadura/pasarela de la
   puerta, un botón "Editar" que abre un formulario inline dentro del
   mismo modal (patrón "las acciones viven dentro de Ver detalles"), y
   debajo la tabla de asignaciones ya existente. **Hallazgo de API
   durante la implementación**: `PuertaTableroResponse`/`PuertaTablero`
   de `aerohub_gates` no exponían `tiene_pasarela` -- sin ese campo no
   se podía prellenar el formulario de edición correctamente; se agregó
   como campo aditivo (la fila ya lo traía de `listar_puertas`, solo
   faltaba propagarlo por `application`/`api`).
4. **Item 11 -- M5 Billing/tarifarios**: consolidados "Ver conceptos" +
   "Agregar concepto" + "Activar" (3 botones de fila) en un solo "Ver
   detalles" -- el modal de conceptos ahora es el contenedor de las 2
   acciones propias del tarifario, que se abren cerrando primero el modal
   de detalles (mismo criterio que `tenant-list`: nunca dos modales
   superpuestos).
5. **Verificado**: build de producción de `apps/web` en verde (mismo
   warning de presupuesto de bundle ya conocido, ahora 700KB); ruff/mypy
   en verde sobre `aerohub_gates` (un `E501` propio de Fase 3 que se
   había colado sin corregir, encontrado y arreglado recién ahora);
   22/22 tests de integración relacionados (gates/tarifarios/Fase 3) sin
   regresiones. **Verificado en navegador real**
   (`controlador@mec.aerohub.test`, `role_operations_controller`): ciclo
   completo crear terminal → crear puerta → ver detalles → editar → el
   cambio se refleja en la tabla, confirmado por red (`POST
   /puertas/terminales` 201, `POST /puertas` 201, `PATCH /puertas/{id}`
   204) y por el DOM. `licencia-list`/`api-key-list` verificados con
   `canario@mec.aerohub.test` (`role_tenant_admin`): "Ver detalles"
   muestra el contenido esperado en ambos. Un 500 en
   `GET /vuelos/catalogo/tipos-vuelo` visto una vez en consola se
   reconfirmó como el mismo artefacto transitorio de conexión ya
   documentado en esta sesión (3/3 reintentos con `curl` dieron 200
   inmediatamente después).
6. **Item 11 -- resto cerrado en la misma sesión** (M1 AODB, M2 FIDS, D6
   Soporte, M9 Compliance):
   - **M1 AODB**: el botón "Cambiar estado" por fila se reemplaza por
     "Ver detalles" (siempre visible, ya no requiere `puedeEscribir()`) --
     abre un modal con `GET /vuelos/{id}` (aerolínea/aeronave/ruta/fecha/
     horarios/pax, resueltos a nombre real via los catálogos ya cargados)
     y el cambio de estado vive DENTRO como formulario nested, solo si
     `puedeEscribir()`. `vueloEditandoEstadoId` se retira, reemplazado por
     `vueloDetalle: VueloConsultado | null`.
   - **M2 FIDS**: plantillas ganan "Ver detalles" (inmutable/versionada,
     sin edición) mostrando el contenido real (`definicion_json`) que
     antes solo se veía al crearla -- el campo ya viajaba en la respuesta
     de `GET /plantillas`, solo no se mostraba. El botón de pantalla pasa
     de "Asignar plantilla" a "Ver detalles": el modal ahora muestra
     terminal/plantilla vigente/ubicación/última señal, con "Asignar otra
     plantilla" como acción nested (mismo formulario de antes, sin
     endpoint nuevo).
   - **D6 Soporte**: el modal de detalle de ticket gana una sección
     "Historial de estado" que consume
     `GET /support/tickets/{id}/transiciones` (cerrado en Fase 3, sin
     consumidor hasta ahora) -- lista simple (no aún un timeline fusionado
     con los mensajes; eso es explícitamente Fase 5 item 16). Nuevo tipo
     `Transicion` + `listarTransicionesTicket()` en `soporte.service.ts`.
   - **M9 Compliance**: revisado, **sin cambios** -- post-mortem ya tenía
     el ciclo completo crear/ver-detalles/publicar desde su propio sprint;
     incidentes/reportes DGAC/accesos de auditor/evidencia SOC2 son
     registros de auditoría deliberadamente inmutables (verificado contra
     el backend: `IncidenteTablero` no tiene ningún campo que la tabla ya
     no muestre, y no existe ninguna función de actualización de
     `incidente_seguridad` en `application/`) -- un "Ver detalles" ahí
     sería ruido sin información nueva, no aplica el patrón.
   - `tenant-list`/`usuario-list`/M4 Ground Ops ya cumplían el patrón
     desde sprints anteriores, sin cambios necesarios. **Item 11 completo
     en los 9 módulos.**
   - **Verificado**: build de producción de `apps/web` en verde (mismo
     warning de bundle, 706KB); 30/30 tests de integración relacionados
     (aodb/fids/soporte/Fase 3) sin regresiones. Verificado en navegador
     real (`canario@mec.aerohub.test` para lectura, un JWT de
     `role_operations_controller` fabricado por `curl` para generar
     eventos de cambio de estado reales): el detalle de vuelo resuelve
     nombres de aerolínea/aeronave/aeropuertos correctamente tras un
     cambio de estado real vía WebSocket; el detalle de plantilla FIDS
     muestra el contenido real; el detalle de pantalla FIDS muestra
     terminal/plantilla/ubicación y permite reasignar; el historial de
     estado de un ticket muestra "Abierto → En progreso · role_support"
     con la marca de tiempo correcta.
   - **Hallazgo de entorno, no de código, encontrado varias veces
     verificando este pase**: `GET /vuelos/catalogo/aeropuertos` (y otros
     endpoints de catálogo, ya visto antes con `/support/kb/articulos` y
     `/vuelos/catalogo/tipos-vuelo`) devuelve intermitentemente 500
     `pymonetdb.exceptions.Error: connection closed` tras un período de
     inactividad. Siempre se resuelve solo en el siguiente intento
     (confirmado repetidas veces con reintentos inmediatos). **No es una
     regresión de ningún sprint** -- es comportamiento pre-existente del
     pool de conexiones, reproducido en múltiples endpoints no
     relacionados entre sí a lo largo de toda la sesión.
     **Corrección (Fase 5, 2026-08-07)**: la nota original de esta
     entrada decía que faltaba `pool_pre_ping` y que el arreglo era de
     una línea -- **incorrecto**, no se leyó `base.py` antes de
     escribirlo. `obtener_engine()` (`packages/repository/aerohub_repository/base.py`)
     ya tiene `pool_pre_ping=True` **y** `pool_recycle=180` desde el
     2026-08-05, con un comentario que documenta exactamente este
     síntoma: el pre-ping de SQLAlchemy no alcanza a detectar un socket
     que MonetDB cerró del lado del servidor (el `assert self.sock` de
     `pymonetdb/mapi.py` salta recién al ejecutar la consulta real, no
     durante el ping), por lo que `pool_recycle` es la mitigación real
     (descarta conexiones viejas proactivamente) y ya está aplicada. Lo
     que queda es un residuo de esa misma clase de fallo, ya mitigado
     tanto como el pool de SQLAlchemy razonablemente permite -- no hay
     una corrección de una línea pendiente. Verificado de nuevo en vivo
     en Fase 5: `GET /rampa/incidencias` lo reprodujo 2 veces seguidas
     tras un `docker restart aerohub-gateway`, resuelto en el tercer
     intento.

**Fase 5 implementada** (2026-08-07, pendiente de commit): comprensibilidad
(items 13-17), usando el skill `frontend-design` y `docs/diseno/DIRECCION_VISUAL.md`
como referencia obligatoria -- ningún token/patrón nuevo, solo aplicación
del sistema ya existente (`.ah-punto`, semáforo de 4 tonos, `.ah-vacio`).

1. **Item 14 -- indicador de conexión en AODB**: `vuelos/estado-tiempo-real`
   se conecta sola al entrar (ya no hay botones "Conectar"/"Desconectar")
   y se reconecta sola cada 3s si se cae (salvo cierre por sesión inválida,
   código ≥4000, que sigue llevando a `/login`). El indicador es de solo
   lectura: `.ah-punto` verde "En vivo" / ámbar "Reconectando…" / rojo
   "Sin conexión".
2. **Item 13 -- línea de apertura + KPI** en M1, M3, M4, M5 (facturas) y
   D6: una oración que dice qué resuelve el módulo, más un conteo en vivo
   sobre los datos ya cargados (sin pedir nada nuevo al backend) --
   eventos en estado crítico (M1), puertas con solapamiento (M3),
   turnarounds con desviación (M4), facturas vencidas/disputadas (M5),
   tickets con SLA vencido (D6).
3. **Item 15 -- selectores en Billing**: moneda pasa de texto libre (3
   letras) a un `<select>` curado de monedas reales para el contexto de
   la app (`MONEDAS_COMUNES` en `panel-tarifarios.ts`, no el catálogo ISO
   4217 completo). El id de vuelo en "Nueva conciliación" pasa a un
   `<select>` poblado por `GET /vuelos` (cerrado en Fase 3, sin frontend
   hasta ahora) -- la tabla de conciliaciones también resuelve
   `numeroVueloDe()` en vez de mostrar el id crudo. **Decisión explícita
   del usuario** (`AskUserQuestion`): agregar `vuelos:leer` a
   `role_billing_officer` en vez de mantener el campo de texto -- tiene
   sentido de dominio (quien concilia pax necesita ver qué vuelos
   existen). Reveló un GRANT de motor faltante: `ops.vuelo` ya tenía
   SELECT para este rol desde S1.6, pero `ops.vuelo_estado` no (lo
   necesita el `LEFT JOIN` de `GET /vuelos`) -- agregado en
   `96_grants_ops.sql`.
4. **Item 16 -- Soporte**: la KB se enlaza desde el ticket -- al abrir el
   detalle, se buscan artículos por `etiqueta = categoria.codigo.toLowerCase()`
   (sin relación formal en el backend entre categoría de ticket y
   etiqueta de artículo; es una sugerencia por vocabulario compartido, no
   un vínculo garantizado). Además, "Conversación" e "Historial de
   estado" (2 listas separadas desde Fase 4) se fusionan en una sola
   **línea de tiempo** cronológica (`lineaTiempo` computed, mensajes +
   transiciones intercalados por fecha) -- resuelve la ejecución
   completa del pedido original del plan ("línea de tiempo del ticket y
   KB enlazada"), no solo la mitad que había quedado en Fase 4.
5. **Item 17 -- estados vacíos con CTA**: en M1, M3, M4 (turnarounds), M5
   y D6 (tickets/KB/changelog), el texto "sin X todavía" ahora explica
   qué va a pasar o incluye un botón hacia la acción de creación
   correspondiente, condicionado a `puedeEscribir()` donde aplica.
   Incidencias (M4) no lleva CTA -- se generan solas, no hay alta manual.
6. **Hallazgo corregido de una nota anterior**: la entrada de Fase 4 de
   este mismo documento decía que faltaba `pool_pre_ping` en el pool de
   conexiones y que el arreglo era de una línea -- **era incorrecto**, no
   se había leído `packages/repository/aerohub_repository/base.py` antes
   de escribirlo. Ese archivo ya tiene `pool_pre_ping=True` y
   `pool_recycle=180` desde el 2026-08-05, con el hallazgo empírico ya
   documentado in situ. Corregido en la entrada original (ver arriba,
   dentro de la sección de Fase 4) para no dejar un dato falso en el
   historial.
7. **Verificado**: build de producción de `apps/web` en verde (716KB,
   mismo warning de bundle); ruff/mypy en verde sobre
   `roles_modulos.py`/`aerohub_aodb`; 95/95 tests de integración
   relacionados (billing/Fase 3/negativos) sin regresiones. Verificado
   en navegador real: AODB se conecta y reconecta sola, KPI se
   actualiza en vivo tras un cambio de estado real vía WebSocket
   (confirmado "1 evento reciente, 1 en estado crítico"); selector de
   moneda y de vuelo poblados correctamente bajo `role_billing_officer`
   real (login real, no JWT fabricado); línea de tiempo de ticket
   intercala mensaje (18:09) y transición (21:04) en el orden correcto;
   artículos relacionados aparecen para un ticket de categoría AODB (7
   coincidencias reales). Los 500 transitorios vistos durante la
   verificación (`/rampa/incidencias`, `/support/changelog`) son el
   mismo hallazgo de conexión ya documentado, no regresiones -- se
   resolvieron solos en el siguiente intento.

**Pendiente**: item 13/17 en M2 FIDS, M9 Compliance, Tenants/Usuarios/
API-Keys/Licencias (no se tocaron en este pase, la Fase 5 se acotó a los
5 módulos de la capa operativa igual que las Fases 1-4).

**Fase 6 implementada** (2026-08-07, pendiente de commit): verificación
final -- cierra `docs/diseno/PLAN_CORRECCION_MODULOS.md` completo
(Fases 1-6).

1. **Item 19 -- compuertas de calidad**: `ruff check .`/`mypy services
   packages`/`bandit -r services packages`/`lint-imports` en verde sobre
   el repo completo (no solo los módulos tocados). Encontró un error
   real propio: el import de `listar_vuelos` en
   `aerohub_aodb/application/__init__.py` (agregado en Fase 3) quedó
   fuera de orden alfabético -- corregido con `ruff check --fix`. El
   resto de hallazgos de `ruff` (15) son deuda preexistente en archivos
   no tocados en toda esta iteración (`tools/crear_usuarios_demo_roles.py`,
   `test_fids_administracion.py`, `test_aodb_catalogos.py`,
   `router_auth.py`, `consultas_informe.py` de gates, y varios
   `__init__.py` con imports sin ordenar) -- se dejan intactos, mismo
   criterio que el resto de la iteración. Suite completa:
   **197 tests pasando** (0 fallos reales; los 2 errores de teardown de
   `test_pn06_pn07_rnf_p01.py`/`test_fids_pn11_...` ya documentados como
   ambientales siguen igual). Build de producción de `apps/web` en verde.
2. **Item 18 -- recorrido con los 5 roles operativos reales** (login real
   por credencial, no JWT fabricado, con logout entre cada uno):
   - `role_operations_controller` (`controlador@`): M1 (conectado en
     vivo, "Nuevo vuelo" visible), M3 (68 puertas), M4 (43 turnarounds,
     1 con desviación, incidencias) -- sin 500 no explicados.
   - `role_ramp_agent` (`rampa@`): M4 con "Crear turnaround" visible
     (tiene `rampa:escribir`) -- correcto.
   - `role_airline_coordinator` (`aerolinea@`): M1 sin botón de
     escritura (no tiene `vuelos:escribir`) -- correcto, ningún error.
   - `role_billing_officer` (`facturacion@`): M5 facturas (35 facturas,
     9 vencidas/disputadas) con "Calcular facturación" visible --
     correcto.
   - `role_tenant_admin` (`canario@`): recorrido completo de
     Usuarios/API Keys/Licencias/FIDS/Tarifarios/Compliance/Soporte/
     Puertas/Informes -- sin escritura visible en M1/M3/M4/M5 (Fase 1),
     "acceso denegado" en Compliance (hallazgo pre-existente S1.7/S1.19,
     no una regresión), un único 500 transitorio en
     `GET /fids/pantallas` resuelto en el reintento inmediato (mismo
     patrón de conexión ya documentado). **Hallazgo de navegación**:
     navegar a `/tenants` con este rol (que no administra tenants) forzó
     un logout -- comportamiento correcto del `authInterceptor` ante un
     403 por scope insuficiente, no un bug.
3. **Corrección de un dato falso dejado en la entrada de Fase 5**: ver
   arriba, dentro de esa misma sección -- la nota sobre `pool_pre_ping`
   faltante era incorrecta y ya fue corregida in situ, no se repite acá.
4. **Item 20 -- documentación actualizada**: `CLAUDE.md` (esta entrada) y
   `docs/diseno/WORKPANEL_Y_DASHBOARD_ROLES.md`, que había quedado
   desactualizado desde el 2026-08-05 -- no reflejaba que
   `role_tenant_admin` perdió escritura en M1/M3/M4/M5 (Fase 1), ni los
   cambios de UI de Fases 4-5 (API Keys/Licencias con "Ver detalles",
   AODB con indicador de conexión, FIDS con detalle de plantilla,
   Gates con CRUD de terminal/puerta, Tarifarios con selectores,
   Soporte con línea de tiempo unificada). Reescrita la sección 1.2
   completa (workpanels de `role_tenant_admin`) y el resumen visual
   final para reflejar el estado real verificado en este mismo pase.

**`docs/diseno/PLAN_CORRECCION_MODULOS.md` queda cerrado en sus 6 fases**
(items 13/17 de M2 FIDS/M9 Compliance/Tenants/Usuarios/API-Keys/Licencias
explícitamente fuera de alcance por decisión de acotar a la capa
operativa, no un pendiente olvidado).

## Checklist de corrección de módulos -- guardado como referencia permanente

A pedido explícito del usuario (2026-08-07): las lecciones de
`docs/diseno/PLAN_CORRECCION_MODULOS.md` quedan guardadas como checklist
reutilizable para no repetir los mismos errores al corregir o construir
**cualquier otro módulo** en el futuro, no solo los que este plan tocó.
Ver la sección **"Checklist de corrección de módulos"** más abajo en
este mismo archivo (las 4 causas raíz A-D, el estándar de CRUD
unificado, y los 4 chequeos previos a reportar un módulo como
"corregido") -- escrita para leerse **antes** de tocar un módulo nuevo,
no solo como registro histórico de lo ya hecho.

## `docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md` implementado (2026-08-07)

A pedido explícito del usuario, se implementó completo con las
decisiones **recomendadas por defecto** (D1(a), D2(a), D3(a), D4(a),
D5(a) -- el usuario pidió "iniciar la implementación" sin especificar
otra cosa, y el propio plan documenta esas 5 como su recomendación si no
se indica lo contrario).

1. **Cambio de mecanismo**: `apps/web/src/app/informes/dashboard-informes/`
   dejó de armar una sección por cada módulo cuyo scope el perfil tuviera
   (barrido genérico, con lado "Compuesto · ClickHouse" + lado
   "Simple · MonetDB" por sección) y ahora resuelve una **config fija por
   `rol_codigo`** (`DASHBOARDS_POR_ROL` en
   `apps/web/src/app/informes/informes-config.ts`): cada rol responde
   **una pregunta de jornada concreta** con KPI derivados en el cliente
   sobre los informes simples ya cargados -- nunca una llamada a
   `GET /analytics/tactico/*`. Período por defecto: **hoy** (no "últimos
   30 días" como antes), con atajos Hoy/24h/Esta semana.
2. **D4(a) -- la infraestructura de ClickHouse queda intacta y sin
   consumidor**: `aerohub_analytics_api`, `tools/sincronizar_analytics_demo.py`,
   `GET /<módulo>/informes/compuesto` y `GET /analytics/tactico/*` no se
   tocaron -- quedan reservados para el dashboard táctico real de la Fase
   2/S2.4 (`ah_tactico`, ADR-016). `InformeService.obtenerInformeTactico`/
   `InformeCompuesto`/`InformeTactico` siguen en el servicio, sin
   consumidor del lado operativo.
3. **Regresión aceptada explícitamente por el propio plan** (su tabla de
   alcance ya decía "las capas táctica/estratégica/plataforma quedan
   fuera hasta nuevo aviso"): `role_business_viewer`, `role_tenant_analyst`,
   `role_regulatory_auditor` y `role_sre` **perdieron el enlace
   "Dashboard"** -- antes veían fragmentos del dashboard viejo por scope
   suelto, ahora no tienen entrada en `DASHBOARDS_POR_ROL`.
4. **Extensión deliberada más allá del texto literal del plan**:
   `role_platform_admin` (capa de plataforma, tampoco cubierta
   formalmente por el plan) se preservó con una entrada propia en
   `DASHBOARDS_POR_ROL` ("¿Cómo está la base de tenants?", informe de
   Tenants) -- sin esto, el cambio de mecanismo le habría dejado el único
   dashboard que ya tenía funcionando vacío de la nada, una regresión
   silenciosa que el plan no pedía y que no tenía sentido introducir de
   paso.
5. **`shell.ts::puedeVerInformes`** cambió de un OR de 6 scopes sueltos a
   `rol_codigo in DASHBOARDS_POR_ROL` -- una sola fuente de verdad
   compartida con el componente del dashboard, en vez de que el enlace
   del menú repita su propia lista.
6. **Verificado en navegador real con los 5 usuarios operativos** (login
   real, no JWT fabricado) -- cada uno ve su pregunta de jornada, sus
   KPI correctos derivados de datos reales (ej. `role_operations_controller`:
   "23 vuelos, 14 asignaciones, 1 turnaround, 1 no completado";
   `role_airline_coordinator`: "23 vuelos, 0 llegadas, 23 salidas"), y
   sus tablas filtradas al período "Hoy" por defecto. `role_platform_admin`
   verificado por API directa (`GET /tenants/informes/simple` con JWT
   fabricado, ya que no hay credencial demo sembrada para este rol) --
   mismo endpoint que ya usa el resto de roles vía el mismo mecanismo, no
   ameritaba una verificación de navegador aparte. Build de producción
   de `apps/web` en verde (713KB, mismo warning de bundle conocido);
   15/15 tests de integración de informes sin regresiones (backend no
   tocado, solo se confirmó que los endpoints que el dashboard nuevo
   consume siguen intactos).

**Sin commitear todavía** -- pendiente de pedido explícito del
usuario (Principio V).

## `docs/diseno/PLAN_CORRECCION_Y_DASHBOARD_ROLES_RESTANTES.md` -- puntos 1 y 2 implementados (2026-08-07)

Extiende `PLAN_DASHBOARDS_OPERATIVOS.md` y `PLAN_CORRECCION_MODULOS.md` a los
10 roles/módulos que ambos habían dejado fuera a propósito. Antes de
implementar nada se verificó permiso real por rol (scope de aplicación +
`GRANT` de motor, causa raíz A del checklist) -- ver la matriz completa en
el propio documento del plan.

**Hallazgo central**: de los 10 roles restantes, solo `role_sre` y
`role_regulatory_auditor` tienen `GRANT` de motor real sobre algo que un
informe simple ya expone (`compliance.log_auditoria`,
`93_grants_compliance.sql:25/27`). `role_tenant_analyst` y
`role_business_viewer` tienen scope de *aplicación* de lectura sobre
varios módulos, pero la matriz 4.3.1 les niega el `GRANT` de motor a
propósito (`96_grants_ops.sql:26-27`, `97_grants_rampa.sql:8-9`) --
dejados fuera deliberadamente (decisión pendiente entre el usuario:
dejarlos fuera hasta la capa táctica real, o abrirles `GRANT`s que hoy
no tienen, ver §2.2 del plan).

**Punto 1 -- dashboard para `role_sre`/`role_regulatory_auditor`**: 2
entradas nuevas en `DASHBOARDS_POR_ROL`
(`apps/web/src/app/informes/informes-config.ts`), ambas sobre
`CONFIG_INFORME_COMPLIANCE` (que ganó `campoAgrupacion: 'tabla'` --
el log de auditoría no tiene un campo de estado propio, agrupar por
tabla responde la pregunta real de "qué tabla concentra la actividad
auditada"). Sin backend nuevo, sin `GRANT` nuevo -- ambos roles ya
podían leer `GET /compliance/informes/simple`. **Nota de refactor**:
`CONFIG_INFORME_COMPLIANCE` tuvo que moverse antes de `DASHBOARDS_POR_ROL`
en el archivo -- un `const` referenciado antes de su propia declaración
revienta en TDZ al cargar el módulo, no es solo un problema de orden de
lectura.

**Punto 2 -- comprensibilidad (items 13/17 pendientes de Fase 5 de
`PLAN_CORRECCION_MODULOS.md`)**: línea de apertura + KPI en vivo +
estado vacío con CTA, mismo patrón ya aplicado a M1/M3/M4/M5/D6, ahora
en las 4 vistas que habían quedado fuera: `compliance/panel-compliance`
(incidentes abiertos, post-mortems sin publicar), `fids/pantalla-list`
(pantallas sin señal, plantillas sin pantalla asignada),
`tenants/tenant-list` (tenants en onboarding, suspendidos), y
`usuarios/usuario-list` + `api-keys/api-key-list` +
`licencias/licencia-list` (suspendidos/sin rol, activas/por expirar,
vigentes/por vencer -- ventana de 30 días calculada en el cliente sobre
`expira_en`/`activa_hasta` ya cargados).

**Hallazgo propio corregido durante la verificación**: el primer intento
armaba la oración de resumen con `@if` anidados en el template
(`@if (b) { @if (a) {, } ... }`) para insertar una coma solo cuando
había 2 cláusulas -- el whitespace de indentación entre bloques `@if`
se colapsa a un espacio real en el HTML renderizado, dejando
`"24 activas , 8 por expirar"` (espacio de más antes de la coma).
Corregido armando la oración completa como un `computed<string>` en
TypeScript (`resumenLlaves`/`resumenTenants`/`resumenUsuarios`/
`resumenLicencias`/`resumenFids`/`resumenCompliance`) y consumiéndola
como una sola interpolación en el template -- patrón a reusar en
cualquier resumen futuro que una 2+ cláusulas condicionales con coma.

**Hallazgo no relacionado, de proceso**: la contraseña real de
`canario@mec.aerohub.test` (el `role_tenant_admin` canario, sembrado por
`db/seeds/generate.py`) es `canario-dev-password` -- **no**
`aerohub-demo-2026`, que es la contraseña fija que usa
`tools/crear_usuarios_demo_roles.py` para los 6 roles que esa
herramienta crea aparte. Son 2 orígenes de credenciales distintos;
confundirlos da un 401 que parece bloqueo por fuerza bruta pero es
simplemente la contraseña equivocada.

**Verificado**: build de producción de `apps/web` en verde (726KB,
mismo warning de bundle conocido) en 2 corridas (antes y después del
arreglo de la coma). Verificado en navegador real: `auditor@mec.aerohub.test`
(`role_regulatory_auditor`) ve su dashboard de Compliance con gráfico +
KPI + "Ver detalle" sobre 1872 eventos reales, agrupados por tabla;
`canario@mec.aerohub.test` (`role_tenant_admin`) confirma los 6 KPI
nuevos con datos reales ("22 sin rol asignado", "24 activas, 8 por
expirar en 30 días", "6 vigentes", "25 sin señal, 9 plantillas sin
pantalla asignada", "Sin pendientes abiertos"). El `403`/`acceso
denegado` visto en `compliance/panel` con `role_tenant_admin` es el
hallazgo pre-existente ya documentado desde S1.7/S1.19 (sin `GRANT` de
motor de `role_tenant_admin` sobre `compliance.*`), no una regresión.
**Punto 3 del plan (`role_tenant_analyst`/`role_business_viewer`) sigue
en pausa** -- decisión pendiente del usuario entre (a) dejarlos fuera
o (b) abrirles `GRANT`s de motor.

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

## Extensión de la iteración de cabecera a las 3 vistas operativas densas restantes + corrección de título duplicado (2026-08-08, pendiente de commit)

Continuación directa de "Iteración de cabecera y modal en
`usuarios/usuario-list`" (más abajo en este archivo) -- mismo día, dos
pedidos directos del usuario.

**Extensión a Terminal & Gate Manager / Ground Operations / Revenue &
Billing** ("faltan los modulos de terminal y gate, ground operations,
revenie y billing, aplicar el plan o el redsiseño"): el patrón de
cabecera/modal de `docs/diseno/MODAL_Y_WORKPANEL.md` §1.2 (ya propagado a
Usuarios/API Keys/Licencias/FIDS/Soporte/Compliance) se extendió a
`puertas/tablero-puertas`, `rampa/panel-turnaround` y
`billing/panel-facturas` -- las 3 de las 4 vistas operativas densas que
el plan original excluía a propósito que el usuario pidió explícitamente
(`vuelos/estado-tiempo-real` no fue parte del pedido, sigue sin tocar).
Chips KPI condicionales: Rampa ("N turnaround con desviación"), Billing
("N vencidas o disputadas"). Nuevo patrón `.consola__subseccion-cabecera`
en Rampa para "Incidencias" (tabla secundaria con su propio botón de
refresco). **Pregunta del usuario resuelta como comportamiento correcto,
no bug**: por qué Puertas no mostraba un chip KPI como el de Rampa --
confirmado por inspección de datos reales en el navegador
(`puertasEnConflicto` computed evalúa a 0 con los datos sembrados
actuales, el chip condicional correctamente se oculta) -- "dejalo así, no
hace falta forzarlo".

**Hallazgo real corregido -- título duplicado en las 9 vistas**
("hay doble titulo en todos los modos", con captura de "GROUND
OPERATIONS" repetido): el `.consola__eyebrow` agregado por la iteración
de cabecera (y propagado a las 8 vistas siguientes) repetía el mismo
texto que `shell.html` ya renderiza en `.content__ubicacion`
(`tituloVistaActual()`, lee `data.title` de la ruta activa en
`app.routes.ts`, función vigente desde S1.13) -- dos títulos idénticos
apilados. Corregido retirando el elemento `.consola__eyebrow` y su regla
CSS de las 9 vistas (`usuarios`, `api-keys`, `licencias`,
`fids/pantallas`, `soporte/panel`, `compliance/panel`, `puertas/tablero`,
`rampa/turnaround`, `billing/facturas`) -- el shell ya resuelve el nombre
de la vista, ninguna vista necesita repetirlo. Regla para no repetir esto
en una vista futura, documentada en `docs/diseno/MODAL_Y_WORKPANEL.md`
§1.2 punto 1: nunca agregar un eyebrow/título de sección que repita
`data.title` de la ruta. **Verificado en navegador real** tras
`docker cp` + `npx nx build web --configuration=production` (verde) +
`docker restart aerohub-web`: las 9 vistas muestran el título una sola
vez (`controlador@mec.aerohub.test` para Ground Operations,
`canario@mec.aerohub.test` para las 8 restantes), sin errores de consola
nuevos -- el único 500 visto (`/vuelos/catalogo/tipos-vuelo`) y el "error
interno del servidor" de la KB en Soporte son el mismo hallazgo de
conexión de pool ya documentado (se resuelven solos al reintentar), no
una regresión de este cambio; `acceso denegado` en Compliance sigue
siendo el hallazgo pre-existente de S1.7/S1.19.

## Traducción del módulo de administración de tenant al español (2026-08-08, pendiente de commit)

Pedido directo del usuario con captura del menú lateral mostrando
"AODB · FIDS Management · Terminal & Gate Manager · Ground Operations ·
Revenue & Billing" en inglés pese a que el resto de la interfaz ya
está en español -- "falto aqui".

**3 capas distintas tenían el mismo nombre en inglés, había que tocar
las 3 para que no quedara ninguna**:

1. **Strings estáticos de `apps/web`**: `app.routes.ts` (`data.title` de
   cada ruta), los `<h1>` de `api-key-list.html`/`pantalla-list.html`/
   `panel-compliance.html`, los textos "API Key(s)" repetidos en
   `api-key-list.html`/`.ts` (botones, estado vacío, toasts), los 2
   enlaces hardcodeados del shell (`shell.html`: "API Keys" → "Llaves de
   API", "Dashboard" → "Panel de Informes"), la lista de módulos del
   selector de changelog en `panel-soporte.ts`, y los `titulo` de
   `informes-config.ts` (M2-M5/M9, consumidos por `dashboard-informes/`).
2. **`packages/contracts/aerohub_contracts/roles_modulos.py::MODULOS`**
   -- la fuente real del nombre de cada módulo que llega al frontend vía
   `GET /auth/yo` → `modulos_visibles` → `shell.ts::modulosConVista()` (el
   `@for` del menú lateral que renderiza `modulo.nombre`). Este es el
   hallazgo real: los 9 nombres en inglés que persistían en el screenshot
   del usuario NO venían de ningún template Angular -- venían de este
   diccionario Python, servido en cada login. Traducido igual que el
   frontend (M2 "Administración de FIDS", M3 "Gestión de Terminales y
   Puertas", M4 "Operaciones de Rampa", M5 "Facturación e Ingresos", M6
   "Experiencia del Pasajero", M7 "ETL y Analítica", M8 "Observabilidad",
   M9 "Centro de Cumplimiento"; M1 "AODB" se mantiene -- es una sigla
   técnica real (Airport Operational Database), no una palabra en
   inglés). **Desplegado con `docker cp` + `docker restart aerohub-gateway`**
   (el proceso `uvicorn` ya tenía el módulo cargado en memoria, mismo
   hallazgo de despliegue ya documentado en S1.11).
3. **`catalogo.modulo.nombre` en MonetDB** -- la tabla que alimenta
   `licencia-list` (`GET /licencias/mi-tenant` → `consultar_licencias.py`
   → `infrastructure/licencia.py` → `JOIN` contra `catalogo.modulo`, S1.11
   "Novena iteración"). Los mismos 9 nombres en inglés vivían TAMBIÉN acá,
   sembrados por `01_catalogo.sql` -- un tercer origen independiente del
   mismo texto, no derivado de `MODULOS` de Python. Actualizado con
   `UPDATE catalogo.modulo SET nombre = ...` directo contra la primaria
   (usuario `monetdb`/admin, no `aerohub_app` -- ningún rol de aplicación
   tiene `GRANT UPDATE` sobre el catálogo, correcto: es dato de plataforma,
   no operativo). También `catalogo.departamento` (`D2`: "Ground
   Operations (Rampa)" → "Operaciones de Rampa"), aunque su nombre no se
   consume hoy en ninguna vista -- se corrigió por completitud ya que
   estaba en el mismo archivo/tabla. **`db/ddl/monetdb/01_catalogo.sql`
   actualizado en paralelo** (mismos `INSERT` con los nombres ya
   traducidos) para que un reset futuro del volumen no reintroduzca los
   nombres en inglés -- sin este cambio, la próxima vez que se recree la
   base desde cero (como pasó el 2026-08-06/07 en la iteración de reset
   completo) el hallazgo hubiera vuelto a aparecer solo. **No propagado a
   `monetdb-standby`/`monetdb-restore-test`** -- se deja que el *shipper*
   de continuidad (ADR-018, S1.9) replique el cambio como cualquier otra
   escritura real, sin tocar esas 2 instancias a mano.

**Hallazgo de caché de sesión durante la verificación**: `AuthService`
guarda `modulos_visibles` en `localStorage` (`aerohub.sesion`) desde la
respuesta de login, y NO la vuelve a pedir en cada recarga de página --
un simple `F5` después del cambio de backend seguía mostrando los
nombres viejos. Hace falta cerrar sesión y volver a entrar (o limpiar
`localStorage`) para que el perfil se resuelva de nuevo contra
`GET /auth/yo` con el diccionario `MODULOS` ya actualizado. No es un bug
-- es el mismo patrón de caché de sesión ya usado a propósito desde
S1.10 -- pero vale la pena recordarlo para no confundirlo con que el
cambio de backend no tomó.

**Verificado en navegador real** (`canario@mec.aerohub.test`, sesión
nueva tras limpiar `localStorage`): los 9 enlaces del menú lateral en
español (`Array.from(document.querySelectorAll('.side__link'))`
confirmado por JS), tabla de Licencias con los 6 módulos contratados en
español. Build de producción de `apps/web` en verde tras cada tanda de
copias. Ningún test de integración de backend depende del texto de
`Modulo.nombre` (son claves `codigo`/scopes las que se comparan, no el
nombre legible) -- no se corrió la suite completa para este cambio
puramente textual, solo se confirmó que el gateway levantó sano después
del restart.

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

## Extensión de la iteración de cabecera a AODB (2026-08-08, pendiente de commit)

Pedido directo del usuario: "al modulo de AODB porque la abreviacion,
ese no se la aplico el rediseño del plan" -- `vuelos/estado-tiempo-real`
había quedado deliberadamente fuera de las 2 rondas de propagación
anteriores (`docs/diseno/MODAL_Y_WORKPANEL.md` §1.2 lo señalaba
explícitamente como "sigue sin tocar") porque su nombre es una sigla
corta y no un título largo como el resto -- el usuario pidió cerrarla
igual, completando las 10 vistas administrativas/operativas de
`role_tenant_admin` con el mismo patrón.

**Adaptación, no copia literal del patrón**: esta vista no tiene ningún
"cargar" manual que justifique el ícono `.consola__refrescar` -- se
conecta sola por WebSocket y se reconecta sola si se cae (Fase 5 item 14
de `PLAN_CORRECCION_MODULOS.md`, ya consolidado desde antes de esta
sesión). En su lugar, el indicador de conexión (`.consola__conexion`,
semáforo `.ah-punto` verde/ámbar/rojo) se movió a la misma fila que el
`<h1>`, en vez de vivir en un párrafo aparte debajo de la cabecera como
antes. El KPI se redujo a un solo chip ("N eventos en estado crítico",
`.ah-chip--critico`) -- se retiró el conteo neutro de "eventos
recientes" (antes texto libre en `.consola__resumen`, ahora eliminado)
porque no existe una variante neutra de `.ah-chip` en `_primitivos.scss`
(el primitivo solo define `--critico`/`--atencion` a propósito: un chip
llama la atención, no narra un total que la tabla ya muestra). El
`.ah-panel` de búsqueda (con su propio `<h2>` "Buscar por vuelo") se
reemplazó por `.consola__fila-busqueda` con `.ah-buscador` (ícono `⌕`) +
el botón "Nuevo vuelo" en la misma fila, igual que las otras 9 vistas.

**Verificado**: build de producción de `apps/web` en verde (mismo
warning de bundle conocido) tras `docker cp` + rebuild dentro de
`aerohub-web` + `docker restart aerohub-web`. No verificado en
navegador real (regla vigente: solo si se pide explícitamente).

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

## Reordenamiento del menú + rediseño de tarjetas KPI del Dashboard (2026-08-08, pendiente de commit)

Dos pedidos directos del usuario, mismo día.

**1. "Dashboard" primero en el menú, nombre restaurado**: el enlace de
`informes/dashboard` (renombrado "Panel de Informes" en la traducción de
esta misma sesión) se movió al principio de `side__nav` en `shell.html`
-- antes de "Tenants" -- y recuperó el nombre "Dashboard" tanto en el
enlace como en `data.title` de `app.routes.ts` (el usuario lo pidió
explícitamente así, "dashboard" en inglés es la excepción deliberada a
la traducción general, no un descuido).

**2. Tarjetas KPI del Dashboard, con referencia visual externa**: el
usuario mostró una captura de un dashboard SaaS genérico (8 tarjetas en
grilla 4×2, cada una con eyebrow "Month to date", título, valor grande
coloreado, sparkline o barra de progreso, y pie con logo de
integración + variación %) y pidió distribuir el Dashboard de AeroHub
así. La fila plana de KPIs (`.ah-kpi-fila`, un `<div>` por indicador con
solo etiqueta+valor) se reemplazó en
`informes/dashboard-informes/` por una grilla de tarjetas
(`.kpi-grid`/`.kpi-card`, 4 columnas en escritorio, `auto-fit` en
pantallas angostas) con eyebrow + título + valor grande + pie.
**Decisión deliberada de NO copiar el pie de tarjeta literal**: la
referencia trae sparkline y variación % porque cada tarjeta viene de una
integración real con historial (Stripe, HubSpot, Google Analytics...) --
los KPI de AeroHub (`DASHBOARDS_POR_ROL` en `informes-config.ts`) son
conteos reales sobre filas ya cargadas de un informe simple, sin serie
histórica ni comparación con un período anterior. Inventar un
sparkline o un `%` ahí violaría el principio de verificación empírica
que rige todo el proyecto -- se adaptó el layout sin fabricar datos:
- **Eyebrow**: el período efectivamente aplicado (Hoy/Últimas 24 h/Esta
  semana, según `atajoActivo()`), no un texto fijo.
- **Pie de tarjeta**: el informe real del que se deriva el número
  (`fuenteKpi()`, el `titulo` de la sección origen) en vez de un
  logo/variación inventados -- procedencia real, no decoración.
- **Color del valor**: heurística por texto de la etiqueta
  (`claseValorKpi()`, lista `PALABRAS_CRITICO`: "vencid", "no
  completad", "disputad", etc. → rojo; el resto queda en navy neutro) --
  mismo criterio de semáforo por palabra clave ya usado en otras partes
  de la app, no una regla de negocio nueva.

**Verificado**: build de producción de `apps/web` en verde (mismo
warning de bundle conocido) tras `docker cp` + rebuild + `docker restart
aerohub-web`, en ambos pasos. No verificado en navegador real (regla
vigente: solo si se pide explícitamente).

**3. Corrección sobre el punto 2, mismo día**: el usuario volvió a pedir
explícitamente el layout completo "tal cual" la referencia, incluyendo
sparkline y variación % -- no solo el esqueleto de tarjeta. Se
implementaron ambos, pero derivados de dato real en vez de decorativos
(el principio de verificación empírica de este proyecto no se relaja ni
a pedido explícito -- se busca la forma de cumplir el pedido visual sin
fabricar números):
- **`ConfigInforme` gana `campoFecha?: string`** (`informes-config.ts`):
  el campo de fecha/fecha-hora real de cada fila, mapeado en las 5
  secciones que tienen uno (`fecha_operacion` en AODB, `inicio_previsto`
  en Puertas/Rampa, `periodo_inicio` en Billing, `ocurrido_en` en
  Compliance). Tenants queda sin `campoFecha` -- su informe no filtra por
  período, no hay eje temporal real que agrupar.
- **`serieKpi(kpi)`** (`dashboard-informes.ts`): agrupa las filas YA
  CARGADAS de la sección por día (`campoFecha`) y le aplica el MISMO
  `kpi.calculo` de la tarjeta a cada grupo -- la serie que se grafica es
  el valor real de ESE kpi puntual, día por día, dentro del período ya
  consultado (no una serie generada al azar).
- **`puntosSparkline(serie)`**: normaliza la serie real a un `<polyline>`
  SVG (`viewBox 0 0 100 30`), sin librería de gráficos.
- **`tendenciaPct(serie)`**: variación real entre el promedio de la
  primera y la segunda mitad de la serie diaria -- comparación dentro del
  propio período cargado (no contra el período anterior, que pediría una
  consulta nueva al backend fuera de alcance de este pase). `null` cuando
  no hay al menos 2 días de datos para comparar -- la tarjeta omite el
  sparkline/badge en ese caso (Tenants, o cualquier período de un solo
  día) en vez de forzar un punto de comparación inexistente.
- **`claseTendencia(kpi, pct)`**: polaridad por semántica -- para un KPI
  "crítico" (vencidas, interrumpidos...) que la serie SUBA es malo (rojo),
  para el resto que suba es bueno (verde); mismo criterio de
  `claseValorKpi`.
- **Pie de tarjeta**: el logo de integración externa de la referencia
  (Stripe/HubSpot/Google Analytics...) se reemplaza por un punto de color
  fijo (`.kpi-card__fuente-punto`) + el nombre del informe real de
  origen -- AeroHub no tiene esas integraciones por KPI, simular una
  marca inexistente sí habría cruzado la línea de fabricar información.

**Verificado**: build de producción de `apps/web` en verde (mismo
warning de bundle, ahora 731KB) tras `docker cp` + rebuild + `docker
restart aerohub-web`. No verificado en navegador real (regla vigente:
solo si se pide explícitamente) -- pendiente si el usuario lo solicita,
en particular para confirmar visualmente el trazo del sparkline SVG.

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

## Vista faltante de la propagación: `billing/panel-tarifarios` (2026-08-08, pendiente de commit)

El usuario preguntó "aplicaste el rediseño aqui tambien?" refiriéndose
en general al plan de propagación -- un chequeo (`grep` de
`consola__fila-busqueda`/`consola__cabecera` sobre las 13 vistas con
`class="consola"`) confirmó que `billing/panel-tarifarios` (Tarifarios y
conciliación) se había quedado con el patrón viejo: botón "Actualizar"
suelto en vez de ícono inline, `.ah-panel` de búsqueda separado en cada
una de sus 2 secciones (Tarifarios, Conciliación de pax), sin ningún
chip KPI. Se me pasó al hacer la propagación original -- no había sido
una exclusión deliberada como sí lo es `tenants/tenant-list`
(`role_platform_admin`, fuera de alcance).

Corregido con el mismo patrón que el resto: ícono `.consola__refrescar`
inline en el `<h1>`, chip nuevo "N conciliaciones pendientes"
(`conciliacionesPendientes` computed en `panel-tarifarios.ts`, mismo
criterio de conteo real sobre filas ya cargadas que el resto de la app),
y `.consola__fila-busqueda` en las 2 secciones (antes 2 `.ah-panel`
separados). Sin chip para Tarifarios -- no hay una condición de atención
real que contar ahí (a diferencia de conciliaciones pendientes, que sí
es una cola de trabajo).

**Con esta corrección, las 10 vistas administrativas/operativas de
`role_tenant_admin` (más el Dashboard, que tiene su propio patrón de
cabecera con filtro de período global) quedan con el mismo patrón de
cabecera/modal.** `tenants/tenant-list` sigue siendo la única excepción
deliberada (`role_platform_admin`, fuera de alcance del plan desde su
origen).

**Verificado**: build de producción de `apps/web` en verde (mismo
warning de bundle, ahora 732KB) tras `docker cp` + rebuild + `docker
restart aerohub-web`. No verificado en navegador real (regla vigente).

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

## Auditoría de la capa operativa + cierre de 2 hallazgos de permisos (2026-08-08, pendiente de commit)

Auditoría general pedida por el usuario sobre los 5 roles operativos
(`role_tenant_admin`, `role_operations_controller`, `role_ramp_agent`,
`role_airline_coordinator`, `role_billing_officer`): se cruzaron las 3
capas (scope de aplicación en `roles_modulos.py` → `GRANT` de motor en
`db/ddl/monetdb/9*_grants_*.sql` → superficie de frontend) con
verificación empírica de 40 combinaciones de lectura y 20 de escritura
vía `TestClient` contra MonetDB real.

**Resultado general: la segregación de funciones es exacta** -- cada 403
observado es deliberado, cada 200 también, y **no apareció ni un solo 500
opaco** (el traductor de errores de motor de S1.20 funciona). La decisión
D1(a) sigue en pie (`role_tenant_admin` bloqueado en escritura de
M1/M3/M4/M5) y el mínimo privilegio de `role_ramp_agent` está
genuinamente implementado en lectura y escritura, con semántica
404-no-403 (PN-01).

**Hallazgo 1 (crítico, CORREGIDO) -- M6 Passenger estaba 100% muerto, en
un cruce invertido perfecto.** Cuarto caso de la familia `fids:*`
(S1.16) / `compliance:*` (S1.19) / `support:*` (S1.20), y el peor de los
cuatro:

- `passenger:escribir` **no lo tenía ningún rol** →
  `POST /passenger/tiempos-espera/recalcular` (CU-O19, RF-O17) era
  inalcanzable por cualquier sesión humana desde S1.6.
- `passenger:leer` lo tenían `role_tenant_admin`/`role_airline_coordinator`/
  `role_tenant_analyst`, pero **ninguno tenía `GRANT`** sobre
  `billing.tiempo_espera_agregado` → 403 "acceso denegado" de motor.
- `role_operations_controller` **tenía el `GRANT` completo (S,I,Up)** desde
  S1.6 -- `98_grants_billing.sql:19,54` lo designa explícitamente como el
  "Sistema" que ejecuta el recálculo -- pero **ningún scope `passenger:*`**.

O sea: quien tenía el permiso de motor no tenía el scope, y quien tenía el
scope no tenía el permiso de motor. Ninguna auditoría previa lo detectó
porque M6 tiene `ruta: null` y nunca tuvo vista que lo ejercitara.
**Corregido**: `passenger:leer`+`passenger:escribir` a
`role_operations_controller` (sin agregarle M6 a sus módulos -- mismo
criterio de "scope de API sin visibilidad de menú" ya usado para
`vuelos:leer` en `role_billing_officer`/`role_ramp_agent`), y
`GRANT SELECT ON billing.tiempo_espera_agregado` a `role_tenant_admin` y
`role_airline_coordinator`. `role_tenant_analyst` queda **fuera a
propósito** (la matriz le niega `billing` entero; esa decisión sigue en
pausa por pedido del usuario). Verificado: los 3 roles pasan de 403 a 200
en `GET`, y `role_operations_controller` ejecutó el recálculo real
(`{'franjas_actualizadas': 0, ...}`) -- CU-O19 corrió por primera vez
desde que se construyó.

**Hallazgo 2 (CORREGIDO) -- `role_airline_coordinator` tenía `GRANT` de
escritura sin scope.** La matriz 4.3.1 le asigna U,S,I,Up sobre `ops`
("solo sus itinerarios") y `96_grants_ops.sql:97-103` ya le otorgaba
INSERT/UPDATE sobre `ops.vuelo`/`vuelo_estado` desde S1.4 -- pero sus
scopes eran solo `{vuelos:leer, passenger:leer}`. **Inverso de la causa
raíz A: motor abierto, aplicación cerrada.** Combinado con el hallazgo 1
y con que M6 no tiene ruta, su superficie usable completa era **una vista
de solo lectura**. La nota previa de este archivo ("M1 sin botón de
escritura -- correcto") había validado que el frontend coincide con el
scope, pero nunca preguntó si el scope coincide con la matriz.
**Corregido** agregando `vuelos:escribir`; verificado antes que la ruta de
escritura completa ya estaba aprovisionada (INSERT sobre
`continuidad.journal_mutacion` y `compliance.log_auditoria`), así que **no
hizo falta ningún `GRANT` nuevo**. NO se agregó `puertas:*` pese a que el
motor también le otorga `asignacion_puerta`: la columna `ops` de la matriz
es de granularidad de esquema, y la asignación de módulos (M1, M6) es la
autoridad más fina sobre lo que el rol realmente opera -- M3 es de
`role_operations_controller`. El frontend no necesitó cambios: el gate de
`vuelos/estado-tiempo-real` es por scope (`puedeEscribir()`), así que los
botones aparecen solos.

**Verificación de escritura real (no solo 422 de validación)**: como el
hallazgo entero trata de "el scope pasa y el motor muere", se creó un
vuelo real con `role_airline_coordinator` (`POST /vuelos` → 201, fila
`AUD901` confirmada en `ops.vuelo` con el tenant correcto) y se registró
un estado real (`POST /vuelos/{id}/estados` → 201). **Residuo conocido**:
ese vuelo de prueba `AUD901` (fecha 2026-08-09, tenant MEC) quedó en la
base -- no se borró porque P5 prohíbe la baja física y sus filas de
journal/auditoría son append-only por diseño; borrar el vuelo dejando el
rastro de auditoría apuntándole sería peor que dejarlo.

**Hallazgo 3 (CORREGIDO en la misma sesión) -- "solo sus itinerarios"/"sus
cargos" no estaba implementado porque NO ERA REPRESENTABLE.** Ambos
archivos de grants delegan ese recorte a la aplicación, pero ninguna tabla
asociaba un usuario a una aerolínea. Se agregó `tenants.usuario.aerolinea_id`
(FK nullable a `catalogo.aerolinea`, `02_tenants.sql` + `ALTER TABLE` en
vivo) y el recorte completo:

- **El contexto viaja por el JWT**, igual que `tenant_id`/`rol`/`usuario_id`
  -- `contexto_aerolinea_id()` nuevo en `packages/repository/contexto.py`,
  poblado por `contexto_gateway.poblar_contexto`. Nunca se acepta del
  cuerpo: un coordinador no puede pedir los vuelos de otra aerolínea
  cambiando un parámetro. Elegido sobre un lookup por consulta para no
  necesitar GRANTs nuevos sobre `tenants.usuario` en aodb/billing.
- **`filtro_aerolinea_del_actor()`** en `aerohub_aodb` y `aerohub_billing`
  (copia local deliberada -- `.importlinter` prohíbe importar entre
  módulos, mismo criterio con el que cada módulo redeclara sus `Table()`).
  Aplicado en `listar_vuelos`, `obtener_vuelo_por_id`, `listar_facturas`,
  `obtener_factura_por_id` **y los informes de ambos módulos** (si no, el
  dashboard sería una vía alternativa para leer los datos de la
  competencia).
- **Fail-closed**: un coordinador sin `aerolinea_id` configurada ve 0
  filas, nunca todas.
- **`PATCH /usuarios/{id}/aerolinea`** + selector en el modal de
  `usuarios/usuario-list` (solo visible si el rol elegido lo usa,
  `ROLES_CON_AEROLINEA`) -- sin esto la columna no tendría forma de
  poblarse y todo coordinador vería 0 vuelos para siempre.

**Hallazgo empírico nuevo, encontrado por el propio guardián**: el
centinela fail-closed NO puede ser `sqlalchemy.false()`. SQLAlchemy
colapsa `A AND B AND false` a `false` y con ello **desaparece el filtro de
tenant del WHERE compilado**, así que el guardián G2 aborta con
`TenantScopeViolation`. Se usa `IS NULL` sobre la propia columna, que es
`NOT NULL` en ambas tablas (`10_ops.sql:37`, `12_billing.sql:92`): nunca
coincide y, al ser un predicado real sobre una columna, no colapsa el
resto del WHERE.

**Hallazgo 4 (CORREGIDO) -- el dashboard de `role_ramp_agent` no respondía
su propia pregunta.** Preguntaba "¿Qué tengo que hacer ahora?" y su única
sección era el informe de turnarounds de TODO el tenant. **Corrección de
un dato que la primera versión de esta auditoría reportó mal**: se dijo
que "su dashboard es más amplio que su propio workpanel" -- es falso,
`listar_turnarounds` (el workpanel) tampoco filtra por agente. El mínimo
privilegio de este rol es exclusivamente a nivel de *tarea*
(`agente_usuario_id`), no de turnaround, así que no había fuga ni
inconsistencia entre ambos. El problema real era solo que no existía
ningún endpoint de "mis tareas del periodo": el filtro por agente solo
vivía en `listar_tareas_de_turnaround`, que exige un turnaround puntual y
no sirve para un panel de jornada. Se agregó
`GET /rampa/informes/mis-tareas` (scope `rampa:leer`, sin scope nuevo --
son SUS tareas, un subconjunto de lo que ya ve; el usuario se resuelve de
la sesión, nunca como query param) y el dashboard pasa a
`[CONFIG_INFORME_MIS_TAREAS, CONFIG_INFORME_TURNAROUNDS]`, con los
turnarounds del tenant como contexto secundario.

**Tests de regresión nuevos**: `tests/integration/test_auditoria_capa_operativa.py`
(11 tests, los 11 en verde) cubre los 4 hallazgos. **Derivan los scopes de
`scopes_del_rol(...)`, nunca los fabrican a mano** -- exactamente la
causa por la que la suite de S1.20 no detectó su propio hallazgo.

**Test obsoleto corregido de paso**:
`tests/unit/tenancy/test_modulos_visibles.py::test_role_platform_admin_ve_los_9_modulos`
afirmaba que ese rol ve los 9 módulos, pero **S1.11 invirtió esa decisión
deliberadamente** -- el test llevaba rojo desde entonces. Reescrito como
`test_role_platform_admin_no_ve_ningun_modulo_operativo`. Un test
permanentemente rojo entrena a ignorar fallos, que es exactamente cómo
S1.20 se le escapó a su propia suite.

**Verificado** (tras los 4 hallazgos): ruff (los 8 hallazgos restantes son
deuda preexistente en `tests/integration/test_aodb_catalogos.py`,
`test_fids_administracion.py` y `tools/crear_usuarios_demo_roles.py`, no
tocados), mypy en verde (273 archivos), bandit sin nada nuevo,
import-linter 16/16 contratos. **293 tests unit/negative/cross_tenant en
verde, 0 fallos**; **134 de integración en verde contra MonetDB real**
(123 previos + 11 nuevos), con exactamente los 6 fallos preexistentes ya
documentados (3 de `test_continuidad_shipper.py` por hostname, 3 que
dependían de `mailpit`, retirado del stack). Build de producción de
`apps/web` en verde (738 KB, mismo warning de bundle conocido).
Verificación empírica adicional del ciclo completo con **login real** (no
JWT fabricado): asignar aerolínea por `PATCH` → el JWT emitido trae el
claim `aerolinea_id` → `GET /vuelos` devuelve solo esa aerolínea →
desasignar → 0 filas.

Nota de entorno: la imagen del gateway no incluye `tests/`, `db/` ni
`tools/` -- hay que `docker cp`-arlos antes de correr la suite, y los
tests de integración necesitan `AEROHUB_TEST_DB_HOST=monetdb` o se saltan
silenciosamente (159 skipped, que parece verde y no lo es). Ojo con
`docker cp tests aerohub-gateway:/app/tests` cuando `/app/tests` YA existe:
anida en `/app/tests/tests` en vez de reemplazar (aparece como archivos
duplicados en ruff, es ruido del contenedor, no del repo).

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

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

## Consolidación de documentos de diseño (2026-08-07, pedido explícito)

`docs/diseno/` quedó reducido a **2 documentos de diseño vigentes**:
`DIRECCION_VISUAL.md` (general -- tokens, tipografía, principios) y
`MODAL_Y_WORKPANEL.md` (nuevo -- estructura de workpanel y modal "Ver
detalles", con `usuarios/usuario-list` como referencia viva). Se
**eliminaron** `PLAN_WORKPANELS_MODULOS.md`, `WORKPANEL_Y_DASHBOARD_ROLES.md`,
`ROLES_POR_CAPA.md`, `PLAN_CORRECCION_MODULOS.md`,
`PLAN_DASHBOARDS_OPERATIVOS.md` y `PLAN_CORRECCION_Y_DASHBOARD_ROLES_RESTANTES.md`
tras fusionar lo vigente en esos 2 documentos -- **cualquier mención a esos
6 archivos en las secciones de abajo es un registro histórico de una
sesión anterior, no un enlace navegable**. El checklist de causas raíz que
`PLAN_CORRECCION_MODULOS.md` dejaba (scope vs. GRANT, traductor de
errores, datos sin sembrar, vista sin listado) sigue completo más abajo en
este mismo archivo -- eso no se perdió, solo el documento fuente.
`docs/diseno/PLAN_REVISION_ENDPOINTS_FRONT.md` en ese momento no se tocó
(tema distinto: brechas de API, no diseño) -- **retirado despues, el
2026-08-08**, pedido explícito del usuario en la misma sesión que
documentó la iteración de cabecera de `usuarios/usuario-list` (ver más
abajo); a diferencia de los otros 6, este SÍ estaba citado como evidencia
en `docs/PLAN_IMPLEMENTACION_v3.0.md` (3 enlaces), corregidos para no
apuntar a un archivo inexistente. `docs/diseno/` queda con exactamente 2
documentos: `DIRECCION_VISUAL.md` y `MODAL_Y_WORKPANEL.md`.

## Iteración de cabecera y modal en `usuarios/usuario-list` (2026-08-08, commit `b4fc851`)

Pedido directo del usuario con una captura de referencia externa --
rediseño puntual del workpanel de Usuarios y Equipo, documentado en
detalle en `docs/diseno/MODAL_Y_WORKPANEL.md` §1.2 (no se repite acá,
solo el resumen y los hallazgos).

1. **Cabecera**: eyebrow (`.consola__eyebrow`) + ícono de refresco
   inline junto al `<h1>` (reemplaza el botón "Actualizar" suelto); KPI
   como chips de fondo tenue (`.ah-chip`, nuevo primitivo local) en vez
   de la oración de resumen; una sola fila con buscador con ícono,
   filtro inline y el botón de acción principal (reemplaza el panel de
   búsqueda + barra de acciones separados). Acción de fila: texto "Ver"
   (se probó un ícono de solo-ojo primero, revertido a pedido explícito).
2. **Experimento de `<select>` personalizado, probado y revertido el
   mismo día**: se construyó `app-select-personalizado`
   (`apps/web/src/app/shared/select-personalizado/`, ya eliminado) para
   reemplazar el `<select>` nativo -- primero solo la flecha (CSS puro,
   funcionaba bien), después un listbox propio completo para la lista
   desplegable (imposible de re-estilar en un `<select>` nativo con CSS
   puro). **2 hallazgos técnicos reales en el camino**, documentados en
   detalle en `MODAL_Y_WORKPANEL.md` §1.2 para no re-descubrirlos si se
   vuelve a intentar: (a) un `overflow` de un ancestro (`.ah-modal`)
   recorta a sus descendientes sin importar el `position` de estos --
   `position: fixed` no escapa del recorte mientras el nodo siga siendo
   descendiente en el DOM, hace falta reubicarlo físicamente en
   `document.body`; (b) una vez reubicado y posicionado con
   `getBoundingClientRect()` calculado una sola vez al abrir, la lista
   queda "flotando" desconectada del control si se hace scroll dentro
   del modal después -- se resuelve cerrando el listbox ante cualquier
   scroll (listener de captura sobre `document`, mismo criterio que
   click-afuera/Escape). Con ambos hallazgos ya resueltos y el
   componente funcionando, el usuario pidió explícitamente volver al
   `<select>` nativo sin ninguna personalización -- decisión final,
   componente eliminado, `_primitivos.scss` revertido a `appearance: auto`.
3. **Consolidación de documentación** (mismo pedido): `docs/diseno/MODAL_Y_WORKPANEL.md`
   actualizado con la iteración de cabecera (marcada explícitamente como
   "hoy solo en `usuarios/usuario-list`", no propagada a `tenants`/
   `api-keys`/`licencias`) y con el experimento del select documentado
   como referencia para no repetirlo sin pedido explícito.
   `docs/diseno/PLAN_REVISION_ENDPOINTS_FRONT.md` retirado (ver nota de
   consolidación arriba) -- sus 3 citas en `docs/PLAN_IMPLEMENTACION_v3.0.md`
   corregidas para no apuntar a un archivo inexistente. `docs/PLAN_IMPLEMENTACION_v2.0.md`
   retirado tambien (pedido explicito, mismo dia) -- a diferencia del
   resto de documentos consolidados, v3.0.md lo marcaba deliberadamente
   como "conservado como historico" al reemplazarlo, asi que se confirmo
   con el usuario antes de borrarlo; sus 3 referencias
   (`PLAN_IMPLEMENTACION_v3.0.md`, `ANALISIS_RUMBO_Y_BRECHAS_2026-08.md`,
   este archivo) corregidas para explicar el retiro en vez de apuntar a
   un archivo inexistente.
4. **Verificado**: build de producción de `apps/web` en verde en cada
   paso (cabecera nueva, select personalizado, y revert final); todo
   probado en navegador real logueado como `canario@mec.aerohub.test`
   (`role_tenant_admin`) -- filtro por rol, KPI en vivo, switch de
   estado con guardado diferido, apertura/cierre del listbox
   personalizado (mientras existió) y su comportamiento ante scroll,
   sin errores de consola en ningún paso.
5. **Hallazgo de infraestructura, no de código**: el stack completo de
   Docker se cayó a mitad de esta sesión (`Exited (137)` en
   `monetdb`/`monetdb-standby`/`monetdb-restore-test`/`gateway`/
   `fids-player`/`clickhouse`/`continuidad-agente` -- síntoma de
   OOM-kill del host). Se reinició manualmente
   (`docker start monetdb monetdb-standby monetdb-restore-test minio`,
   luego `gateway fids-player`) y se verificó sano antes de continuar.
   Si vuelve a pasar seguido, revisar el límite de memoria asignado a
   Docker Desktop.
6. **Hallazgo de proceso, no de código**: `canario@mec.aerohub.test`
   quedó con 2 usuarios de prueba en estado `suspendido`/con rol
   reasignado (`Usuario PN-16`, `Demo role_tenant_analyst`) como
   residuo de las pruebas de esta sesión sobre datos reales -- no se
   revirtieron por completo, queda para una limpieza futura si hace
   falta un estado prolijo para demos.
7. **Modal "Invitar Usuario" -- título duplicado corregido** (pedido
   directo con captura, mismo día): `apps/web/src/app/usuarios/invitar/`
   reusaba `_auth-form.scss` (pensado para páginas de auth standalone,
   con su propio `<h1>` + tarjeta con sombra) -- al embeberse dentro de
   `.ah-modal` (que ya trae su propia cabecera con título + botón de
   cierre) esto se veía como un título duplicado y una
   tarjeta-dentro-de-tarjeta. Reescrito para seguir exactamente el mismo
   patrón que el modal "Ver detalles" (`.formulario` + `.ah-campo` por
   campo + `.ah-alerta` + `.modal-acciones` con
   `justify-content: flex-end`), sin `<h1>`, sin tarjeta ni sombra
   propias -- documentado como regla general nueva en
   `docs/diseno/MODAL_Y_WORKPANEL.md` §2.7 ("componentes de creación
   embebidos, sin título ni tarjeta propia") para que cualquier otro
   formulario de alta embebido en un modal siga el mismo criterio.
   Verificado en navegador real: un solo `<h2>` dentro del modal
   (`Invitar Nuevo Usuario`), campos Correo/Rol, botones "Enviar
   invitación"/"Cancelar" alineados a la derecha, sin errores de
   consola. Build de producción en verde (bundle ~10KB más chico al
   dejar de depender de `_auth-form.scss`).

## `docs/diseno/PLAN_PROPAGACION_WORKPANEL_MODAL.md` implementado (2026-08-08, pendiente de commit)

Propagación completa del patrón de `usuarios/usuario-list` (§1.2/§2 de
`docs/diseno/MODAL_Y_WORKPANEL.md`) a las 5 vistas administrativas
restantes de `role_tenant_admin`, en el orden propuesto por el plan
(simple → grande): **API Keys → Licencias → FIDS → Soporte → Compliance
Hub**. `tenants/tenant-list` (`role_platform_admin`) y las 4 vistas
operativas densas quedan fuera, tal como el plan lo definía desde el
principio.

1. **API Keys**: eyebrow + refresco inline, chip único ("N por expirar en
   30 días" -- se descartó un chip para "activas", no es un conteo que
   requiera atención), fila de búsqueda + "Generar API Key". `apiKeysActivas`
   y `resumenLlaves` (ya no usados) se retiraron del `.ts`.
2. **Licencias**: mismo patrón, **sin fila de búsqueda** (catálogo cerrado
   M1-M9, sin filtro de texto ni acción de alta -- el workpanel queda
   reducido a cabecera + chip + tabla). `licenciasVigentes`/`resumenLicencias`
   retirados.
3. **`.ah-chip` promovido a primitivo global** (`_primitivos.scss`) al
   llegar al tercer uso real (Usuarios/API Keys/Licencias) -- se quitaron
   las 3 copias locales, verificado que las 3 vistas lo siguen usando bien
   desde el primitivo compartido.
4. **FIDS** (2 secciones: Plantillas, Pantallas): primera vista
   multi-sección -- confirma el criterio "un eyebrow/chips de página, una
   fila de búsqueda por sección". Los 4 modales de FIDS ya seguían el
   patrón correcto (sin título duplicado), sin cambios ahí más que alinear
   `.modal-acciones` a la derecha.
5. **Soporte** (3 secciones: Tickets, KB, Changelog): la sección Tickets
   combina 2 filtros (Estado + Severidad) como `.ah-campo--inline` en la
   misma fila, antes del botón "Nuevo ticket" -- primer caso real de "más
   de un filtro en una fila", documentado en `MODAL_Y_WORKPANEL.md` §1.2.
6. **Compliance Hub** (5 secciones -- la más grande, dejada última a
   propósito): 2 chips de página (incidentes abiertos, post-mortems sin
   publicar) + 5 filas de búsqueda, una por sección. `resumenCompliance`
   retirado.
7. **Verificado, vista por vista, en navegador real** (nunca JWT
   fabricado): API Keys/Licencias/FIDS/Soporte con `canario@mec.aerohub.test`
   (`role_tenant_admin`); Compliance con `auditor@mec.aerohub.test`
   (`role_regulatory_auditor` -- `role_tenant_admin` no tiene `GRANT` de
   motor sobre `compliance.*`, hallazgo pre-existente de S1.7/S1.19, no
   apto para probar esta vista). Build de producción de `apps/web` en
   verde después de cada vista. Ningún modal de creación quedó con título
   duplicado en ninguna de las 5.
8. **2 hallazgos de conexión transitoria del pool** durante la
   verificación (`GET /support/catalogo/categorias-ticket` y
   `GET /compliance/accesos-auditor`, ambos 500 en el primer intento) --
   mismo patrón ya documentado extensamente (pool de MonetDB,
   `pool_recycle=180`), confirmado con reintento inmediato (200 OK en
   ambos casos), no una regresión introducida por este pase.

**Sin commitear todavía** -- pendiente de pedido explícito del usuario
(Principio V).

## Checklist de corrección de módulos (lecciones ya cerradas de un plan hoy consolidado, no repetir)

El extinto `docs/diseno/PLAN_CORRECCION_MODULOS.md` (Fases 1-6, cerrado
2026-08-07, contenido ya consolidado -- ver nota arriba) encontró que casi
todos los "errores" que un usuario reporta módulo por
módulo se explican por un puñado de **causas raíz repetibles**, no por
bugs sueltos distintos cada vez. **Leer esto antes de corregir o
construir cualquier módulo nuevo** (incluido el dashboard operativo que
sigue) — evita re-descubrir estos mismos hallazgos a mano otra vez.

### Las 4 causas raíz a chequear siempre

- **A. Scope de aplicación ≠ GRANT de motor.** La autorización vive en
  dos capas independientes: el scope del JWT (`packages/contracts/
  aerohub_contracts/roles_modulos.py`) y el `GRANT` real de MonetDB bajo
  `SET ROLE` (`db/ddl/monetdb/9*_grants_*.sql`). Agregar un scope nuevo a
  un rol SIN el `GRANT` correspondiente pasa el control de la aplicación
  y muere en el motor con un 500 opaco (o 403 legible, ver causa B).
  **Antes de agregar cualquier scope nuevo a un rol**: `grep` los
  archivos de grants de esa(s) tabla(s) para confirmar que el rol ya
  tiene el privilegio de motor que ese scope implica -- si no lo tiene,
  agregarlo en el mismo cambio (ver el ejemplo de `role_billing_officer`
  + `vuelos:leer` + `ops.vuelo_estado` en Fase 5, item 15).
- **B. El traductor de errores de permisos debe reconocer TODAS las
  frases del motor.** `services/gateway/main.py::_manejador_acceso_denegado_motor`
  ya reconoce `"access denied"` (SELECT denegado) e
  `"insufficient privileges"` (INSERT/UPDATE/DELETE denegado) -- si
  MonetDB usa una frase nueva para un tipo de operación no visto todavía
  (p. ej. `EXECUTE` sobre un procedimiento), hay que agregarla ahí
  también o vuelve a aparecer un 500 en vez de un 403.
- **C. Sin datos sembrados, un módulo correcto parece un bug.**
  `db/seeds/generate.py` sigue el patrón `_obtener_o_crear_X` (idempotente,
  lookup por la clave `UNIQUE` real de la tabla antes de insertar). Todo
  módulo nuevo (o toda tabla nueva de uno existente) necesita su propio
  helper ahí, sembrado por tenant canario en el loop principal -- de lo
  contrario la pantalla se abre vacía tras cualquier reset y se reporta
  como "esto no funciona" cuando en realidad nunca hubo datos que mostrar.
- **D. Confirmar que existe un listado antes de construir la vista.**
  Un módulo con solo `POST`/`GET /{id}` (alta + detalle puntual, sin
  `GET` de listado) no puede tener una pantalla que "abra mostrando algo"
  -- por diseño, no por bug. Si falta, es un hueco de API que se cierra
  primero (nuevo caso de uso + endpoint), nunca se intenta maquillar en
  el frontend. Ejemplo: `GET /vuelos` no existía hasta la Fase 3 de este
  plan; sin él, M1 dependía enteramente de eventos de WebSocket.

### Estándar de CRUD unificado (aplica a toda vista nueva o corregida)

`crear` / `ver detalles` (contenedor único de **todas** las acciones
propias del registro -- nunca botones de fila sueltos por cada acción) /
`editar` (dentro del detalle) / `suspender-activar` si el dominio lo
soporta estructuralmente (no forzarlo si la entidad no tiene un campo de
estado para eso -- ver M3 Gates, que no tiene "activo/suspendido" y por
lo tanto su CRUD real es solo crear+editar). **Eliminación física: nunca**
-- si existe un botón así en una vista, se retira (el endpoint del
backend puede quedar intacto sin consumidor, D2(b) del plan).

### Antes de reportar un módulo como "corregido"

1. `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre el **repo
   completo**, no solo los archivos tocados (Fase 6 encontró un import
   propio fuera de orden que había pasado desapercibido durante 2 fases
   enteras por revisar solo carpetas puntuales).
2. Suite de tests completa, no solo la del módulo -- un cambio de scope
   o de GRANT puede romper un rol que no se estaba mirando.
3. Verificación en navegador real con **login real** (no JWT fabricado a
   mano cuando se está probando un cambio de scope/permiso -- un JWT
   fabricado con `codificar_jwt` puede tener scopes que la sesión real
   nunca tendría, enmascarando el bug real).
4. Un 500 visto una sola vez en un endpoint de catálogo/listado, que
   desaparece al reintentar inmediatamente, es casi siempre el hallazgo
   ya documentado de conexión obsoleta del pool (ver "Hallazgos
   empíricos de MonetDB" más abajo) -- reintentar 2-3 veces antes de
   investigarlo como bug nuevo, pero **nunca asumirlo sin reintentar y
   confirmar**: no dar por sentado que "seguro es eso" sin verificarlo.

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
- **Responder siempre en español** -- todo texto dirigido al usuario (explicaciones,
  resúmenes, preguntas, nombres de archivos de plan/spec cuando aplique), sin excepción,
  independientemente del idioma en que esté escrito el código o la documentación técnica
  en inglés (nombres de variables, commits si el usuario no pide otra cosa, etc.).
- **No verificar cambios de frontend en el navegador de forma automática.**
  Regla vigente desde S1.16, reafirmada explícitamente el 2026-08-08: tras editar
  `apps/web`/`apps/fids-player`, NO usar las herramientas de Browser pane
  (`preview_start`/`navigate`/`read_page`/etc.) por iniciativa propia para
  verificar el resultado -- alcanza con que el build de producción
  (`npx nx build web --configuration=production`) quede en verde. Verificar en
  navegador real **solo cuando el usuario lo pida explícitamente** (p. ej. "pruébalo
  en el navegador", "verifica que se vea bien"). Si no se pidió, decirlo
  explícitamente en la respuesta ("no verificado en navegador real, build en verde")
  en vez de asumir que hace falta.

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
  el token caduca (30 min desde el 2026-08-05, pedido directo del usuario --
  era 15 min desde S1.2) o sus permisos quedaron obsoletos tras un cambio de rol.
  Patrón de componente: standalone, todo el estado en `signal()`, `inject()` para
  DI, manejo de error uniforme vía `mensajeDeError(err)`. `<input type="datetime-local">`
  no lleva zona horaria — convertir a UTC con un helper tipo `aUtcIso()` antes de
  enviar al backend.

## Hallazgos empíricos de MonetDB (ver también `docs/runbooks/monetdb.md`)

- **No es de MonetDB, es del guardián propio** (`packages/repository/guard.py`),
  pero se documenta aquí por ser el mismo tipo de trampa silenciosa: `_tiene_filtro_tenant`
  (G2) solo inspecciona la cláusula `WHERE` de un `SELECT` -- un filtro de
  tenant puesto únicamente en la condición `ON` de un `JOIN`/`outerjoin`
  no lo satisface, aunque sea lógicamente equivalente y MonetDB lo
  ejecutaría bien. Repetir el filtro también en `WHERE` (con `| columna.is_(None)`
  si el JOIN es `LEFT` y la tabla puede no tener fila coincidente).
  Encontrado en `aerohub_aodb/infrastructure/consultas.py::listar_vuelos`
  (Fase 3 de `docs/diseno/PLAN_CORRECCION_MODULOS.md`, 2026-08-07).
- `GRANT` repetido sobre el mismo privilegio falla con
  `01007!GRANT: User/role '<rol>' already has this privilege` --
  MonetDB no lo trata como no-op idempotente. Encontrado al reaplicar
  `db/migrations/apply.py` desde cero (2026-08-06/07): `92_grants_tenants.sql`
  y `99_grants_identidad.sql` otorgaban el mismo
  `GRANT ... ON tenants.invitacion TO role_tenant_admin` dos veces --
  nunca se había vuelto a correr el DDL completo contra un volumen
  realmente vacío desde que el segundo archivo se creó en S1.10.
  Cualquier `GRANT` nuevo debe revisarse contra los archivos de grants
  ya existentes de la misma tabla antes de agregarse.
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
- `GROUP BY` sobre una columna referenciada en su forma completa de 3
  partes `esquema.tabla.columna` (lo que SQLAlchemy Core genera por
  defecto al agrupar sobre `tabla.c.columna` directamente) es rechazado
  con `42000!SELECT: cannot use non GROUP BY column ... without an
  aggregate function`, **incluso cuando esa columna exacta está en el
  `GROUP BY`** y sin ninguna función agregada de por medio -- reproducido
  con una consulta tan simple como
  `SELECT ops.vuelo.aerolinea_id, count(*) FROM ops.vuelo GROUP BY
  ops.vuelo.aerolinea_id`. Se resuelve con un alias de tabla
  (`tabla.alias("v")`): SQLAlchemy compila entonces `v.columna` (2
  partes) en vez de `esquema.tabla.columna` (3 partes), y MonetDB lo
  acepta. Encontrado en
  `aerohub_aodb/infrastructure/consultas_informe.py::agrupar_vuelos_por_aerolinea`
  (S1.18) -- aplicar el mismo alias a todo `GROUP BY` nuevo sobre una
  tabla de `schema="..."`.
- `sqlalchemy-monetdb` ya deserializa columnas `JSON` a `dict`/`list` en
  la lectura (hallazgo original de S1.9) -- un `select(tabla)` completo
  sobre una tabla con columna(s) `JSON` (p. ej. `compliance.log_auditoria.
  valores_nuevos`) vuelve a intentar `json.loads()` sobre un `dict` ya
  deserializado y falla con `TypeError: the JSON object must be str,
  bytes or bytearray, not dict`. Reproducido de nuevo en S1.18 al hacer
  `select(log_auditoria)` para un informe -- la fila no necesitaba esas
  columnas. Corregido seleccionando solo las columnas escalares
  necesarias (`select(tabla.c.col1, tabla.c.col2, ...)`) en vez de la
  tabla completa.
- `JOIN` contra una subconsulta con `GROUP BY` (patrón "última fila por
  grupo": `JOIN (SELECT col, max(version) ... GROUP BY col)`) es rechazado
  con `42000!SELECT: cannot use non GROUP BY column ... without an
  aggregate function`, aunque el `GROUP BY` vive enteramente dentro de la
  subconsulta. Usar un anti-join `NOT EXISTS` correlacionado contra un
  alias de la misma tabla en su lugar (funciona en MonetDB y es más
  portable entre motores). Encontrado en
  `aerohub_fids/infrastructure/consultas.py::listar_plantillas` (S1.16).

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
