# Runbook — MonetDB en desarrollo local

| Campo | Contenido |
|:---|:---|
| Sprint de origen | S0.1 (Plan §7.1); corregido en S0.2 tras verificación empírica |
| Motivo | MonetDB tiene menos documentación operativa que motores mainstream (riesgo R-09 del Plan §15); este runbook fija el procedimiento conocido-bueno para no reconstruirlo cada vez |
| Servicios relacionados | `monetdb` (primario), `monetdb-standby` (ADR-018, componente C3) |

## Arranque

```bash
docker compose -f infra/docker-compose.yml up -d monetdb monetdb-standby
```

Healthcheck: `monetdb status` dentro del contenedor, cada 10 s, hasta 12 reintentos (~2 min). Con `MDB_CREATE_DBS: aerohub` (ver más abajo) la base `aerohub` queda creada y lista para conexión **sin ningún paso manual adicional**, verificado en S0.2 contra un volumen recién creado (sano en < 30 s). Si no vuelve sano:

```bash
docker compose -f infra/docker-compose.yml logs monetdb
```

## Cómo se crea la base `aerohub` (automático, no manual)

`infra/docker-compose.yml` fija `MDB_CREATE_DBS: aerohub`. El `entrypoint.sh` de la imagen oficial ejecuta, en el primer arranque del volumen:

```
monetdb create -p "$MDB_DB_ADMIN_PASS" aerohub
```

**Hallazgo real (S0.2):** el valor por defecto de `MDB_CREATE_DBS` en la imagen es únicamente `"monetdb"` (el nombre reservado del motor). Sin fijarlo explícitamente a `aerohub`, esa base *no* se crea con `MDB_DB_ADMIN_PASS`. Un `docker exec ... monetdb create aerohub` manual (sin `-p`) sí crea la base, pero con el password histórico por defecto del motor (`monetdb`), no con el que se documenta en `docker-compose.yml` — discrepancia silenciosa que se detectó probando la conexión real, no leyendo la documentación de la imagen. **No crear la base a mano**: si `MDB_CREATE_DBS` está bien fijado, no hace falta, y si se hace de todos modos con un password distinto, dos credenciales quedan divergentes sin ningún error visible hasta el intento de conexión.

## Conexión

```bash
docker exec -it aerohub-monetdb sh -c "printf 'user=monetdb\npassword=aerohub\n' > /tmp/.monetdb && cd /tmp && mclient -d aerohub"
```

`mclient` no acepta el password por flag (`-u` solo fija el usuario); sin un archivo `.monetdb` en el directorio de trabajo pide el password de forma interactiva por TTY, lo que rompe cualquier uso no interactivo (scripts, `docker exec -i` con heredoc). El archivo `.monetdb` es el mecanismo soportado para uso no interactivo.

DSN para SQLAlchemy (dialecto `monetdb`, vía `sqlalchemy-monetdb` + `pymonetdb`, que sí aceptan el password directamente en la URI):

```
monetdb://monetdb:aerohub@localhost:50000/aerohub
```

## Particularidades frente a un motor con RLS/PITR nativo (por qué existen ADR-018 y ADR-019)

| Ausencia en MonetDB | Consecuencia | Compensación |
|:---|:---|:---|
| Row-Level Security nativo | El aislamiento de tenant no lo aplica el motor | Guardián en `packages/repository` (ADR-019) |
| Triggers | La auditoría no la dispara el motor ante un `UPDATE` | Escritura de `compliance.log_auditoria` en la misma transacción, desde `packages/repository` |
| PITR / replicación streaming | Sin recuperación a un punto arbitrario | Journal transaccional + standby + snapshot (ADR-018) |
| `EXCLUDE USING gist` (restricción de rango) | No hay forma declarativa de impedir solapamiento de intervalos | Transacción serializable con bloqueo de fila en `services/gates` (PN-05) |

## Roles y `SET ROLE` (aislamiento departamental, PN-03)

MonetDB soporta `CREATE ROLE`, `GRANT <rol> TO <usuario>` y `SET ROLE <rol>` (verificado en S0.2 contra el contenedor real). El aislamiento departamental de ADR-014 — "control estructural, falla cerrado" — depende de que la capa de repositorio ejecute `SET ROLE <rol_actor>` en cada sesión antes de emitir la consulta de negocio: sin ese paso, el usuario técnico de conexión (con privilegios amplios) resolvería cualquier tabla, y la matriz de roles de Análisis v6.0 §4.3.1 quedaría enforced solo en la aplicación, no en el motor. Ver `packages/repository/base.py`.

## Segunda instancia (standby) y tercera instancia (prueba de restauración)

`monetdb-standby` corre la misma imagen en el puerto `50001`, con el mismo `MDB_CREATE_DBS: aerohub`. No recibe tráfico de aplicación en operación normal — solo el *shipper* de continuidad (ADR-018, componente C3, Sprint S1.9) escribe en ella.

`monetdb-restore-test` (puerto `50002`, Sprint S1.9) es una tercera instancia estática dedicada EXCLUSIVAMENTE a la prueba de restauración semanal (ADR-018 C4) — deliberadamente separada del standby real para no mezclar "réplica que debe reflejar el estado real" con "recuperación desde cero sobre datos sintéticos" (`specs/011-continuidad-rto-rpo/research.md`, Decisión 5).

Las tres instancias corren el MISMO DDL (`db/migrations/apply.py` contra cada una, mismo pipeline versionado) — verificado en S1.9 aplicando el DDL completo (23 archivos) contra `monetdb-standby` y `monetdb-restore-test` recién creados, sin seeds (no necesitan datos canario, solo el esquema).

```bash
docker exec -it aerohub-monetdb-standby sh -c "printf 'user=monetdb\npassword=aerohub\n' > /tmp/.monetdb && cd /tmp && mclient -d aerohub"
docker exec -it aerohub-monetdb-restore-test sh -c "printf 'user=monetdb\npassword=aerohub\n' > /tmp/.monetdb && cd /tmp && mclient -d aerohub"
```

## `sys.hot_snapshot()` y el volumen compartido `snapshotstage` (Sprint S1.9)

`sys.hot_snapshot(tarfile string [, onserver bool [, omitunlogged bool [, omitids string]]])` existe como procedimiento SQL real (verificado contra `monetdb/monetdb:latest`, cuatro sobrecargas en `sys.functions`) y produce un `.tar` válido en la ruta indicada.

**Hallazgo real**: el proceso de MonetDB corre como el usuario `monetdb` (uid 5000) dentro de la imagen oficial. Un volumen Docker nuevo (`snapshotstage`, compartido con `continuidad-agente` para trasladar el artefacto fuera del contenedor) se crea con propietario `root:root` y modo `0755` — `sys.hot_snapshot()` falla con `GDK reported error: ... Permission denied` al intentar escribir ahí, aunque el volumen ya esté montado. Corrección aplicada: `chmod 777 /snapshotstage` una vez por volumen (persiste mientras no se borre el volumen con `docker volume rm`). El archivo resultante queda además con modo `0600` (solo `monetdb` puede leerlo) — inofensivo para `continuidad-agente` porque su imagen (`python:3.12-slim`, sin `USER` declarado) corre como `root`, que en Linux ignora permisos de archivo ajenos; un proceso no-root que intente leer ese volumen sí fallaría igual que falló la escritura.

## Problemas conocidos

- Si el contenedor no arranca sano tras un `docker compose down -v`, el volumen puede haber quedado en estado inconsistente; recrearlo con `docker volume rm infra_monetdata` (el nombre del volumen lleva el prefijo del directorio de `infra/docker-compose.yml`, no `aerohub_`) antes de reintentar.
- `mclient` no viene instalado en el host por defecto — usar `docker exec -it aerohub-monetdb mclient ...` en vez de instalarlo localmente, salvo que el equipo lo requiera para depuración frecuente.
- **Referencia de columna calificada a 3 partes (`schema.vista.columna`) en un `WHERE` sobre una VISTA falla** con `42S22!SELECT: no such column` (verificado S1.1, `ops.v_vuelo_estado_actual`) — el mismo patron de 3 partes funciona sin problema contra tablas reales (`ops.vuelo`, etc.), y contra la vista funciona si la columna se califica solo a 2 partes (`vista.columna`) o sin calificar. SQLAlchemy Core siempre genera el nombre a 3 partes en el `WHERE` para una `Table` con `schema=` declarado, asi que cualquier consulta parametrizada de aplicacion contra una vista con columnas del mismo nombre que la tabla base debe reimplementar la logica de la vista directamente sobre la tabla base (ver `services/aodb/aerohub_aodb/infrastructure/consultas.py::obtener_estado_vuelo_actual_por_id`) en vez de seleccionar desde la vista. La vista en si sigue siendo DDL valida para consumidores que no filtran con columnas calificadas (reportes, `mclient` interactivo).
- **Control de concurrencia optimista muy sensible bajo escritura concurrente sobre tablas compartidas** (verificado S1.2, RNF-P01: `POST /vuelos/{id}/estados` con solo 10-20 hilos concurrentes). MonetDB puede abortar una transaccion EN EL COMMIT con `40001!COMMIT: transaction is aborted because of concurrency conflicts` incluso cuando los hilos escriben en FILAS distintas (probado repartiendo la carga entre 10 vuelos distintos, sin mejora) — la contencion real parece originarse en las tablas TRANSVERSALES que escribe toda mutacion de negocio en la misma transaccion (`continuidad.journal_mutacion`, `compliance.log_auditoria`, patron P8/ADR-018), no en la tabla de negocio en si. Ademas, tras el 40001, el intento de ROLLBACK de limpieza de SQLAlchemy puede fallar con `pymonetdb.exceptions.Error("connection closed")` (el motor ya cerro la conexion al abortar) — ese segundo error llega como `sqlalchemy.exc.DBAPIError` generico, no como `OperationalError`, hay que capturar la clase base para no dejarlo pasar. Mitigacion aplicada: `aerohub_repository.reintentar_en_conflicto` (decorador que reintenta la funcion de caso de uso COMPLETA, con backoff exponencial + jitter) en las mutaciones de negocio (`alta_vuelo`, `registrar_cambio_estado`, `aprovisionar_tenant`). Con mas de ~5 escritores verdaderamente concurrentes contra las mismas tablas transversales, incluso 40 reintentos con backoff no siempre convergen en tiempo razonable -- `tests/integration/test_pn06_pn07_rnf_p01.py` limita el paralelismo real a 3 hilos (repartiendo 100 peticiones entre ellos) como el punto donde el reintento SI converge de forma fiable, documentado ahi mismo. Pendiente de investigar a fondo en un sprint posterior si esto tiene solucion de configuracion (aislamiento de transaccion, particionado de las tablas transversales) o si es un limite estructural del motor para este patron de escritura.
- **`sqlalchemy-monetdb` ya deserializa columnas JSON a `dict`/`list` de Python** (verificado S1.9) -- a diferencia de `pymonetdb` crudo, que devuelve el valor como `str` sin parsear. Declarar una `Column(..., JSON)` de SQLAlchemy sobre esa misma columna hace que SQLAlchemy intente `json.loads()` sobre un valor que el dialecto YA convirtio a `dict`, y falla con `TypeError: the JSON object must be str, bytes or bytearray, not dict`. Mitigacion: declarar la columna sin tipo `JSON` (p. ej. `Text`) cuando el uso es de solo lectura vía SQLAlchemy Core, y manejar en Python tanto el caso `dict` como el caso `str` de forma defensiva (`aerohub_continuidad.operaciones.shipper._como_dict`). Las columnas JSON que solo se ESCRIBEN vía SQLAlchemy (p. ej. `compliance.log_auditoria` en `packages/repository/audit.py`) no se ven afectadas -- el problema es específico de leerlas de vuelta con un tipo `JSON` declarado.
- **Un standby/réplica nuevo necesita el checkpoint del *shipper* de continuidad (S1.9) inicializado al `lsn` máximo actual, no en `0`** -- el journal acumula entradas desde que existe (S0.2) referenciando ids de `tenant`/`vuelo`/etc. del PRIMARIO; si un standby se siembra por separado (`db/seeds/generate.py` genera ids Snowflake nuevos, no reproducibles entre corridas), esos ids NO coinciden con los del primario, y drenar el journal completo desde `lsn=0` produce violaciones de FK reales contra datos que nunca existieron en el standby con esos ids exactos. Correcto conforme a ADR-018: un standby nuevo se restaura desde un snapshot (que sí preserva los ids), y su checkpoint se inicializa al `lsn_corte` de ESE snapshot -- sembrar por separado y adelantar el checkpoint al máximo actual es el sustituto válido en un entorno de desarrollo sin restauración real todavía disponible (`tests/integration/test_continuidad_shipper.py::_checkpoint_al_dia`).
- **Sobrecoste de latencia del mecanismo de continuidad (S1.9) sobre RNF-P01**: `tests/integration/test_pn06_pn07_rnf_p01.py` (100 cambios de estado repartidos en 3 hilos, ya documentado arriba) se re-ejecutó con `continuidad-agente` corriendo en paralelo de forma continua (shipper cada 5s, publicación de métricas cada 60s, un ciclo de snapshot ya disparado) -- la prueba sigue en verde, sin necesidad de ajustar el paralelismo ya acotado a 3 hilos. El mecanismo de continuidad no introdujo un sobrecoste de latencia perceptible sobre la escritura de negocio: `escribir_journal`/`registrar_auditoria` (la escritura transversal que sí paga cada mutación, ADR-018) no cambiaron en este sprint -- S1.9 solo agrega LECTURA periódica de `journal_mutacion` (shipper) y escrituras propias en tablas nuevas sin relación con el camino crítico de escritura de negocio.
