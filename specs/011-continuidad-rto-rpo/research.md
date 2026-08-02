# Research: Continuidad operacional (RTO/RPO) (S1.9)

## Decisión 1 — Alcance del cierre de RNF-R01 en este sprint

**Decisión**: este sprint construye los cuatro componentes de ADR-018 y
los pone a publicar métricas reales, pero NO declara cerrado RNF-R01. El
*game day* mensual y la ventana de observación de 4 semanas consecutivas
en verde quedan fuera de alcance -- son actividades de la Fase 4 (S4.2).

**Razón**: la propia fuente normativa lo prohíbe explícitamente (SRS
§2.7, §5.2, §11; ADR-018 "Condición de cierre de RNF-R01"): un mecanismo
recién construido no puede declararse sostenido sin observación en el
tiempo. Tratar este sprint como el cierre sería contradecir la fuente que
se está implementando.

**Alternativas consideradas**: declarar RNF-R01 cerrado si las pruebas de
este sprint pasan una vez -- rechazada, viola la condición de cierre
explícita del propio ADR-018 y del SRS.

## Decisión 2 — `aerohub_continuidad` no sigue las 4 capas de ADR-017 §5.4

**Decisión**: `aerohub_continuidad` vive en `packages/`, con una
estructura simplificada (`domain/` puro + `operaciones/` + `metricas.py`),
no la estructura `domain/application/infrastructure/api` de un módulo de
negocio.

**Razón**: la arquitectura de capas de ADR-017 existe para separar reglas
de negocio de un actor con tenant (dominio) de su exposición HTTP (api) y
su persistencia guardada por tenant (infrastructure). Ninguna de esas
tres nociones aplica aquí: no hay actor de tenant, no hay HTTP expuesto, y
la persistencia no es "las tablas de un módulo" sino una operación de
*replay* genérica sobre CUALQUIER `(esquema, tabla, operación, payload)`
que ya pasó por `journal_mutacion` -- siguiendo el patrón exacto de
`packages/repository` (que tampoco sigue esas 4 capas, por la misma
razón: es infraestructura transversal, no un módulo de negocio).

**Alternativas consideradas**: (a) forzar las 4 capas -- rechazada, exigiría
que `aerohub_continuidad` importe `infrastructure/` de cada módulo de
negocio existente y futuro para poder reconstruir sus `Table()` y
reproducir sus mutaciones, violando directamente la independencia de
módulos (Principio II) que las capas buscan proteger en primer lugar; (b)
construir el *shipper* dentro de cada módulo de negocio (que cada
`infrastructure/comandos.py` sepa "re-aplicarse a sí mismo" contra el
standby) -- rechazada, dispersaría la lógica de replicación en N módulos
en vez de un único punto de responsabilidad, y volvería a violar
independencia de módulos al obligar a un contrato compartido entre todos.

## Decisión 3 — Dos rutas de conexión distintas: lectura guardada del primario, escritura directa al standby

**Decisión**: el *shipper* LEE `continuidad.journal_mutacion` del
primario a través de `aerohub_repository.sesion()` bajo
`alcance_global(motivo="shipper_continuidad", rol="role_platform_admin")`
(mismo patrón que el monitor de señal FIDS, S1.3) -- respeta P1 para la
lectura. Para APLICAR cada entrada sobre el standby usa DOS conexiones
`pymonetdb` directas adicionales (sin pasar por `aerohub_repository`):
una al primario, para re-consultar la fila COMPLETA por `clave_primaria`
(Decisión 9, más abajo -- `payload` es abreviado, no sirve para
reconstruir la fila), y otra al standby, para aplicar esa fila completa
como *UPSERT* genérico.

**Razón**: el standby no es "la base que sirve peticiones de aplicación"
-- es un destino de replicación pasivo, administrado por un proceso de
plataforma, exactamente la misma categoría que ya tiene una excepción
documentada en este proyecto (`db/migrations/apply.py`,
`db/seeds/generate.py`: "conexión admin directa... no una petición de
aplicación con contexto de tenant/rol ya establecido"). El guardián de
tenant (`aerohub_repository.guard`) tampoco podría verificar nada útil
aquí: la entrada del journal YA es la mutación validada y aislada por
tenant en el momento en que ocurrió en el primario; re-verificarla al
aplicarla en el standby sería redundante y, peor, el *replay* genérico no
construye objetos `Table()` tipados por módulo (Decisión 2), que es lo
único que el guardián sabe inspeccionar.

**Alternativas consideradas**: replicar también por `aerohub_repository`
usando los `Table()` de cada módulo -- rechazada por la misma razón que la
Decisión 2 (acoplaría el *shipper* a todos los módulos de negocio).

## Decisión 4 — Proceso continuo propio, no Airflow

**Decisión**: snapshot programado, *shipper* y prueba de restauración
semanal corren como tres ciclos concurrentes dentro de un único
contenedor nuevo de proceso continuo (`continuidad-agente`), mismo patrón
que la tarea de fondo `asyncio` del monitor de señal FIDS en
`services/gateway/main.py` (S1.3) -- no como DAGs de Apache Airflow.

**Razón**: Airflow ya está desplegado desde S0.1, pero el propio plan de
implementación lo reserva explícitamente para la Fase 2 (§9, "Semanas
23-34 · D4 · Medallion + ClickHouse") -- ETL analítico, no continuidad
operacional de la base transaccional. Introducir DAGs de Airflow para un
mecanismo de disponibilidad de Fase 1 adelantaría una pieza de
infraestructura fuera del orden que el propio plan declara, y acoplaría
la disponibilidad del motor operacional a la disponibilidad de Airflow
(un sistema con su propio *scheduler* y *metastore*, ahora mismo SQLite
de un solo executor) -- una dependencia nueva e innecesaria para algo que
un proceso Python continuo con temporizadores resuelve directamente,
igual que ya resuelve el monitor de señal FIDS.

**Alternativas consideradas**: (a) Airflow -- rechazada por lo anterior;
(b) `cron` del sistema operativo dentro del contenedor -- rechazada frente
a un *loop* `asyncio`: cron no ofrece un lugar natural para mantener el
estado en memoria entre ciclos (p. ej. la métrica de atraso debe
publicarse de forma continua, no solo en el instante de una ejecución de
cron) y añade un segundo mecanismo de *scheduling* (cron + el propio
proceso Python) sin necesidad.

## Decisión 5 — Contenedor dedicado y estático para la prueba de restauración, no un contenedor efímero

**Decisión**: `infra/docker-compose.yml` agrega un tercer servicio
MonetDB estático, `monetdb-restore-test`, dedicado exclusivamente a la
prueba de restauración semanal -- se reinicia/limpia antes de cada
ejecución, en vez de crear y destruir un contenedor nuevo por cada
prueba.

**Razón**: crear contenedores dinámicamente desde dentro de
`continuidad-agente` exigiría acceso al *socket* de Docker del host (o al
SDK de Docker) desde un contenedor de aplicación -- una superficie de
privilegio mayor (control total sobre el motor Docker del host) para un
beneficio menor (ahorrar un contenedor inactivo la mayor parte del
tiempo). Un tercer servicio estático, igual que ya se hizo con
`monetdb-standby` desde S0.1, es más simple, más auditable y no requiere
otorgar ese privilegio.

**Alternativas consideradas**: contenedor efímero vía Docker SDK --
rechazada por el motivo anterior; reutilizar el propio `monetdb-standby`
para la prueba -- rechazada, mezclaría el propósito de C3 (réplica que
debe reflejar el estado real para un failover real) con el de C4
(recuperación desde cero sobre datos sintéticos), y una prueba de
restauración que sobrescribe el standby real dejaría al mecanismo de C3
inconsistente durante la prueba.

## Decisión 6 — Artefactos de snapshot: volumen compartido + subida a MinIO

**Decisión**: `sys.hot_snapshot()` escribe su archivo en un volumen
Docker nuevo (`snapshotstage`), montado tanto en `monetdb` como en
`continuidad-agente`. Este último calcula el checksum del archivo, lo
sube a MinIO (cliente S3-compatible, `boto3`) y cataloga el resultado en
`continuidad.snapshot_base` (vía `aerohub_repository`, es una tabla de
plataforma sin necesidad de acceso cross-schema genérico -- a diferencia
del *shipper*, esto SÍ es una simple fila propia).

**Razón**: `sys.hot_snapshot()` corre DENTRO del proceso de MonetDB y
escribe en SU PROPIO sistema de archivos -- sin un volumen compartido, el
archivo resultante sería inalcanzable para cualquier proceso fuera de ese
contenedor. Un volumen compartido es el mecanismo más simple disponible
en Docker Compose para ese traspaso, sin inventar un protocolo de
transferencia de archivos adicional.

**Alternativas consideradas**: exponer un endpoint HTTP en el propio
MonetDB para servir el archivo -- rechazada, MonetDB no ofrece eso
nativamente y construirlo sería una superficie nueva innecesaria frente a
un volumen compartido ya soportado por Compose.

## Decisión 7 — Purga del journal condicionada al avance confirmado del *shipper*

**Decisión**: la purga automática de `continuidad.journal_mutacion`
elimina una entrada únicamente si se cumplen AMBAS condiciones: (a) su
antigüedad supera la ventana de retención (48 h, ya vigente desde S0.2) Y
(b) su `lsn` es menor o igual al último `lsn` confirmado aplicado por el
*shipper* (`continuidad.shipper_checkpoint`).

**Razón**: es la única forma de que la retención por antigüedad (motivada
por no dejar crecer el journal sin límite) y la garantía de RPO del
*shipper* (que necesita poder drenar TODA entrada pendiente, sin importar
su edad, tras una interrupción prolongada) no entren en conflicto -- una
purga que ignorara el avance del *shipper* podría borrar, en un escenario
de interrupción prolongada de la réplica, exactamente los datos que el
*shipper* todavía no había replicado, convirtiendo el propio mecanismo de
retención en una fuente de pérdida de datos (spec.md, Edge Cases).

**Alternativas consideradas**: purgar solo por antigüedad (más simple) --
rechazada, es precisamente el escenario de riesgo que el Edge Case de
spec.md identifica.

## Decisión 8 — La conmutación no se automatiza sin supervisión humana

**Decisión**: `tools/continuidad_conmutar.py` es una herramienta de
*preflight* -- verifica el atraso actual de la réplica, drena lo
pendiente si es seguro hacerlo, e imprime los pasos exactos del runbook
(`docs/runbooks/continuidad_failover.md`) con el nuevo DSN a aplicar. No
reinicia contenedores ni cambia configuración por sí sola. El mecanismo
de conmutación en sí (que la aplicación pueda apuntar a otra base
cambiando `AEROHUB_DB_DSN`) YA EXISTE desde S0.2
(`packages/repository/base.py`) -- este sprint no le agrega código nuevo,
solo el procedimiento guiado y el runbook.

**Razón**: ADR-018 exige que la conmutación pase por "un único punto de
configuración", no que sea automática sin supervisión -- una conmutación
mal disparada (p. ej. por una falla transitoria de red, no una caída
real) es más costosa que un minuto adicional de verificación humana.
Coincide además con el Principio V de la constitución: acciones de alto
impacto y difícil reversión requieren confirmación explícita, nunca
automatización silenciosa.

**Alternativas consideradas**: conmutación completamente automática ante
la primera falla detectada del *health check* -- rechazada, introduce el
riesgo de conmutar innecesariamente ante una falla transitoria,
exactamente el tipo de decisión que ADR-018 reserva para una persona con
autorización de plataforma.

## Hallazgo empírico — `sys.hot_snapshot()` y permisos del volumen compartido

Verificado contra `monetdb/monetdb:latest` real (Docker, fase de
implementación de S1.9): `sys.hot_snapshot(tarfile string [, onserver
bool [, omitunlogged bool [, omitids string]]])` existe como
procedimiento SQL (`sys.functions`, cuatro sobrecargas) y produce un
archivo `.tar` válido en el `tarfile` indicado -- confirma la sintaxis
que ADR-018 asume, sin necesitar adivinarla.

**Hallazgo real no anticipado**: el proceso de MonetDB corre como el
usuario `monetdb` (uid 5000) dentro del contenedor oficial. Un volumen
Docker nuevo se crea con propietario `root:root` y modo `0755` -- sin
ajustar el permiso, `sys.hot_snapshot()` falla con `Permission denied` al
intentar escribir en el volumen compartido `snapshotstage`, aunque el
volumen ya esté montado y exista. El archivo resultante, además, queda
con modo `0600` (solo legible por `monetdb`) -- el contenedor
`continuidad-agente` (imagen `python:3.12-slim`, sin `USER` declarado,
corre como `root`) puede leerlo igual porque `root` en Linux ignora los
permisos de archivo de otros usuarios, pero cualquier proceso NO-root que
intente leer ese volumen compartido fallaría de la misma forma que
`hot_snapshot()` falló al escribir. Documentado en
`docs/runbooks/monetdb.md` para no tener que redescubrirlo.

## Hallazgo empírico — `payload` de `journal_mutacion` es abreviado, no la fila completa

**Hallazgo**: ADR-018 describe `payload` como "estado resultante de la
fila", pero al revisar CADA llamada real a `escribir_journal` desde S1.1
hasta S1.8 (`services/aodb/aerohub_aodb/application/alta_vuelo.py`,
`services/billing/aerohub_billing/application/calcular_facturacion.py`,
`services/compliance/aerohub_compliance/application/gestionar_incidentes.py`,
y el resto de módulos), NINGUNA pasa la fila completa -- todas pasan un
subconjunto abreviado de 2-3 campos, suficiente para una traza forense
("qué cambió"), insuficiente para *reconstruir* la fila (faltan
`tenant_id`, columnas `NOT NULL`, marcas de tiempo, etc.). Es una brecha
real entre la intención del ADR y el uso efectivo en 8 sprints previos,
no algo introducido por este sprint.

**Decisión 9 — el *shipper* re-consulta la fila completa en el primario,
no confía en `payload`**: al ver una entrada `(esquema, tabla,
clave_primaria)` en el journal, el *shipper* usa `clave_primaria` para
`SELECT *` esa fila en el PRIMARIO (conexión `pymonetdb` administrativa
independiente de la de lectura del journal) y replica esa fila COMPLETA
sobre el standby -- nunca construye el `INSERT`/`UPDATE` a partir de
`payload`. La escritura sobre el standby es un *UPSERT* genérico
(`UPDATE` por clave primaria; si afecta cero filas, `INSERT`), idempotente
por construcción independientemente del campo `operacion` registrado.

**Por qué esto no requiere corregir 8 sprints retroactivamente**: cambiar
cada llamada a `escribir_journal` para que lleve la fila completa
tocaría decenas de archivos de todos los módulos de negocio, fuera de
alcance de un sprint de continuidad y con su propio riesgo de regresión
-- exactamente el tipo de expansión de alcance que la constitución pide
señalar en vez de resolver en silencio. La Decisión 9 logra el mismo
resultado (RPO real, réplica consistente) sin tocar ningún módulo de
negocio existente.

**Por qué es seguro pese a no seguir el orden histórico exacto**: el
sistema no permite `DELETE` físico (P5, "toda baja es lógica") -- una
fila prácticamente nunca desaparece, solo se inserta o actualiza. Si el
*shipper* re-consulta DESPUÉS de una actualización posterior a la
entrada que está procesando, obtiene el estado más reciente, no el de
ese instante exacto -- aceptable porque el objetivo declarado es RPO
(cuánto se puede perder si el primario desaparece AHORA), no una
reproducción byte-a-byte del historial intermedio (eso ya lo preserva
`compliance.log_auditoria`/el propio `journal_mutacion`, con otro
propósito). `operacion='DDL'` se omite explícitamente -- los cambios de
esquema se aplican por el pipeline de migraciones versionado (FR-017),
nunca por el *shipper*.

**Alternativas consideradas**: (a) corregir retroactivamente cada
`escribir_journal` para pasar la fila completa -- rechazada por el
alcance y riesgo explicados arriba; (b) tolerar filas incompletas en el
standby -- rechazada, viola el propósito mismo de C3 (una réplica que no
sirve para un failover real no es una réplica).

## Decisión 10 — La prueba de restauración semanal automatizada usa el volcado lógico, no `hot_snapshot()`

**Decisión**: `operaciones/restauracion.py` restaura exclusivamente el
último snapshot verificado de `tipo='volcado_diario'` (el volcado lógico
propio en JSON-lines, ver Decisión de `operaciones/snapshot.py`) sobre
`monetdb-restore-test`, replayando cada fila como *UPSERT* -- nunca
intenta restaurar un artefacto `tipo='programado'` (`sys.hot_snapshot()`,
formato binario).

**Razón**: restaurar un `.tar` de `hot_snapshot()` exige detener el
proceso `mserver5` y reemplazar el contenido de `/var/monetdb5/dbfarm`
con el artefacto ANTES de reiniciarlo -- una operación de control de
proceso/sistema de archivos que ningún procedimiento SQL expone, y que
requeriría acceso al *socket* de Docker o al control de `monetdbd` desde
`continuidad-agente`, exactamente la superficie de privilegio que
research.md Decisión 5 ya rechazó para el contenedor de prueba. El
volcado lógico, en cambio, es un conjunto de filas -- restaurarlo es
"volver a insertarlas", una operación 100% alcanzable por SQL/Python
puro, sin tocar el proceso del motor.

**Consecuencia declarada**: la prueba automatizada de este sprint mide
RTO/RPO del camino de recuperación vía volcado lógico, NO del camino vía
`hot_snapshot()` (más rápido en un desastre real, pero solo restaurable
con intervención manual de infraestructura, documentada como
procedimiento aparte si llegara a necesitarse). No se declara que ambos
caminos midan lo mismo -- el DoD de este sprint exige que el mecanismo
"opere y publique métricas", no que cubra automáticamente cada variante
de restauración posible.

**Alternativas consideradas**: dar acceso al *socket* de Docker a
`continuidad-agente` para poder restaurar `hot_snapshot()` de verdad --
rechazada, mismo motivo que la Decisión 5 (superficie de privilegio
mayor para un beneficio que el volcado lógico ya cubre para el propósito
de la prueba automatizada: demostrar que el mecanismo de restauración
funciona y queda medido).
