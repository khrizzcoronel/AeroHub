# Quickstart: Informes operativos (S1.18)

Prerrequisitos: stack en Docker, sesión con acceso a cada módulo, tenant
canario MEC con datos sembrados.

## Escenario 1 — Informe simple con filtros de período (US1)

1. Abrir "Informes" en cualquier módulo (p. ej. AODB).
2. Fijar un rango de fechas conocido → **Esperado**: la tabla muestra
   exactamente las filas de ese período.
3. Exportar → **Esperado**: el CSV descargado tiene las mismas filas.

## Escenario 2 — Informe compuesto con subtotales reconciliables (US2)

1. Abrir el informe compuesto de Billing (facturación por aerolínea ×
   concepto) para un período con al menos 2 aerolíneas facturadas.
2. **Esperado**: cada grupo muestra su subtotal; sumar todos los
   subtotales a mano da exactamente el total general mostrado.
3. Comparar contra la vista de facturas (`billing/facturas`) del mismo
   período → **Esperado**: los montos coinciden (SC-003).

## Escenario 3 — Parámetros declarados en el artefacto exportado (US3)

1. Exportar cualquier informe con filtros no triviales.
2. **Esperado**: el CSV abierto en un editor de texto muestra, antes de
   las filas, el período y demás filtros usados, y la fecha/hora de
   generación.

## Escenario 4 — Auditoría de emisión (US4)

1. Emitir el informe compuesto de Billing o de Compliance.
2. Consultar el log de auditoría (`compliance.log_auditoria`, vía SQL
   admin o el endpoint correspondiente) → **Esperado**: aparece una
   entrada nueva con el usuario y la fecha/hora.
3. Emitir el informe de cualquiera de los otros 4 módulos → **Esperado**:
   NO aparece entrada nueva de auditoría por esta causa.

## Verificación empírica (no manual)

- `pytest tests/integration/test_{aodb,gates,ramp,billing,tenancy,compliance}_informes.py`
  contra MonetDB real -- cada suite verifica SC-002 (suma de subtotales
  == total) sobre datos reales; `test_billing_informes.py` verifica
  además SC-003 (conciliación con facturas emitidas).
- `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre los 6 servicios.
- Build de producción de `apps/web`.
