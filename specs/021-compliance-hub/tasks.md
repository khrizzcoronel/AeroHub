# Tasks: Compliance Hub (M9)

**Input**: Design documents from `specs/021-compliance-hub/`

**Tests**: sin automatizados para el frontend; sí pytest de integración
para el hallazgo de scopes y los 4 listados nuevos.

**Organización**: US1 (post-mortem, P1), US2 (reportes DGAC, P1), US3
(evidencia SOC2, P2), US4 (accesos de auditor, P2).

## Phase 1: Setup — el hallazgo que bloquea todo lo demás

- [X] T001 `packages/contracts/aerohub_contracts/roles_modulos.py`:
      agregar `M9` a los módulos y `compliance:leer`/`compliance:escribir`
      a los scopes de `role_sre` (research.md Decisión 1).
- [X] T002 `packages/contracts/aerohub_contracts/roles_modulos.py`:
      `MODULOS["M9"]` ruta de `None` a `/compliance/panel`.

## Phase 2: Foundational (bloqueante para las 4 historias)

- [X] T003 [P] `services/compliance/aerohub_compliance/infrastructure/consultas.py`:
      agregar `listar_post_mortems(conn)`, `listar_reportes_dgac(conn)`,
      `listar_accesos_auditor(conn)`, `listar_evidencia_soc2(conn)` --
      todos tenant-scoped.
- [X] T004 [P] `services/compliance/aerohub_compliance/infrastructure/consultas_catalogo.py`
      NUEVO: `listar_tipos_incidente(conn)`, `listar_tipos_reporte_regulatorio(conn)`,
      `listar_controles_soc2(conn)` -- catálogos globales de solo lectura.
- [X] T005 `services/compliance/aerohub_compliance/infrastructure/__init__.py`:
      exportar las 7 funciones nuevas.
- [X] T006 `services/compliance/aerohub_compliance/application/consultar.py`:
      agregar `consultar_post_mortems()`, `consultar_reportes_dgac()`,
      `consultar_accesos_auditor()`, `consultar_evidencia_soc2()`.
- [X] T007 `services/compliance/aerohub_compliance/application/consultar_catalogos.py`
      NUEVO: `consultar_tipos_incidente()`, `consultar_tipos_reporte()`,
      `consultar_controles_soc2()`.
- [X] T008 `services/compliance/aerohub_compliance/application/__init__.py`:
      exportar los 7 casos de uso nuevos.
- [X] T009 `services/compliance/aerohub_compliance/api/router.py`: agregar
      `GET /compliance/post-mortems`, `GET /compliance/reportes-dgac`,
      `GET /compliance/accesos-auditor`, `GET /compliance/evidencia-soc2`,
      `GET /compliance/catalogo/{tipos-incidente,tipos-reporte,controles-soc2}`
      (todos `compliance:leer`).
- [X] T010 `apps/web/src/app/compliance/compliance.service.ts` NUEVO:
      interfaces y métodos para las 11 operaciones (5 alta/mutación ya
      existentes + 7 lecturas nuevas).
- [X] T011 `apps/web/src/app/app.routes.ts`: ruta `compliance/panel` →
      componente `PanelCompliance` (T012).

**Checkpoint**: `role_sre` autenticado puede llamar
`POST /compliance/post-mortems` y recibir 201 (no 403) -- confirma T001.

---

## Phase 3: User Story 1 - Post-mortem de punta a punta (Priority: P1)

- [X] T012 [US1] `apps/web/src/app/compliance/panel-compliance/panel-compliance.ts`
      NUEVO: signals de la sección de incidentes (alta + listado).
- [X] T013 [US1] `panel-compliance.ts`: signals de la sección de
      post-mortems -- listado, detalle con acciones, alta, editar causa
      raíz, agregar acción, completar acción, publicar.
- [X] T014 [US1] `panel-compliance.html`: secciones "Incidentes" y
      "Post-mortems" -- `.ah-panel`/`.ah-tabla`/`.ah-modal`, sin acción
      de editar/publicar visible una vez el post-mortem está publicado
      (spec.md Edge Cases).

**Checkpoint**: US1 verificable -- Escenario 1 de quickstart.md.

---

## Phase 4: User Story 2 - Reportes DGAC con hash visible (Priority: P1)

- [X] T015 [US2] `panel-compliance.ts`: signals de la sección de
      reportes DGAC (alta + listado, select de tipo desde el catálogo).
- [X] T016 [US2] `panel-compliance.html`: sección "Reportes DGAC" --
      tabla con columna de hash visible.

**Checkpoint**: US2 verificable -- Escenario 2 de quickstart.md.

---

## Phase 5: User Story 4 - Accesos de auditor (Priority: P2)

*(Antes que US3 -- US3 depende conceptualmente de que exista al menos
un acceso otorgado, aunque no hay dependencia tecnica real.)*

- [X] T017 [US4] `panel-compliance.ts`: signals de la sección de accesos
      de auditor (alta + listado).
- [X] T018 [US4] `panel-compliance.html`: sección "Accesos de auditor"
      -- tabla con ventana de fechas visible.

**Checkpoint**: US4 verificable -- Escenario 3 (parte 1) de quickstart.md.

---

## Phase 6: User Story 3 - Evidencia SOC2 de solo lectura (Priority: P2)

- [X] T019 [US3] `panel-compliance.ts`: signal de listado de evidencia
      SOC2; alta condicionada a `compliance:escribir` (research.md
      Decisión 4).
- [X] T020 [US3] `panel-compliance.html`: sección "Evidencia SOC2" --
      tabla de solo lectura, botón de alta oculto si el rol no puede
      escribir.

**Checkpoint**: US3 verificable -- Escenario 3 (parte 2) de quickstart.md.

---

## Phase 7: Polish y verificación

- [X] T021 [P] `tests/integration/test_compliance_hub.py` NUEVO --
      verifica que `role_sre` alcanza `POST /compliance/post-mortems`
      (hallazgo de scopes), y que los 4 listados nuevos filtran por
      tenant contra MonetDB real.
- [X] T022 [P] `docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.5: sin cambios
      de contenido necesarios -- solo referenciar el commit al cerrar.
- [X] T023 [P] `CLAUDE.md`: fila S1.19 en la tabla de sprints + resumen.
- [X] T024 `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre
      `services/compliance`.
- [ ] T025 Ejecutar los 3 escenarios de quickstart.md contra Docker real
      -- solo si el usuario lo pide explícitamente (regla vigente).
- [X] T026 Build de producción de `apps/web` en verde.

## Dependencies

- Fase 1 (T001-T002) bloquea absolutamente todo -- sin scopes, `role_sre`
  no alcanza ningún endpoint de post-mortem.
- Fase 2 (Foundational) bloquea las 4 historias.
- US1 (Fase 3) es el flujo central del sprint -- se implementa primero.
- US4 (Fase 5) antes que US3 (Fase 6) por orden conceptual, no técnico.
- Fase 7 depende de las 4 historias completas.

## Implementation Strategy

**MVP = US1**: con Fase 1+2+3, el hallazgo crítico de scopes queda
corregido y el flujo central (post-mortem) es demostrable de punta a
punta. US2/US3/US4 completan el resto de la superficie sin bloquear la
demostración inicial.

## Notes

- `post_mortem`/`post_mortem_accion` son la única excepción con UPDATE
  dentro de `compliance.*` (PN-04 reforzada, ya garantizada por S1.7) --
  este sprint no cambia esa garantía, solo la expone.
- Commit solo si se pide explícitamente.
