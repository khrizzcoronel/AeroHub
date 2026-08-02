# Quickstart: validación de S1.9

Prerrequisito: stack en Docker corriendo, incluidos los servicios nuevos
de este sprint:

```bash
docker compose -f infra/docker-compose.yml up -d monetdb monetdb-standby monetdb-restore-test minio prometheus continuidad-agente
```

DDL aplicado (`db/ddl/monetdb/15_continuidad_snapshot.sql` +
`99_grants_continuidad_ext.sql`) sobre primario, standby y contenedor de
restauración.

## Escenario 1 — Punto de partida recuperable siempre disponible (US1)

1. Forzar un ciclo de snapshot: `uv run python tools/continuidad_agente.py --forzar-snapshot programado`.
2. Consultar `continuidad.snapshot_base` -- verificar una fila nueva con
   `estado='verificado'`, `lsn_corte` y `hash_artefacto` no nulos.
3. Verificar en MinIO que el artefacto referenciado por `ruta_artefacto`
   existe y su tamaño es mayor que cero.

## Escenario 2 — Réplica caliente con atraso siempre visible (US2)

1. Insertar una mutación sintética en el primario (p. ej. crear un ticket
   de soporte cualquiera vía la API).
2. Verificar que, tras el siguiente ciclo del *shipper*, la fila
   equivalente aparece en `monetdb-standby` con los mismos valores.
3. Reintentar aplicar manualmente la misma entrada del journal (mismo
   `lsn`) -- verificar que no produce error ni una segunda fila.
4. `GET /metrics` de `continuidad-agente` -- verificar que
   `aerohub_standby_lag_seconds` refleja un valor consistente con el
   tiempo transcurrido desde la última mutación sin aplicar (o `0` si ya
   se aplicó todo).

## Escenario 3 — Conmutación desde un único punto (US3)

1. Detener el acceso al primario de forma simulada (p. ej. pausar el
   contenedor `monetdb`).
2. Ejecutar `uv run python tools/continuidad_conmutar.py --standby monetdb-standby`
   -- verificar que reporta el atraso pendiente y, si es seguro, el nuevo
   DSN a aplicar.
3. Aplicar el cambio de `AEROHUB_DB_DSN` sobre el `gateway` (siguiendo
   `docs/runbooks/continuidad_failover.md`) y verificar que la aplicación
   completa sirve tráfico desde el standby, sin que ninguna ruta quede
   apuntando al contenedor pausado.

## Escenario 4 — Evidencia semanal automática de recuperación (US4)

1. Forzar una ejecución de la prueba de restauración:
   `uv run python tools/continuidad_agente.py --forzar-prueba-restauracion`.
2. Verificar que `monetdb-restore-test` queda con los datos del último
   snapshot verificado.
3. Consultar `continuidad.prueba_restauracion` -- verificar una fila nueva
   con `rto_observado_segundos`, `rpo_observado_segundos` y
   `resultado='exitosa'`.
4. `GET /metrics` -- verificar que `aerohub_prueba_restauracion_rto_segundos`
   y `..._rpo_segundos` reflejan la corrida más reciente.

## Escenario 5 — El registro de cambios no crece sin límite (US5)

1. Con entradas sintéticas de `journal_mutacion` más antiguas que 48 h
   (fixture de prueba, sin esperar 48 h reales) y `shipper_checkpoint`
   confirmando que ya se aplicaron, ejecutar el ciclo de purga.
2. Verificar que esas entradas desaparecen de `journal_mutacion`.
3. Repetir con una entrada igual de antigua pero CON `lsn` mayor al
   último confirmado en `shipper_checkpoint` -- verificar que esa entrada
   NO se purga.
