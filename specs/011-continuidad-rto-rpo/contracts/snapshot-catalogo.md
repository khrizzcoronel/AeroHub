# Contrato: ciclo de snapshot y catálogo (`aerohub_continuidad`, C2)

Corre dentro de `continuidad-agente` (proceso continuo, research.md
Decisión 4) -- no es un endpoint HTTP ni un script de invocación manual
única, aunque `tools/continuidad_agente.py` puede forzar un ciclo fuera
de horario con `--forzar-snapshot {programado|volcado_diario}` para
verificación manual.

## Ciclo programado (cada 6 horas)

1. Invoca `sys.hot_snapshot()` sobre el primario, escribiendo el artefacto
   en el volumen compartido `snapshotstage` (research.md Decisión 6).
2. Calcula el checksum SHA-256 del artefacto resultante.
3. Sube el artefacto a MinIO/S3.
4. Inserta una fila en `continuidad.snapshot_base` con `tipo='programado'`,
   `estado='generado'`, el `lsn_corte` (el `lsn` máximo de
   `journal_mutacion` en el momento de iniciar el snapshot).
5. Verifica la integridad del artefacto ya subido (recalcula el checksum
   desde el objeto en MinIO y lo compara contra el calculado en el paso
   2). Si coincide, actualiza el estado a `'verificado'`; si no, a
   `'corrupto'` -- nunca se borra un artefacto corrupto, queda catalogado
   como tal para diagnóstico (FR-004).

## Ciclo diario (volcado lógico completo)

Mismos pasos 2-5, con `tipo='volcado_diario'` y el mecanismo de volcado
lógico (no `sys.hot_snapshot()`) como origen del artefacto -- independiente
del formato interno del motor (FR-002).

## Consulta "último snapshot utilizable"

Cualquier proceso que necesite el snapshot más reciente para restaurar
(la prueba semanal, C4) consulta:

```sql
SELECT * FROM continuidad.snapshot_base
WHERE estado = 'verificado'
ORDER BY generado_en DESC
LIMIT 1
```

Un snapshot `'generado'` (aún no verificado) o `'corrupto'` NUNCA se
usa como origen de restauración.

## Fallos

Si `sys.hot_snapshot()` falla, o la subida a MinIO falla, o el archivo
local no aparece en el volumen compartido dentro de un tiempo de espera
razonable: NO se inserta fila en `snapshot_base` (no se cataloga un
snapshot que no existe) y el fallo se registra en el log del contenedor
`continuidad-agente` -- el ciclo siguiente (6 h después) reintenta desde
cero; no hay reintento inmediato automático dentro del mismo ciclo.
