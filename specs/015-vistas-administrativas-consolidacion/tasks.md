# Tasks: Vistas administrativas + consolidación

**Input**: Design documents from `specs/015-vistas-administrativas-consolidacion/`

**Tests**: sin automatizados — verificación manual guiada por
[quickstart.md](./quickstart.md).

**Organización**: US1 (billing, P1), US2 (tenants, P2), US3 (auditoría, P3).

## Phase 1: User Story 1 - Panel de facturas (Priority: P1)

- [X] T001 [US1] `apps/web/src/app/billing/panel-facturas/panel-facturas.ts`:
      función pura `claseEstadoFactura(estado: string): string` (research.md
      Decisión 1) -- `borrador`→'', `emitida`→`'ah-tira--atencion'`,
      `pagada`→`'ah-tira--ok'`, `vencida`/`disputada`→`'ah-tira--critico'`
- [X] T002 [US1] `apps/web/src/app/billing/panel-facturas/panel-facturas.html`:
      lista de facturas como `.ah-tira` (id/aerolinea/periodo/monto en
      mono, barra con T001); detalle con `.ah-tabla` para líneas de
      cargo; formularios con `.ah-campo`/`.ah-btn`; errores con
      `.ah-alerta`; estado vacío con `.ah-vacio`
- [X] T003 [US1] `apps/web/src/app/billing/panel-facturas/panel-facturas.scss`
      NUEVO: extraer el bloque `styles:` inline del componente, layout
      responsivo consistente con las otras vistas rediseñadas

**Checkpoint**: US1 verificable — Escenario 1 de quickstart.md.

---

## Phase 2: User Story 2 - Formulario de tenant (Priority: P2)

- [X] T004 [US2] `apps/web/src/app/tenants/tenant-creation/tenant-creation.html`:
      campos con `.ah-campo`, botón con `.ah-btn`, resultado de creación
      como lista de definición dentro de `.ah-alerta--aviso` (research.md
      Decisión 3), error con `.ah-alerta`
- [X] T005 [US2] `apps/web/src/app/tenants/tenant-creation/tenant-creation.scss`
      NUEVO: contenedor simple, responsivo

**Checkpoint**: US2 verificable — Escenario 2 de quickstart.md.

---

## Phase 3: User Story 3 - Auditoría de las 8 vistas de S1.10 (Priority: P3)

- [X] T006 [US3] Revisar `apps/web/src/app/auth/**/*.html` + `.scss` y
      `apps/web/src/app/shell/*` contra los tokens/primitivos vigentes;
      corregir inconsistencias menores encontradas; documentar
      hallazgos mayores sin resolverlos (research.md Decisión 4)

**Checkpoint**: US3 verificable — Escenario 3 de quickstart.md.

---

## Phase 4: Documentación y Polish

- [X] T007 [P] `docs/PLAN_IMPLEMENTACION_v2.0.md`: sección §8.13 nueva
- [X] T008 [P] `CLAUDE.md`: fila S1.13 + estado del rediseño
- [X] T009 Ejecutar los 3 escenarios de quickstart.md contra Docker real
- [X] T010 Build de producción de `apps/web` en verde

## Notes

- Cero cambios en `billing.service.ts`/`tenant.service.ts`.
- Commit solo si se pide explícitamente.
