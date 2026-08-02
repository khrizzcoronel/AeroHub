# Contrato: preflight de conmutación (`tools/continuidad_conmutar.py`, C4)

No es un mecanismo automático de failover (research.md Decisión 8) -- es
una herramienta de verificación previa que una persona con autorización
de plataforma ejecuta a mano quien decide conmutar, y el runbook completo
que acompaña la decisión.

## Invocación

```text
uv run python tools/continuidad_conmutar.py --standby monetdb-standby
```

- Consulta `continuidad.shipper_checkpoint` y el `lsn` máximo actual de
  `continuidad.journal_mutacion` para calcular el atraso pendiente.
- Si el atraso es `0` (réplica al día): imprime el nuevo valor de
  `AEROHUB_DB_DSN` a aplicar y los pasos exactos del runbook
  (`docs/runbooks/continuidad_failover.md`). Código de salida `0`.
- Si el atraso es mayor que `0` pero por debajo del umbral de alerta (120
  s): imprime una advertencia con el atraso exacto y los mismos pasos,
  dejando la decisión final a la persona que ejecuta el comando. Código
  de salida `0`.
- Si el atraso supera el umbral de alerta: imprime un error explícito
  indicando cuántos segundos de posible pérdida de datos implica conmutar
  en ese momento. Código de salida `1` -- no imprime los pasos de
  conmutación como si fueran seguros de aplicar sin más consideración.

## Lo que este script NUNCA hace

- No reinicia contenedores.
- No cambia variables de entorno ni archivos de configuración.
- No decide por sí solo si el primario "está caído" -- esa determinación
  (el *health check* de C4) la hace la persona que ejecuta el
  procedimiento, siguiendo `docs/runbooks/continuidad_failover.md`.

## `docs/runbooks/continuidad_failover.md`

Documenta, en pasos numerados: (1) cómo confirmar que el fallo del
primario es real y no transitorio; (2) cuándo ejecutar
`continuidad_conmutar.py` y cómo interpretar su salida; (3) el cambio
concreto de `AEROHUB_DB_DSN` y el reinicio del `gateway` apuntando al
standby; (4) verificación de consistencia post-conmutación; (5) qué hacer
si el primario original vuelve a estar disponible (spec.md, Edge Cases:
el runbook deja explícito si corresponde reconmutar o si el standby pasa
a ser la nueva referencia).
