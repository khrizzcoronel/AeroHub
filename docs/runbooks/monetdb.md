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

## Segunda instancia (standby)

`monetdb-standby` corre la misma imagen en el puerto `50001`, con el mismo `MDB_CREATE_DBS: aerohub`. No recibe tráfico de aplicación en operación normal — solo el *shipper* de continuidad (ADR-018, componente C3, Sprint S1.9) escribe en ella.

```bash
docker exec -it aerohub-monetdb-standby sh -c "printf 'user=monetdb\npassword=aerohub\n' > /tmp/.monetdb && cd /tmp && mclient -d aerohub"
```

## Problemas conocidos

- Si el contenedor no arranca sano tras un `docker compose down -v`, el volumen puede haber quedado en estado inconsistente; recrearlo con `docker volume rm infra_monetdata` (el nombre del volumen lleva el prefijo del directorio de `infra/docker-compose.yml`, no `aerohub_`) antes de reintentar.
- `mclient` no viene instalado en el host por defecto — usar `docker exec -it aerohub-monetdb mclient ...` en vez de instalarlo localmente, salvo que el equipo lo requiera para depuración frecuente.
- **Referencia de columna calificada a 3 partes (`schema.vista.columna`) en un `WHERE` sobre una VISTA falla** con `42S22!SELECT: no such column` (verificado S1.1, `ops.v_vuelo_estado_actual`) — el mismo patron de 3 partes funciona sin problema contra tablas reales (`ops.vuelo`, etc.), y contra la vista funciona si la columna se califica solo a 2 partes (`vista.columna`) o sin calificar. SQLAlchemy Core siempre genera el nombre a 3 partes en el `WHERE` para una `Table` con `schema=` declarado, asi que cualquier consulta parametrizada de aplicacion contra una vista con columnas del mismo nombre que la tabla base debe reimplementar la logica de la vista directamente sobre la tabla base (ver `services/aodb/aerohub_aodb/infrastructure/consultas.py::obtener_estado_vuelo_actual_por_id`) en vez de seleccionar desde la vista. La vista en si sigue siendo DDL valida para consumidores que no filtran con columnas calificadas (reportes, `mclient` interactivo).
