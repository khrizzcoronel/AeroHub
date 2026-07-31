# Runbook — MonetDB en desarrollo local

| Campo | Contenido |
|:---|:---|
| Sprint de origen | S0.1 (Plan §7.1) |
| Motivo | MonetDB tiene menos documentación operativa que motores mainstream (riesgo R-09 del Plan §15); este runbook fija el procedimiento conocido-bueno para no reconstruirlo cada vez |
| Servicios relacionados | `monetdb` (primario), `monetdb-standby` (ADR-018, componente C3) |

## Arranque

```bash
docker compose -f infra/docker-compose.yml up -d monetdb monetdb-standby
```

Healthcheck: `monetdb status` dentro del contenedor, cada 10 s, hasta 12 reintentos (~2 min). Si no vuelve sano:

```bash
docker compose -f infra/docker-compose.yml logs monetdb
```

## Crear la base `aerohub` (una sola vez por volumen)

```bash
docker exec -it aerohub-monetdb monetdb create aerohub
docker exec -it aerohub-monetdb monetdb release aerohub
```

`monetdb create` deja la base en estado `maintenance`; `monetdb release` la pone `running` — sin este segundo paso ninguna conexión cliente la alcanza.

## Conexión

```bash
mclient -u monetdb -d aerohub
```

Contraseña por defecto en el contenedor: `monetdb` (cambiar antes de cualquier entorno compartido — variables `MDB_DB_ADMIN_PASS` / `MDB_DAEMON_PASS` en `infra/docker-compose.yml`).

DSN para SQLAlchemy (dialecto `monetdb`, via `sqlalchemy-monetdb` + `pymonetdb`):

```
monetdb://monetdb:monetdb@localhost:50000/aerohub
```

## Particularidades frente a un motor con RLS/PITR nativo (por qué existen ADR-018 y ADR-019)

| Ausencia en MonetDB | Consecuencia | Compensación |
|:---|:---|:---|
| Row-Level Security nativo | El aislamiento de tenant no lo aplica el motor | Guardián en `packages/repository` (ADR-019) |
| Triggers | La auditoría no la dispara el motor ante un `UPDATE` | Escritura de `compliance.log_auditoria` en la misma transacción, desde `packages/repository` |
| PITR / replicación streaming | Sin recuperación a un punto arbitrario | Journal transaccional + standby + snapshot (ADR-018) |
| `EXCLUDE USING gist` (restricción de rango) | No hay forma declarativa de impedir solapamiento de intervalos | Transacción serializable con bloqueo de fila en `services/gates` (PN-05) |

## Segunda instancia (standby)

`monetdb-standby` corre la misma imagen en el puerto `50001`. No recibe trafico de aplicación en operación normal — solo el *shipper* de continuidad (ADR-018, componente C3, Sprint S1.9) escribe en ella. Para inspeccionarla manualmente:

```bash
docker exec -it aerohub-monetdb-standby monetdb create aerohub
docker exec -it aerohub-monetdb-standby monetdb release aerohub
mclient -h localhost -p 50001 -u monetdb -d aerohub
```

## Problemas conocidos

- Si el contenedor no arranca sano tras un `docker compose down -v`, el volumen `monetdata`/`monetdata-standby` puede haber quedado en estado inconsistente; recrearlo con `docker volume rm aerohub_monetdata` antes de reintentar.
- `mclient` no viene instalado en el host por defecto — usar `docker exec -it aerohub-monetdb mclient ...` en vez de instalarlo localmente, salvo que el equipo lo requiera para depuración frecuente.
