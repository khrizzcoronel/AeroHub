# Contrato: compuerta de error budget (`tools/verificar_error_budget.py`)

No es un endpoint HTTP — es un script invocable desde CI/CD y a mano
(research.md Decisión 2).

## Invocación normal

```text
uv run python tools/verificar_error_budget.py --servicio aodb
```

- Consulta `http://<prometheus>/api/v1/query` por el consumo de error
  budget del servicio en el período mensual en curso.
- Código de salida `0` si el consumo es `< 80%`.
- Código de salida `1` (bloquea el pipeline que lo invoque) si el
  consumo es `>= 80%`, imprimiendo el porcentaje observado.

## Invocación con override

```text
uv run python tools/verificar_error_budget.py --servicio aodb \
    --override --motivo "release critica aprobada por on-call, ver INC-123"
```

- Si el consumo es `>= 80%` y se pasa `--override` con `--motivo`
  no vacío: escribe un evento de auditoría
  (`registrar_auditoria(esquema="observabilidad",
  tabla="bloqueo_despliegue", operacion="UPDATE",
  valores_nuevos={"servicio": ..., "consumo_pct": ..., "motivo": ...})`)
  y termina con código `0`.
- Si `--override` se pasa sin `--motivo`: error de uso, código `2`,
  no se despliega ni se audita nada (no hay override silencioso).
- Si el consumo es `< 80%`: el flag `--override` no tiene efecto
  (no hay nada que levantar), termina `0` sin auditar.
