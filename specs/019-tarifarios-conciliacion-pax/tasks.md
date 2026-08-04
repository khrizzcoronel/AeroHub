# Tasks: Tarifarios y conciliación de pax

**Input**: Design documents from `specs/019-tarifarios-conciliacion-pax/`

**Tests**: sin automatizados para el frontend (verificación manual guiada
por [quickstart.md](./quickstart.md)); sí se agrega cobertura `pytest`
de integración para los 2 listados nuevos y la regla de conciliación.

**Organización**: US1 (publicar/activar tarifario, P1), US2 (ver
historial de tarifarios, P2), US3 (registrar y conciliar pax, P2).

## Phase 1: Setup

- [X] T001 Verificar que `role_tenant_admin`/`role_billing_officer` ya
      tienen `billing:escribir` en
      `packages/contracts/aerohub_contracts/roles_modulos.py` (research.md
      Decisión 1 de S1.16 fue un hallazgo de scopes faltantes; este
      sprint confirmó por lectura directa que **no** hay gap equivalente
      — sin cambios de scope necesarios).

## Phase 2: Foundational (bloqueante para las 3 historias)

- [X] T002 [P] `services/billing/aerohub_billing/infrastructure/consultas.py`:
      agregar `listar_tarifarios(conn)` (todos los estados del tenant,
      no solo vigente, research.md Decisión 4) y `listar_conciliaciones(conn)`
      (todas las del tenant).
- [X] T003 `services/billing/aerohub_billing/application/consultar.py`:
      agregar `consultar_tarifarios()` (incluye conceptos de cada
      tarifario vía `listar_conceptos_de_tarifario` ya existente) y
      `consultar_conciliaciones()`, con sus dataclasses
      `TarifarioResumen`/`ConciliacionResumen` (incluye `diferencia`
      derivada, nunca almacenada).
- [X] T004 `services/billing/aerohub_billing/application/__init__.py`:
      exportar los 2 casos de uso nuevos y sus dataclasses.
- [X] T005 `services/billing/aerohub_billing/api/router.py`: agregar
      `GET /billing/tarifarios` (scope `billing:leer`, incluye conceptos
      anidados) y `GET /billing/conciliaciones` (scope `billing:leer`) —
      ids Snowflake como string.
- [X] T006 `apps/web/src/app/billing/billing.service.ts`: extender con
      interfaces `Tarifario`/`ConceptoTarifario`/`Conciliacion` y métodos
      `listarTarifarios`, `crearTarifario`, `agregarConcepto`,
      `activarTarifario`, `listarConciliaciones`, `registrarConciliacion`,
      `conciliar`.
- [X] T007 `apps/web/src/app/app.routes.ts`: ruta `billing/tarifarios` →
      componente `PanelTarifarios` (definido en T008), con
      `data: { title: 'Tarifarios y conciliación' }`.
- [X] T008 `apps/web/src/app/shell/shell.ts`/`.html`: computed
      `puedeVerTarifarios` (scope `billing:escribir`, mismo mecanismo que
      `puedeVerUsuarios`/`puedeVerApiKeys`, research.md Decisión 1) +
      enlace nuevo en el menú lateral.

**Checkpoint**: los 2 endpoints nuevos responden con datos reales contra
MonetDB en Docker; `billing.service.ts` compila sin errores TS; la ruta
nueva carga vacía sin error 403 bajo `role_tenant_admin`.

---

## Phase 3: User Story 1 - Publicar y activar un tarifario sin SQL manual (Priority: P1)

- [X] T009 [US1] `apps/web/src/app/billing/panel-tarifarios/panel-tarifarios.ts`
      NUEVO: signals de la sección de tarifarios (`tarifarios`,
      `conceptosCargo` del catálogo, `mostrarModalTarifario`, campos del
      formulario `nombre`/`moneda`/`vigenteDesde`), método
      `crearTarifario()`.
- [X] T010 [US1] `panel-tarifarios.ts`: signals/método para agregar
      concepto (`tarifarioAgregandoConcepto`, `conceptoCargoId`,
      `tarifaUnitaria`), método `agregarConcepto()`.
- [X] T011 [US1] `panel-tarifarios.ts`: signal `tarifarioActivando`,
      método `activarTarifario()` — el modal de confirmación se abre
      ANTES de invocar el endpoint (FR-003), nunca activa directo desde
      la fila.
- [X] T012 [US1] `panel-tarifarios.html` NUEVO: sección "Tarifarios" —
      `.ah-panel` de búsqueda por nombre/moneda, `.ah-tabla`
      (nombre, moneda, estado como `.ah-pill`, vigencia), botón "Nuevo
      tarifario" → modal con campos de cabecera; por fila, botón
      "Agregar concepto" (select de `conceptosCargo`, nunca id a mano) y
      botón "Activar" → modal de confirmación con el aviso textual de
      inmutabilidad (research.md Decisión 3: informativo, sin bloquear
      si no hay conceptos — el backend tampoco lo exige).
- [X] T013 [US1] `panel-tarifarios.scss` NUEVO: layout base de la vista
      (dos secciones apiladas: tarifarios, conciliaciones), reutilizando
      `.ah-panel`/`.ah-tabla`/`.ah-modal`/`.ah-pill` ya globales — sin
      `max-width`.

**Checkpoint**: US1 verificable — Escenario 1 de quickstart.md completo
(crear, agregar concepto, activar con aviso, verificar que el anterior
pasa a histórico).

---

## Phase 4: User Story 2 - Ver historial completo de tarifarios (Priority: P2)

- [X] T014 [US2] `panel-tarifarios.ts`: computed/signal para expandir el
      detalle de un tarifario (conceptos con tarifa unitaria) sin
      navegar a otra vista — expansión inline de fila o modal de
      detalle, reutilizando los datos ya cargados por T009 (sin query
      nueva).
- [X] T015 [US2] `panel-tarifarios.html`: acción "Ver conceptos" por fila
      de tarifario (tabla o lista compacta dentro de un `.ah-modal`),
      visible para tarifarios en cualquier estado (no solo vigente).

**Checkpoint**: US2 verificable — Escenario 2 de quickstart.md (tabla
completa con históricos + detalle de conceptos).

---

## Phase 5: User Story 3 - Registrar y resolver una conciliación de pax (Priority: P2)

- [X] T016 [US3] `panel-tarifarios.ts`: signals de la sección de
      conciliaciones (`conciliaciones`, `mostrarModalConciliacion`,
      campos del formulario `vueloId`/`periodo`/`paxReportadoAerolinea`/
      `paxRegistradoSistema`/`fuenteReporte` — AMBOS conteos son input,
      research.md Decisión 2), método `registrarConciliacion()`.
- [X] T017 [US3] `panel-tarifarios.ts`: método `conciliar()` — al
      recibir un error del backend por diferencia distinta de cero
      (`DiferenciaNoNula`, HTTP 409 esperado), mostrarlo con
      `mensajeDeError(err)` sin intentar validarlo antes en el frontend
      (la regla vive solo en el backend, research.md Decisión 2).
- [X] T018 [US3] `panel-tarifarios.html`: sección "Conciliación de pax" —
      `.ah-panel` de búsqueda por vuelo/período, `.ah-tabla` (vuelo,
      período, pax aerolínea, pax sistema, diferencia calculada visible
      sin abrir detalle FR-009, estado conciliado/pendiente como
      `.ah-pill`), botón "Nueva conciliación" → modal con los 2 campos
      de conteo; acción "Conciliar" por fila (solo si diferencia visible
      es 0, deshabilitada en otro caso — ayuda visual, el backend igual
      la re-valida).

**Checkpoint**: US3 verificable — Escenario 3 de quickstart.md completo
(diferencia distinta de cero rechazada, diferencia cero conciliada).

---

## Phase 6: Polish y verificación

- [X] T019 [P] `tests/integration/test_billing_tarifarios_conciliacion.py`
      NUEVO: `pytest` de integración contra MonetDB real — listar
      tarifarios (incluye históricos), activar tarifario nuevo y
      verificar que un cargo/factura ya calculado no cambia
      (spec.md SC-002), registrar conciliación con diferencia no nula y
      confirmar que `conciliar()` la rechaza, registrar una con
      diferencia cero y confirmar que se marca conciliada.
- [ ] T020 [P] `docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.3: sin cambios
      de contenido necesarios (ya describe el sprint correctamente) —
      solo referenciar el commit al cerrar.
- [ ] T021 [P] `CLAUDE.md`: fila S1.17 en la tabla de sprints + resumen
      de lo implementado, mismo formato que S1.15/S1.16.
- [X] T022 `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre
      `services/billing` completo (imagen reconstruida en vivo por
      `docker cp` + verificación, incluye la suite existente
      `test_billing_facturacion.py` sin regresiones, 11/11 en verde).
- [ ] T023 Ejecutar los 3 escenarios de quickstart.md contra Docker real
      — solo si el usuario lo pide explícitamente (regla vigente:
      no verificar automáticamente en el navegador).
- [X] T024 Build de producción de `apps/web` en verde.

## Dependencies

- Fase 1 (T001) es una verificación, no bloquea nada — confirma que no
  hace falta ningún cambio de scope antes de construir sobre esa
  suposición.
- Fase 2 (Foundational) bloquea las 3 historias por igual.
- US1 (Fase 3) es el caso de uso central del sprint (RF-T10) — se
  implementa primero.
- US2 (Fase 4) depende de que existan tarifarios históricos, que solo
  aparecen tras activar un segundo tarifario en US1 — implementarla
  después es lo natural, aunque técnicamente no depende de código de
  US1, solo de datos.
- US3 (Fase 5) es independiente de US1/US2 salvo por compartir el mismo
  componente `panel-tarifarios.ts`/`.html` (secciones distintas).
- Fase 6 depende de que las 3 historias estén completas.

## Parallel Example

```text
# Tras completar Fase 1 y Fase 2:
Task T009-T013           (US1 -- tarifarios)
Task T016-T018           (US3 -- conciliaciones, seccion distinta del mismo componente)
# US1 y US3 tocan el mismo panel-tarifarios.ts/.html en secciones
# distintas -- mismo patron que S1.16 (fids/pantalla-list.ts con 2
# secciones). US2 depende de datos que solo existen tras US1, no de
# archivo compartido.
```

## Implementation Strategy

**MVP = US1**: con Fase 1+2+3 completas, RF-T10 ya es cierto -- publicar
y activar un tarifario sin SQL manual funciona de punta a punta. US2
(historial) y US3 (conciliación) son valiosas pero no bloqueantes para
la demostración inicial del hallazgo que motiva el sprint.

## Notes

- Cero cambios al contrato de los 6 endpoints de escritura existentes
  (S1.6) ni al motor de facturación (spec.md Assumptions).
- `domain/` de `aerohub_billing` no cambia -- sin regla de negocio
  nueva, solo consultas de listado y su consumo desde `apps/web`.
- Commit solo si se pide explícitamente.
