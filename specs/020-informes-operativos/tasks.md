# Tasks: Informes operativos (RF-I)

**Input**: Design documents from `specs/020-informes-operativos/`

**Tests**: sin automatizados para el frontend (verificación manual guiada
por [quickstart.md](./quickstart.md)); sí se agrega `pytest` de
integración por módulo (6 suites) verificando SC-002/SC-003.

**Organización**: US1 (informe simple, P1), US2 (informe compuesto con
subtotales, P1), US3 (parámetros en el artefacto, P2), US4 (auditoría de
emisión, P3).

## Phase 1: Setup — primitivo visual compartido

- [X] T001 `apps/web/src/app/_primitivos.scss`: agregar `.ah-informe`
      (cabecera de parámetros, filas de subtotal/total diferenciadas de
      filas normales, estilos de impresión), reutilizando `.ah-tabla`/
      `.ah-panel`/`.ah-campo` ya existentes.

## Phase 2: Foundational — servicio y componente compartidos (bloqueante para las 4 historias)

- [X] T002 `apps/web/src/app/informes/informe.service.ts` NUEVO:
      interfaces genéricas `InformeSimple<TFila>`/`InformeCompuesto<TFila>`
      (`parametros`, `generado_en`, `filas`|`grupos`, `total`), método
      genérico `obtenerInforme<T>(url, params)` + helper
      `urlExportarCsv(url, params)` (research.md Decisión 2).
- [X] T003 `apps/web/src/app/informes/panel-informe/panel-informe.ts`
      NUEVO: componente reutilizable con `@Input() config` (título,
      endpoint simple/compuesto, columnas, filtros disponibles),
      signals de filtros/resultado/cargando/error, método `consultar()`,
      link de exportación vía `urlExportarCsv` (research.md Decisión 1).
- [X] T004 `panel-informe.html`/`.scss` NUEVOS: `.ah-panel` de filtros +
      `.ah-informe` con cabecera de parámetros/fecha de generación,
      tabla de filas (modo simple) o grupos con subtotal + fila de total
      general diferenciada (modo compuesto).

**Checkpoint**: `panel-informe` compila y renderiza con datos de prueba
estáticos (sin backend todavía) -- listo para conectar cada módulo.

---

## Phase 3: User Story 1 - Informes simples de los 6 módulos (Priority: P1)

- [X] T005 [P] [US1] `services/aodb/aerohub_aodb/infrastructure/consultas_informe.py`
      NUEVO: `listar_vuelos_informe(conn, *, periodo_inicio, periodo_fin, aerolinea_id=None, estado=None)`.
- [X] T006 [P] [US1] `services/gates/aerohub_gates/infrastructure/consultas_informe.py`
      NUEVO: `listar_asignaciones_informe(conn, *, periodo_inicio, periodo_fin, puerta_id=None)`.
- [X] T007 [P] [US1] `services/ramp/aerohub_ramp/infrastructure/consultas_informe.py`
      NUEVO: `listar_turnarounds_informe(conn, *, periodo_inicio, periodo_fin, estado=None)`.
- [X] T008 [P] [US1] `services/billing/aerohub_billing/infrastructure/consultas_informe.py`
      NUEVO: `listar_facturas_informe(conn, *, periodo_inicio, periodo_fin, aerolinea_id=None, estado=None)`
      (reutiliza el mismo criterio de `listar_facturas` ya existente).
- [X] T009 [P] [US1] `services/tenancy/aerohub_tenancy/infrastructure/consultas_informe.py`
      NUEVO: `listar_usuarios_tenants_informe(conn, *, estado=None)` --
      alcance `interno` (lista tenants + conteo de usuarios, no requiere
      tenant único, mismo criterio que `GET /tenants`).
- [X] T010 [P] [US1] `services/compliance/aerohub_compliance/infrastructure/consultas_informe.py`
      NUEVO: `listar_eventos_auditoria_informe(conn, *, periodo_inicio, periodo_fin)`
      (lee `compliance.log_auditoria`, redeclarada localmente si hace
      falta -- alcance `interno`, ya registrado por `packages/repository`).
- [X] T011 [US1] `application/informes.py` NUEVO en cada uno de los 6
      módulos: función `consultar_informe_simple(...)` que arma
      `parametros`/`generado_en`/`filas` sobre la consulta de T005-T010.
- [X] T012 [US1] `api/router.py` de cada módulo: agregar
      `GET /<prefijo>/informes/simple?formato=json|csv` (scope
      `<modulo>:leer` ya existente), con exportación CSV desde el mismo
      objeto de respuesta (research.md Decisión 3).
- [X] T013 [US1] `apps/web/src/app/informes/informe.service.ts`: agregar
      los 6 métodos `obtenerInformeSimple<Modulo>()` + rutas nuevas
      `/*/informes` en `app.routes.ts` instanciando `panel-informe` con
      la config de cada módulo (columnas + filtros propios).

**Checkpoint**: US1 verificable -- Escenario 1 de quickstart.md, para
los 6 módulos.

---

## Phase 4: User Story 2 - Informes compuestos con subtotales reconciliables (Priority: P1)

- [X] T014 [P] [US2] `consultas_informe.py` de AODB: agregar
      `agrupar_vuelos_por_aerolinea(conn, *, periodo_inicio, periodo_fin)`
      -- `func.count`/puntualidad calculada con SQL (`func.sum(case(...))`),
      nunca en Python sobre filas ya traídas (research.md Decisión 6).
- [X] T015 [P] [US2] `consultas_informe.py` de Gates: agregar
      `agrupar_asignaciones_por_puerta(conn, ...)` -- conteo +
      solapamientos por puerta.
- [X] T016 [P] [US2] `consultas_informe.py` de Ramp: agregar
      `agrupar_turnarounds_por_tipo_tarea(conn, ...)` -- conteo,
      desviación media, incidencias por severidad.
- [X] T017 [P] [US2] `consultas_informe.py` de Billing: agregar
      `agrupar_facturacion_por_concepto(conn, ...)` -- `func.sum(monto)`
      agrupado por `concepto_cargo_id` vía `factura_linea`→`cargo_aeronautico`,
      cierra RF-E02 (spec.md US2, escenario 2).
- [X] T018 [P] [US2] `consultas_informe.py` de Tenancy: agregar
      `agrupar_tenants_por_plan_estado(conn, ...)` -- conteo de tenants,
      usuarios activos, licencias vigentes.
- [X] T019 [P] [US2] `consultas_informe.py` de Compliance: agregar
      `agrupar_reportes_dgac_por_tipo(conn, ...)` -- conteo de
      `reporte_dgac` por `tipo_reporte_id` (research.md Decisión 5).
- [X] T020 [US2] `application/informes.py` de cada módulo: función
      `consultar_informe_compuesto(...)` -- arma `grupos[].subtotal` +
      `total = sum(subtotales)`, calculado en Python SOLO como suma de
      subtotales ya agregados por SQL (nunca vuelve a sumar filas
      crudas) -- ver Constraints del plan.
- [X] T021 [US2] `api/router.py` de cada módulo: agregar
      `GET /<prefijo>/informes/compuesto?formato=json|csv`.
- [X] T022 [US2] `informe.service.ts` + rutas: agregar los 6 métodos de
      informe compuesto; `panel-informe` ya soporta el modo grupos desde
      T004, solo se conecta la config.

**Checkpoint**: US2 verificable -- Escenario 2 de quickstart.md, para
los 6 módulos; verificación manual de que suma(subtotales) == total en
al menos Billing (SC-003).

---

## Phase 5: User Story 3 - Parámetros en el artefacto exportado (Priority: P2)

- [X] T023 [US3] Los 12 endpoints de T012/T021: el CSV generado
      (research.md Decisión 3) antepone una sección de cabecera con
      `parametros` (cada filtro usado) y `generado_en` antes de las
      filas de datos -- una sola función helper `_csv_con_cabecera(...)`
      reutilizada dentro de cada `api/router.py` (sin paquete
      compartido, mismo criterio que research.md Decisión 2).
- [X] T024 [US3] `panel-informe.html`: la cabecera de `.ah-informe` en
      pantalla también muestra `parametros`/`generado_en` -- mismo dato
      que el CSV, nunca inventado en el frontend.

**Checkpoint**: US3 verificable -- Escenario 3 de quickstart.md.

---

## Phase 6: User Story 4 - Auditoría de emisión (Priority: P3)

- [X] T025 [US4] `application/informes.py` de Billing: `consultar_informe_compuesto`
      llama a `registrar_auditoria(...)` al emitir (research.md Decisión 4).
- [X] T026 [US4] `application/informes.py` de Compliance: idem para el
      informe compuesto de DGAC.

**Checkpoint**: US4 verificable -- Escenario 4 de quickstart.md.

---

## Phase 7: Polish y verificación

- [X] T027 [P] `tests/integration/test_aodb_informes.py` NUEVO.
- [X] T028 [P] `tests/integration/test_gates_informes.py` NUEVO.
- [X] T029 [P] `tests/integration/test_ramp_informes.py` NUEVO.
- [X] T030 [P] `tests/integration/test_billing_informes.py` NUEVO --
      incluye SC-003 (conciliación con facturas emitidas).
- [X] T031 [P] `tests/integration/test_tenancy_informes.py` NUEVO.
- [X] T032 [P] `tests/integration/test_compliance_informes.py` NUEVO.
- [X] T033 [P] `docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.4: sin cambios
      de contenido necesarios -- solo referenciar el commit al cerrar.
- [X] T034 [P] `CLAUDE.md`: fila S1.18 en la tabla de sprints + resumen.
- [X] T035 `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre los 6
      servicios modificados.
- [ ] T036 Ejecutar los 4 escenarios de quickstart.md contra Docker real
      — NO realizado: regla vigente de no verificar automáticamente en
      el navegador salvo pedido explícito del usuario.
- [X] T037 Build de producción de `apps/web` en verde.

## Dependencies

- Fase 1+2 (primitivo + componente compartido) bloquean las 4 historias.
- US1 (Fase 3) antes que US2 (Fase 4) -- los informes simples validan la
  conexión backend↔frontend antes de sumarle agregación.
- US3 (Fase 5) depende de que los 12 endpoints ya existan (T012/T021).
- US4 (Fase 6) depende de que el informe compuesto de Billing/Compliance
  ya exista (T020-T021, ese módulo).
- Fase 7 depende de las 4 historias completas.

## Parallel Example

```text
# Tras completar Fase 1+2:
Task T005, T006, T007, T008, T009, T010   (US1 -- 6 modulos, archivos independientes)
# Tras completar Fase 3:
Task T014, T015, T016, T017, T018, T019   (US2 -- 6 modulos, archivos independientes)
```

## Implementation Strategy

**MVP = US1 + US2 en Billing únicamente**: con Fase 1+2 completas más
T008/T011/T012/T017/T020/T021 (solo Billing), SC-003 (la compuerta de
pruebas más citada del plan, RF-E02) ya es demostrable de punta a punta.
Los otros 5 módulos siguen el mismo patrón exacto una vez que Billing
está verificado.

## Notes

- Cero cambios a la lógica de negocio de los 6 módulos -- los informes
  son de solo lectura (spec.md Assumptions).
- `domain/` de ningún módulo cambia.
- Commit solo si se pide explícitamente.
