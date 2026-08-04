# Tasks: Contrato de API y superficie del AODB

**Input**: Design documents from `specs/017-contrato-api-superficie-aodb/`

**Tests**: sin automatizados para el frontend (verificación manual guiada
por [quickstart.md](./quickstart.md)); sí se agrega cobertura `pytest`
para las 3 consultas de catálogo nuevas de backend (Principio IV/III).

**Organización**: US1 (superficie de vuelos, P1), US2 (contrato de API,
P2), US3 (endpoints huérfanos, P3).

## Phase 1: Setup

- [X] T001 `docs/api/openapi.yaml`: regenerar corriendo
      `tools/generar_openapi.py` (ya existe, sin cambios de código) dentro
      del contenedor `gateway`, para partir de un contrato sincronizado
      antes de agregar rutas nuevas.

## Phase 2: Foundational (bloqueante para US1)

- [X] T002 [P] `services/aodb/aerohub_aodb/infrastructure/consultas_catalogo.py`
      NUEVO: redeclarar `catalogo.aerolinea`, `catalogo.aeronave`,
      `catalogo.modelo_aeronave`, `catalogo.tipo_vuelo` (solo lectura,
      research.md Decisión 2) y `listar_aerolineas`, `listar_aeronaves`
      (join con `modelo_aeronave` para mostrar matrícula+modelo),
      `listar_tipos_vuelo`.
- [X] T003 `services/aodb/aerohub_aodb/infrastructure/__init__.py`: exportar
      las 3 funciones de T002.
- [X] T004 `services/aodb/aerohub_aodb/application/consultar_catalogos.py`
      NUEVO: casos de uso `consultar_aerolineas`, `consultar_aeronaves`,
      `consultar_tipos_vuelo` (envuelven T002 en `with sesion()`, mismo
      patrón que `consultar_vuelo.py`).
- [X] T005 `services/aodb/aerohub_aodb/application/__init__.py`: exportar
      los 3 casos de uso de T004.
- [X] T006 `services/aodb/aerohub_aodb/api/router.py`: agregar
      `GET /vuelos/catalogo/aerolineas`, `/aeronaves`, `/tipos-vuelo`,
      cada uno bajo `requiere_scope("vuelos:leer")` (mismo scope que
      `GET /vuelos/{id}`), ids Snowflake como string en la respuesta.
- [X] T007 `apps/web/src/app/vuelos/vuelo.service.ts` NUEVO: interfaces y
      métodos `altaVuelo`, `obtenerVuelo`, `cambiarEstadoVuelo`,
      `listarAerolineas`, `listarAeronaves`, `listarTiposVuelo`,
      `listarAeropuertos` (reutiliza `GET /catalogo/aeropuertos` ya
      existente en tenancy, sin duplicar).

**Checkpoint**: los 3 endpoints de catálogo responden con datos reales
contra MonetDB en Docker; `vuelo.service.ts` compila sin errores TS.

---

## Phase 3: User Story 1 - Registrar y actualizar el estado de un vuelo (Priority: P1)

- [X] T008 [US1] `apps/web/src/app/vuelos/estado-tiempo-real/estado-tiempo-real.ts`:
      signals `mostrarModalNuevoVuelo`, campos del formulario de alta
      (aerolinea_id, aeronave_id, numero_vuelo, tipo_vuelo_id,
      fecha_operacion, sentido, aeropuerto_origen_id,
      aeropuerto_destino_id, sta_utc, std_utc, pax_estimado), listas
      cargadas de T007 (aerolíneas/aeronaves/tipos/aeropuertos),
      método `crearVuelo()`.
- [X] T009 [US1] `estado-tiempo-real.ts`: signal `vueloEditandoEstado`,
      campo `estadoNuevo`, método `cambiarEstado()` -- usa el
      `vuelo_id` de la fila ya cargada, nunca pedido a mano
      (research.md Decisión 5); catálogo de 6 estados ya definido en
      `ETIQUETAS_ESTADO` (S1.14) reutilizado como opciones del
      `<select>`.
- [X] T010 [US1] `estado-tiempo-real.html`: botón "Nuevo vuelo" en
      `.consola__acciones`; columna "Acciones" en la tabla con botón
      "Cambiar estado" por fila; modal de alta (`.ah-modal-fondo`/
      `.ah-modal`, campos `.ah-campo`, selects poblados de T007) y modal
      de cambio de estado (research.md Decisión 3).
- [X] T011 [US1] `estado-tiempo-real.ts`: tras un alta o cambio de estado
      exitoso, refrescar la fila afectada en `eventos`/estado local sin
      esperar al WebSocket (UX inmediata) y mostrar toast de
      confirmación (`ToastService`, mismo patrón que el resto del
      sistema).
- [X] T012 [US1] `estado-tiempo-real.ts`: manejo de error 409
      (`TransicionEstadoInvalida`) y 422 con `mensajeDeError()`
      (`auth.service.ts`), mostrado dentro del modal, sin cerrarlo.

**Checkpoint**: US1 verificable -- Escenario 2 de quickstart.md.

---

## Phase 4: User Story 2 - Contrato de API confiable (Priority: P2)

- [X] T013 [US2] `.github/workflows/ci.yml`: en el job `contrato-api`,
      agregar un paso que corre `tools/generar_openapi.py` a un archivo
      temporal (requiere `uv`/dependencias del gateway disponibles en el
      runner, mismo entorno que el job `pruebas-unitarias`) y falla
      (`diff` con código de salida distinto de 0) si difiere de
      `docs/api/openapi.yaml` comiteado.
- [X] T014 [US2] `docs/api/openapi.yaml`: regenerar una segunda vez tras
      T006-T007 (agregó rutas nuevas) para que el contrato final incluya
      también los 3 endpoints de catálogo de este mismo sprint.

**Checkpoint**: US2 verificable -- Escenario 1 de quickstart.md.

---

## Phase 5: User Story 3 - Endpoints huérfanos (Priority: P3)

- [X] T015 [US3] `apps/web/src/app/puertas/puertas.service.ts`: método
      `cancelarAsignacion(asignacionId: string): Observable<void>` →
      `POST /puertas/asignaciones/{id}/cancelar`.
- [X] T016 [US3] `apps/web/src/app/puertas/tablero-puertas/tablero-puertas.html`/`.ts`:
      botón "Cancelar" dentro del modal "Ver asignaciones" (ya existe
      desde el rediseño operativo del 2026-08-04), por fila de
      asignación; tras cancelar, refresca el tablero y muestra toast.
- [X] T017 [US3] `apps/web/src/app/auth/auth.service.ts`: método
      `solicitarVerificacion(): Observable<unknown>` →
      `POST /auth/solicitar-verificacion`.
- [X] T018 [US3] `apps/web/src/app/shell/shell.ts`: computed
      `mostrarBannerVerificacion` (`perfil()?.email_verificado === false`)
      y método `reenviarVerificacion()` (research.md Decisión 4 -- vive
      en el shell, no en la vista pública `auth/verificar-correo`, porque
      el endpoint exige sesión).
- [X] T019 [US3] `apps/web/src/app/shell/shell.html`/`.scss`: banner
      condicional con el texto de aviso y el botón de reenvío, con toast
      de confirmación al enviarse.

**Checkpoint**: US3 verificable -- Escenario 3 de quickstart.md.

---

## Phase 6: Polish y verificación

- [X] T020 [P] `pytest` para `consultas_catalogo.py` (T002): al menos un
      test de integración contra MonetDB real por consulta, confirmando
      que el join aeronave→modelo_aeronave trae los campos esperados.
- [X] T021 [P] `docs/PLAN_IMPLEMENTACION_v3.0.md` §8-bis.1: marcar S1.15
      con su commit al cerrar (dejar el placeholder listo).
- [X] T022 [P] `CLAUDE.md`: fila S1.15 en la tabla de sprints + resumen
      de lo implementado, mismo formato que las filas S1.11-S1.14.
- [X] T023 `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre
      `services/aodb` completo (Principio IV).
- [X] T024 Ejecutar los 3 escenarios de quickstart.md contra Docker real
      (`docker compose up -d --build gateway web`).
- [X] T025 Build de producción de `apps/web` en verde.

## Dependencies

- Fase 1 (T001) no bloquea nada más que sí misma -- es independiente,
  pero se hace primero para partir de un contrato sincronizado.
- Fase 2 (Foundational) bloquea US1: sin los 3 endpoints de catálogo y
  `vuelo.service.ts`, el formulario de alta no tiene de dónde poblar sus
  selects (FR-010).
- US1 (Fase 3), US2 (Fase 4) y US3 (Fase 5) son independientes entre sí
  una vez completada la Fase 2 -- tocan archivos distintos sin solapar
  (vuelos vs. CI vs. puertas/shell).
- T014 depende de que T006 (endpoints de catálogo) ya exista, para que el
  contrato final los incluya.
- Fase 6 depende de que las 3 historias estén completas.

## Parallel Example

```text
# Tras completar Fase 1 y Fase 2:
Task T008, T009, T010, T011, T012   (US1 -- superficie de vuelos)
Task T013, T014                      (US2 -- contrato de API)
Task T015, T016, T017, T018, T019    (US3 -- endpoints huérfanos)
# Las 3 no comparten archivo -- ejecutables en paralelo real, a
# diferencia de S1.14 donde las 3 historias tocaban el mismo componente.
```

## Implementation Strategy

**MVP = US1 solo**: con Fase 1+2+3 completas, M1 AODB deja de ser
solo-lectura desde la aplicación -- el caso de uso que motivó toda la
Fase 1.5. US2 y US3 son mejoras de confiabilidad y limpieza que no
bloquean la demostración del MVP.

## Notes

- Cero cambios al contrato HTTP de los 3 endpoints de vuelos ni de los 2
  huérfanos -- ya existen y ya están probados (spec.md Assumptions).
- `domain/` de `aerohub_aodb` no cambia -- sin regla de negocio nueva,
  solo consultas de catálogo de solo lectura.
- Commit solo si se pide explícitamente.
