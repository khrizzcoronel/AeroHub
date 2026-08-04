# Quickstart: Tarifarios y conciliación de pax (S1.17)

Prerrequisitos: stack en Docker (`docker compose -f infra/docker-compose.yml
up -d monetdb gateway web`), sesión con `role_tenant_admin` o
`role_billing_officer` (ambos con `billing:escribir`), tenant canario MEC.

## Escenario 1 — Publicar y activar un tarifario sin SQL manual

1. Iniciar sesión, ir a "Tarifarios y conciliación" (enlace nuevo del
   menú lateral, visible por scope `billing:escribir`).
2. "Nuevo tarifario" → nombre, moneda `USD`, vigente desde hoy.
3. Sobre el tarifario recién creado (estado "borrador"), agregar al
   menos un concepto del catálogo con su tarifa unitaria.
4. "Activar" → el modal muestra el aviso de que los cargos/facturas ya
   emitidos con el tarifario vigente actual no cambian → confirmar.
5. **Esperado**: el tarifario pasa a estado "vigente" en la tabla; si
   había otro vigente en la misma moneda, ahora aparece como histórico.

## Escenario 2 — Ver historial completo de tarifarios

1. Con al menos 2 tarifarios de la misma moneda (uno vigente, uno
   histórico tras el Escenario 1), abrir la vista.
2. **Esperado**: ambos aparecen en la tabla con su estado distinguible;
   al ver el detalle de cada uno, sus conceptos con tarifa unitaria son
   visibles.

## Escenario 3 — Registrar y conciliar pasajeros

1. En la sección "Conciliación de pax", registrar una conciliación para
   un vuelo canario y un período, con conteo de aerolínea y de sistema
   distintos (p. ej. 150 vs 148).
2. **Esperado**: la diferencia mostrada es `2`, calculada, no editable.
3. Intentar "Conciliar" → **esperado**: rechazado con mensaje claro
   (diferencia distinta de cero).
4. Registrar una segunda conciliación (otro vuelo/período) con conteos
   iguales → diferencia `0` → "Conciliar" → **esperado**: pasa a estado
   conciliado, visible en la tabla.

## Verificación empírica (no manual)

- `pytest tests/integration/test_billing_tarifarios_conciliacion.py` contra
  MonetDB real (Docker) -- cubre los 3 escenarios anteriores sin UI.
- `ruff check services/billing && mypy services/billing/aerohub_billing
  && bandit -r services/billing/aerohub_billing && lint-imports`.
- Build de producción de `apps/web`.
