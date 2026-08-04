# Tasks: Administración de FIDS

**Input**: Design documents from `specs/018-administracion-fids/`

**Tests**: sin automatizados para el frontend (verificación manual guiada
por [quickstart.md](./quickstart.md)); sí se agrega cobertura `pytest`
de integración para las 3 consultas nuevas de backend.

**Organización**: US1 (pantallas/telemetría, P1), US2 (plantillas, P1),
US3 (reasignación, P2).

## Phase 1: Setup — el hallazgo que bloquea todo lo demás

- [X] T001 `packages/contracts/aerohub_contracts/roles_modulos.py`:
      agregar `fids:leer` y `fids:administrar` a los scopes de
      `role_tenant_admin` (research.md Decisión 1 — sin esto, ningún rol
      humano puede usar la vista de este sprint).

## Phase 2: Foundational (bloqueante para US1/US2)

- [X] T002 [P] `services/fids/aerohub_fids/infrastructure/consultas.py`:
      agregar `listar_plantillas(conn)` (agrupada por `nombre`, solo la
      `version` más alta de cada una, research.md Decisión 2) y
      `listar_pantallas(conn)` (tenant-scoped, todas las columnas
      incluida `estado`/`ultima_senal_en`).
- [X] T003 [P] `services/fids/aerohub_fids/infrastructure/consultas_catalogo.py`
      NUEVO: redeclarar `ops.terminal` de solo lectura, **filtrada por
      tenant** (research.md Decisión 4, a diferencia de los catálogos
      globales de S1.15) — `listar_terminales(conn)`.
- [X] T004 `services/fids/aerohub_fids/infrastructure/__init__.py`:
      exportar `listar_plantillas`, `listar_pantallas`,
      `listar_terminales`.
- [X] T005 `services/fids/aerohub_fids/application/consultar_plantillas.py`
      NUEVO: `consultar_plantillas()`, dataclass `PlantillaResumen`.
- [X] T006 `services/fids/aerohub_fids/application/consultar_pantallas.py`
      NUEVO: `consultar_pantallas()`, dataclass `PantallaResumen` (con
      `estado`, `ultima_senal_en`).
- [X] T007 `services/fids/aerohub_fids/application/consultar_catalogos.py`
      NUEVO: `consultar_terminales()`, dataclass `Terminal`.
- [X] T008 `services/fids/aerohub_fids/application/__init__.py`: exportar
      los 3 casos de uso y sus dataclasses de T005-T007.
- [X] T009 `services/fids/aerohub_fids/api/router.py`: agregar
      `GET /fids/plantillas` (scope `fids:leer`), `GET /fids/pantallas`
      (scope `fids:leer`), `GET /fids/catalogo/terminales` (scope
      `fids:leer`) — ids Snowflake como string, `ultima_senal_en` como
      ISO string o null.
- [X] T010 `apps/web/src/app/fids/fids.service.ts` NUEVO: interfaces y
      métodos `listarPlantillas`, `publicarPlantilla`, `listarPantallas`,
      `registrarPantalla`, `asignarPlantilla`, `listarTerminales`.
- [X] T011 `apps/web/src/app/app.routes.ts`: ruta `fids/pantallas` →
      componente `PantallaList` (nombre a definir en T012), con
      `data: { title: 'FIDS Management' }`.

**Checkpoint**: los 3 endpoints nuevos responden con datos reales contra
MonetDB en Docker bajo `role_tenant_admin` (post T001); `fids.service.ts`
compila sin errores TS; la ruta nueva carga vacía sin error 403.

---

## Phase 3: User Story 2 - Publicar y reutilizar plantillas (Priority: P1)

*(Antes que US1 en el orden de implementación — US1 depende de que haya
al menos una plantilla seleccionable, research.md Decisión 6.)*

- [X] T012 [US2] `apps/web/src/app/fids/pantalla-list/pantalla-list.ts`
      NUEVO: signals de la sección de plantillas (`plantillas`,
      `mostrarModalPlantilla`, campos del formulario `nombre` +
      `definicionJson` como texto), método `publicarPlantilla()` que
      parsea el JSON antes de enviar y muestra error de formato inválido
      sin cerrar el modal (spec.md US2, escenario 2).
- [X] T013 [US2] `pantalla-list.html` NUEVO: sección "Plantillas" —
      `.ah-panel` de búsqueda por nombre, `.ah-tabla` (nombre, versión,
      vigente desde), botón "Nueva plantilla" → modal con campo de
      nombre y textarea de `definicion_json`.
- [X] T014 [US2] `pantalla-list.scss` NUEVO: layout base de la vista
      (dos secciones apiladas), reutilizando `.ah-panel`/`.ah-tabla`/
      `.ah-modal` ya globales — sin `max-width` (mismo criterio que el
      resto de `apps/web` desde S1.14).

**Checkpoint**: US2 verificable — mitad del Escenario 1 de
quickstart.md (publicar plantilla).

---

## Phase 4: User Story 1 - Registrar pantalla y ver telemetría (Priority: P1)

- [X] T015 [US1] `pantalla-list.ts`: signals de la sección de pantallas
      (`pantallas`, `terminales`, `mostrarModalRegistrar`, campos del
      formulario `terminalId`/`codigo`/`plantillaId`/
      `ubicacionDescripcion`), método `registrarPantalla()`.
- [X] T016 [US1] `pantalla-list.ts`: signal `codigoRecienRegistrado`
      para el aviso copiable post-alta (research.md Decisión 5); función
      pura `claseEstadoPantalla`/`etiquetaEstadoPantalla` (3 valores:
      `en_linea`→ok, `sin_senal`→crítico, `mantenimiento`→neutro).
- [X] T017 [US1] `pantalla-list.html`: sección "Pantallas" —
      `.ah-panel` de búsqueda por código, `.ah-tabla` (código, terminal,
      plantilla vigente, `.ah-pill` de telemetría, última señal, acción
      "Asignar plantilla"), botón "Nueva pantalla" → modal con selects
      de terminal/plantilla (nunca ids a mano, FR-004); estado vacío
      explícito si `terminales` está vacío (spec.md Edge Cases); modal
      de éxito con el código en un `.ah-alerta--aviso` copiable.
- [X] T018 [US1] `pantalla-list.html`/`.ts`: si `terminales().length === 0`,
      el `<select>` de terminal se reemplaza por un mensaje explícito en
      vez de un select vacío sin explicación (spec.md Edge Cases,
      research.md Decisión 4).

**Checkpoint**: US1 verificable — resto del Escenario 1 + Escenario 3 de
quickstart.md.

---

## Phase 5: User Story 3 - Reasignar plantilla (Priority: P2)

- [X] T019 [US3] `pantalla-list.ts`: signal `pantallaReasignando`, campo
      `plantillaIdNueva`, método `asignarPlantilla()`.
- [X] T020 [US3] `pantalla-list.html`: modal "Asignar plantilla" (abierto
      desde la acción de fila de T017) con select de plantilla y
      confirmación; toast de éxito (`ToastService`, mismo patrón que el
      resto del sistema).

**Checkpoint**: US3 verificable — Escenario 2 de quickstart.md (incluye
confirmar en `apps/fids-player` real que el contenido cambia sin
reconectar).

---

## Phase 6: Polish y verificación

- [X] T021 [P] `pytest` de integración para `listar_plantillas` (confirma
      que solo devuelve la última versión por nombre),
      `listar_pantallas` (confirma telemetría real) y `listar_terminales`
      contra MonetDB real.
- [X] T022 [P] `docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.2: sin cambios
      de contenido necesarios (ya describe el sprint correctamente) —
      solo referenciar el commit al cerrar.
- [X] T023 [P] `CLAUDE.md`: fila S1.16 en la tabla de sprints + resumen
      de lo implementado, mismo formato que S1.15.
- [X] T024 `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre
      `services/fids` completo.
- [ ] T025 Ejecutar los 3 escenarios de quickstart.md contra Docker real
      (`docker compose up -d --build gateway web fids-player`) — NO
      realizado: regla vigente de no verificar automáticamente en el
      navegador salvo pedido explícito del usuario.
- [X] T026 Build de producción de `apps/web` en verde.

## Dependencies

- Fase 1 (T001) bloquea absolutamente todo — sin scopes, cada llamada de
  la vista nueva devuelve 403 sin importar qué tan bien esté construida.
- Fase 2 (Foundational) bloquea US1 y US2 por igual.
- US2 (Fase 3) se implementa antes que US1 (Fase 4) en el orden de
  ejecución, aunque ambas son P1 — US1 necesita al menos una plantilla
  existente para ser demostrable de punta a punta (registrar una
  pantalla sin plantillas para elegir no prueba nada).
- US3 (Fase 5) depende de que existan pantallas ya registradas (US1).
- Fase 6 depende de que las 3 historias estén completas.

## Parallel Example

```text
# Tras completar Fase 1 y Fase 2:
Task T012, T013, T014           (US2 -- plantillas, independiente de archivos de US1 salvo el mismo .ts/.html compartido)
# US1 y US3 SI comparten pantalla-list.ts/.html con US2 -- a diferencia
# de S1.15 (3 historias en archivos separados), aqui las 3 tocan el
# mismo componente en secciones distintas. Ejecutar T012-T014 (US2)
# antes de T015-T018 (US1) por la dependencia real de datos, no solo de
# archivo.
```

## Implementation Strategy

**MVP = US2 + US1**: con Fase 1+2+3+4 completas, el caso de uso central
del sprint ya funciona de punta a punta (publicar plantilla, registrar
pantalla, conectar el reproductor real). US3 (reasignar) es la operación
de mantenimiento recurrente, valiosa pero no bloqueante para la
demostración inicial.

## Notes

- Cero cambios al contrato de los 3 endpoints de escritura existentes ni
  a `apps/fids-player` (spec.md Assumptions).
- `domain/` de `aerohub_fids` no cambia — sin regla de negocio nueva,
  solo consultas de listado.
- Commit solo si se pide explícitamente.
