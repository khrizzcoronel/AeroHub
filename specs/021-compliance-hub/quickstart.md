# Quickstart: Compliance Hub (S1.19)

Prerrequisitos: stack en Docker, sesión con `role_sre` (post-mortems) o
`role_tenant_admin` (resto), tenant canario MEC.

## Escenario 1 — Post-mortem de punta a punta (US1)

1. Registrar un incidente de seguridad.
2. Crear un post-mortem referenciando ese incidente (`role_sre`).
3. Editar la causa raíz, agregar una acción con responsable y fecha límite.
4. Completar la acción.
5. Publicar el post-mortem → **esperado**: pasa a estado publicado, sin
   más ediciones de causa raíz disponibles en la UI.

## Escenario 2 — Reporte DGAC con hash visible (US2)

1. Emitir un reporte DGAC para un tipo y período.
2. **Esperado**: aparece en el listado con su hash de contenido.

## Escenario 3 — Acceso de auditor + evidencia SOC2 (US3/US4)

1. Otorgar acceso de auditor a un usuario con ventana de fechas.
2. **Esperado**: aparece en el listado con su ventana vigente.
3. Consultar evidencia SOC2 → **esperado**: solo lectura, sin botón de
   alta si el rol activo no tiene `compliance:escribir`.

## Verificación empírica (no manual)

- `pytest tests/integration/test_compliance_hub.py` -- verifica que
  `role_sre` alcanza post-mortems (hallazgo de scopes corregido), y que
  los 4 listados nuevos filtran por tenant.
- `ruff`/`mypy`/`bandit`/`import-linter` en verde.
- Build de producción de `apps/web`.
