# Tasks: M5 Revenue & Billing + M6 Passenger Experience

**Input**: Design documents from `specs/008-billing-passenger-experience/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: incluidas -- la constitución (Principio III, Principio IV) exige
verificación empírica y calidad continua en verde; cada historia trae sus
pruebas de integración contra MonetDB real, no mocks.

**Organización**: por historia de usuario (US1-US4 de `spec.md`), en orden
de prioridad (P1, P1, P2, P2).

## Phase 1: Setup

**Propósito**: scaffolding compartido -- YA EXISTE parte de esto (creado al
inicio del sprint): `services/billing/` y `services/passenger/` tienen
`pyproject.toml` registrados en el workspace raíz (`uv.lock` pendiente de
regenerar tras agregar dependencias reales) y subpaquetes vacíos
`domain/application/infrastructure/api`.

- [X] T001 Confirmar/completar `services/billing/pyproject.toml` y
      `services/passenger/pyproject.toml` (dependencias ya declaradas:
      `fastapi`, `pydantic`, `aerohub-kernel`, `aerohub-contracts`,
      `aerohub-repository` -- sin dependencias nuevas de negocio)
- [X] T002 [P] Confirmar `.importlinter`: agregar `aerohub_billing` y
      `aerohub_passenger` como contratos de independencia de módulo
      (mismo patrón que `aerohub_gates`/`aerohub_ramp`)
- [X] T003 Regenerar `uv.lock` dentro del contenedor del gateway
      (`docker cp aerohub-gateway:/app/uv.lock .`) tras registrar los
      módulos nuevos, per hallazgo empírico de S1.5

---

## Phase 2: Foundational (bloqueante para todas las historias)

**Propósito**: DDL del esquema `billing` completo + grants + catálogo
sembrado -- ninguna historia puede implementarse sin esto.

**⚠️ CRÍTICO**: ninguna tarea de US1-US4 empieza antes de cerrar esta fase.

- [X] T004 `db/ddl/monetdb/12_billing.sql`: las 8 tablas de
      [data-model.md](./data-model.md) transcritas fielmente del SDD §9
      (`concepto_cargo`, `tarifario`, `tarifario_concepto`,
      `cargo_aeronautico`, `factura`, `factura_linea`, `conciliacion_pax`,
      `tiempo_espera_agregado`), con todos los CHECK/UNIQUE/FK
      especificados
- [X] T005 `db/ddl/monetdb/98_grants_billing.sql`: grants por rol según
      la matriz (`role_platform_admin` U,S; `role_tenant_admin` U,S
      facturas propias; `role_airline_coordinator` U,S sus cargos;
      `role_billing_officer` U,S,Up disputas; `role_operations_controller`
      -- solo lo necesario para `tiempo_espera_agregado`) -- **sin
      ninguna entrada para `role_support`** (FR-008)
- [X] T006 [P] `db/seeds/generate.py`: sembrar `CONCEPTO_CARGO` (tasa de
      aterrizaje, uso de manga, estacionamiento, tasa por pasajero) como
      catálogo global, mismo patrón que `TIPOS_TAREA` (S1.5)
- [X] T007 [P] `services/billing/aerohub_billing/infrastructure/tablas.py`:
      `Table()` de las 7 tablas propias de `aerohub_billing`
- [X] T008 [P] `services/passenger/aerohub_passenger/infrastructure/tablas.py`:
      `Table()` propia de `billing.tiempo_espera_agregado` (redeclarada
      localmente, NO importa `aerohub_billing` -- ver research.md
      Decisión 3) + redeclaración local de `ops.terminal`,
      `ops.asignacion_puerta`, `rampa.turnaround` para lectura
- [X] T009 [P] `services/billing/aerohub_billing/infrastructure/alcances.py`
      y `services/passenger/aerohub_passenger/infrastructure/alcances.py`:
      registro G1 idempotente de alcance `tenant`/`global` por tabla (ver
      tabla de alcances en data-model.md)
- [X] T010 Verificación empírica: aplicar el DDL contra MonetDB real en
      Docker (`docker compose exec monetdb ...` o `pymonetdb` directo,
      nunca `mclient` por el hallazgo de caracteres UTF-8 de S1.4),
      confirmar las 8 tablas creadas con sus constraints

**Checkpoint**: esquema `billing` completo y verificado en MonetDB real --
las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - El motor de facturación calcula la factura mensual automáticamente (Priority: P1) 🎯 MVP

**Goal**: `POST /billing/facturacion/calcular` consolida hechos
facturables del período en `cargo_aeronautico` con el tarifario vigente, y
los agrupa en una `factura` cuyo total se deriva de sus líneas.

**Independent Test**: cerrar un período con vuelos ya registrados,
ejecutar el cálculo, confirmar que la factura resultante concilia al 100%
con los movimientos del período (RF-O15) -- Escenario en
[quickstart.md](./quickstart.md).

### Tests para US1

- [X] T011 [P] [US1] Test de dominio: `calcular_monto(cantidad,
      tarifario_concepto)` respeta `monto_minimo`/`monto_maximo` en
      `services/billing/tests/unit/test_cargo_aeronautico.py`
- [X] T012 [P] [US1] Test de integración: cálculo de facturación genera un
      `cargo_aeronautico` por hecho facturable y una `factura` cuyas
      líneas referencian cada cargo exactamente una vez, en
      `services/billing/tests/integration/test_calcular_facturacion.py`
- [X] T013 [P] [US1] Test de integración: período sin vuelos completados
      produce cero cargos y ninguna factura (edge case de spec.md, no es
      error)

### Implementación de US1

- [X] T014 [P] [US1] `services/billing/aerohub_billing/domain/tarifario.py`:
      `vigente_en(fecha)`, `validar_unico_vigente()`
- [X] T015 [P] [US1] `services/billing/aerohub_billing/domain/cargo_aeronautico.py`:
      `calcular_monto(cantidad, tarifario_concepto)` con clamp a
      `monto_minimo`/`monto_maximo`
- [X] T016 [P] [US1] `services/billing/aerohub_billing/domain/factura.py`:
      construcción de líneas desde cargos, validación de estado inicial
- [X] T017 [US1] `services/billing/aerohub_billing/application/gestionar_tarifario.py`:
      crear tarifario (borrador), agregar `tarifario_concepto`, activar
      (falla 409 si ya hay uno vigente para el mismo `(tenant_id, moneda)`)
- [X] T018 [US1] `services/billing/aerohub_billing/application/calcular_facturacion.py`
      (CU-O17): consolida hechos de `ops` del período, aplica tarifario
      vigente en la fecha de cada vuelo, INSERT de `cargo_aeronautico` +
      `factura`/`factura_linea` en una única transacción,
      `@reintentar_en_conflicto()` (depende de T014-T016)
- [X] T019 [US1] `services/billing/aerohub_billing/infrastructure/consultas.py`:
      `total` de factura derivado por `SUM(factura_linea.monto)`, nunca
      columna
- [X] T020 [US1] `services/billing/aerohub_billing/api/router.py`:
      `POST /billing/tarifarios`, `POST /billing/tarifarios/{id}/conceptos`,
      `POST /billing/tarifarios/{id}/activar`,
      `POST /billing/facturacion/calcular`, `GET /billing/facturas`,
      `GET /billing/facturas/{id}` (per
      [contracts/billing-api.md](./contracts/billing-api.md))
- [X] T021 [US1] Montar `router_billing` en `services/gateway/main.py`
      (mismo patrón que `router_ramp`)

**Checkpoint**: US1 funcional e independientemente verificable --
Escenario 1 y 2 de `quickstart.md` (parcial, sin disputa aún).

---

## Phase 4: User Story 2 - Cambiar el tarifario vigente no altera facturas históricas (Priority: P1)

**Goal**: garantizar que `tarifa_aplicada`/`monto_calculado` en
`cargo_aeronautico` (y `precio_unitario`/`monto` en `factura_linea`) son
instantáneas inmutables -- publicar un tarifario nuevo nunca modifica
cargos ya calculados.

**Independent Test**: calcular una factura con el tarifario A vigente,
publicar el tarifario B, confirmar que la factura ya emitida conserva los
montos de A -- Escenario 1 de `quickstart.md`.

### Tests para US2

- [X] T022 [P] [US2] Test de integración: `UPDATE
      tarifario_concepto.tarifa_unitaria` después de calcular un cargo no
      altera `tarifa_aplicada`/`monto_calculado` del cargo ya existente,
      en `services/billing/tests/integration/test_inmutabilidad_tarifa.py`
      (compuerta de pruebas obligatoria del sprint)
- [X] T023 [P] [US2] Test de integración: cargos calculados DESPUÉS de
      publicar el tarifario nuevo sí usan la tarifa nueva (la
      inmutabilidad no congela el sistema completo)

### Implementación de US2

- [X] T024 [US2] Confirmar en `calcular_facturacion.py` (T018) que
      `tarifa_aplicada`/`monto_calculado` se copian por valor en el
      momento del INSERT, sin FK "viva" que permita un JOIN posterior a
      `tarifario_concepto` para servir esos valores -- ya cubierto por el
      diseño de T015/T018, esta tarea es la verificación explícita
- [X] T025 [US2] Confirmar que `factura_linea.precio_unitario`/`.monto`
      (T016/T018) se copian de `cargo_aeronautico`, no se derivan en
      lectura -- mismo criterio que T024

**Checkpoint**: SC-002 verificado explícitamente (no solo por diseño) --
inmutabilidad financiera comprobada contra MonetDB real.

---

## Phase 5: User Story 3 - El operador de facturación concilia la factura y registra disputas (Priority: P2)

**Goal**: `role_billing_officer` revisa la factura, la concilia contra
`conciliacion_pax` (diferencia derivada, cero para éxito) y puede
disputar una factura sin alterar el cálculo original.

**Independent Test**: conciliar una factura y confirmar diferencia cero;
registrar una disputa y confirmar que la línea queda trazada sin alterar
`monto_calculado` -- Escenario 2 de `quickstart.md`.

### Tests para US3

- [X] T026 [P] [US3] Test de integración: conciliación con conteos
      iguales -> `diferencia == 0` -> `POST .../conciliar` responde 200,
      en `services/billing/tests/integration/test_conciliacion.py`
- [X] T027 [P] [US3] Test de integración: conciliación con conteos
      distintos -> `POST .../conciliar` responde 409 (no se puede forzar
      diferencia != 0)
- [X] T028 [P] [US3] Test de integración: `POST
      /billing/facturas/{id}/disputar` transiciona a `disputada` sin
      modificar ningún `monto_calculado` de los cargos referenciados
- [X] T029 [US3] Test de integración (segregación de funciones): request
      con `role_support` contra `GET /billing/facturas` responde 404, no
      403 (PN-01) -- compuerta de pruebas obligatoria del sprint,
      Escenario 4 de `quickstart.md`

### Implementación de US3

- [X] T030 [P] [US3] `services/billing/aerohub_billing/domain/conciliacion_pax.py`:
      `diferencia()` derivada, `puede_conciliar()`
- [X] T031 [US3] `services/billing/aerohub_billing/application/conciliar_pax.py`:
      crear `conciliacion_pax`, marcar `conciliado_en`/
      `conciliado_por_usuario_id` (de `contexto_usuario_id()`) solo si
      `diferencia == 0`
- [X] T032 [US3] `services/billing/aerohub_billing/application/disputar_factura.py`:
      transición `emitida` -> `disputada`, exclusivo de
      `role_billing_officer` (Up "disputas" en la matriz -- no puede
      crear/emitir facturas)
- [X] T033 [US3] Extender `services/billing/aerohub_billing/api/router.py`:
      `POST /billing/conciliaciones`,
      `POST /billing/conciliaciones/{id}/conciliar`,
      `POST /billing/facturas/{id}/disputar`
- [X] T034 [US3] Confirmar en `alcances.py` (T009) que ningún alcance de
      `aerohub_billing` se registra para `role_support` -- verificación
      cruzada con T029

**Checkpoint**: US3 funcional -- ciclo completo de CU-O17 cerrado con
revisión humana. SC-001, SC-003 verificados.

---

## Phase 6: User Story 4 - El sistema estima y publica tiempos de espera por terminal, sin PII (Priority: P2)

**Goal**: `POST /passenger/tiempos-espera/recalcular` agrega
`ops.asignacion_puerta` + `rampa.turnaround` en
`billing.tiempo_espera_agregado` por terminal/franja, con `muestra_n` y
cero campos de PII; `GET /passenger/tiempos-espera` sirve lecturas con
frescura <= 15 min.

**Independent Test**: con datos de ocupación de puertas y turnarounds ya
existentes, ejecutar la estimación y confirmar publicación con
`muestra_n > 0` y 0 columnas de PII -- Escenarios 3 y 5 de
`quickstart.md`.

### Tests para US4

- [X] T035 [P] [US4] Test de dominio:
      `agregacion_por_franja(asignaciones, turnarounds)` produce
      `minutos_estimados`/`muestra_n` correctos, en
      `services/passenger/tests/unit/test_tiempo_espera.py`
- [X] T036 [P] [US4] Test de dominio: franja sin actividad reciente ->
      `muestra_n == 0` -> `descarta_por_muestra_insuficiente()` es `True`
      (no se publica una fila con estimado sin respaldo, edge case de
      spec.md)
- [X] T037 [P] [US4] Test de integración PN-11: `information_schema.columns`
      de `billing.tiempo_espera_agregado` coincide EXACTAMENTE con las 9
      columnas de `data-model.md` -- ninguna columna de pasajero/vuelo/
      agente individual, en
      `services/passenger/tests/integration/test_pn11_sin_pii.py`
- [X] T038 [P] [US4] Test de integración: `GET /passenger/tiempos-espera`
      responde solo los campos del contrato (sin campos extra ocultos en
      el modelo Pydantic de respuesta)
- [X] T039 [US4] Test de integración de frescura: `recalcular` seguido de
      `GET` inmediato -> `calculado_en` a menos de 15 min de `now()`
      (RF-O17, Escenario 5 de `quickstart.md`)
- [X] T040 [US4] Test de integración (segregación de funciones):
      `role_support` contra `GET /passenger/tiempos-espera` responde 404

### Implementación de US4

- [X] T041 [P] [US4] `services/passenger/aerohub_passenger/domain/tiempo_espera.py`:
      `agregacion_por_franja()`, `descarta_por_muestra_insuficiente()`
- [X] T042 [US4] `services/passenger/aerohub_passenger/application/recalcular_tiempos_espera.py`
      (CU-O19): lee `ops.asignacion_puerta` + `rampa.turnaround` del
      terminal/ventana, agrega por franja, UPSERT en
      `billing.tiempo_espera_agregado` por
      `(tenant_id, terminal_id, fecha, franja_inicio)` -- descarta
      franjas con `muestra_n == 0` (depende de T041)
- [X] T043 [US4] `services/passenger/aerohub_passenger/infrastructure/consultas.py`:
      lectura por `(terminal_id, fecha)`, proyección Pydantic limitada a
      las columnas del contrato (sin exponer columnas internas futuras
      por accidente)
- [X] T044 [US4] `services/passenger/aerohub_passenger/api/router.py`:
      `POST /passenger/tiempos-espera/recalcular`,
      `GET /passenger/tiempos-espera` (per
      [contracts/passenger-api.md](./contracts/passenger-api.md))
- [X] T045 [US4] Montar `router_passenger` en `services/gateway/main.py`

**Checkpoint**: US4 funcional -- SC-004, SC-005 verificados. Las 4
historias de usuario están completas e independientemente probadas.

---

## Phase 7: Polish & Cross-Cutting

**Propósito**: vista Angular, regresión completa, cierre del sprint.

- [X] T046 [P] `apps/web/src/app/billing/panel-facturas/`: listar
      facturas, ver detalle con líneas y total derivado, disputar --
      **usar el skill `frontend-design`** antes de diseñar la vista (regla
      de `CLAUDE.md`)
- [ ] T047 [P] `apps/web/src/app/passenger/panel-tiempos-espera/` (opcional,
      solo si el tiempo alcanza -- ver Assumptions de spec.md, sincronía
      con FIDS es stretch, no bloqueante)
- [X] T048 Regresión completa de pruebas negativas PN-01 a PN-11
      existentes (SC-006) -- confirmar que agregar `billing`/`passenger`
      no rompe ningún test previo de `tests/cross_tenant/`
- [X] T049 `ruff check .`, `mypy .`, `bandit -r services/billing
      services/passenger`, `lint-imports` en verde, corriendo dentro del
      contenedor del gateway (Docker, nunca en el host)
- [X] T050 Ejecutar los 5 escenarios de [quickstart.md](./quickstart.md)
      completos contra MonetDB real en Docker (no solo `pytest` con
      `TestClient` -- verificación manual/exploratoria final)
- [ ] T051 Actualizar `CLAUDE.md`: fila S1.6 en "Estado del plan" con el
      hash del commit, una vez cerrado

---

## Dependencies & Execution Order

### Fases

- **Setup (Fase 1)**: sin dependencias, scaffolding parcial ya existe
- **Foundational (Fase 2)**: depende de Setup -- BLOQUEA todas las
  historias
- **US1 (Fase 3, P1)**: depende de Foundational -- es el MVP
- **US2 (Fase 4, P1)**: depende de Foundational + de T014-T018 de US1
  (verifica el comportamiento de inmutabilidad que US1 ya implementa,
  no agrega tablas/endpoints nuevos)
- **US3 (Fase 5, P2)**: depende de Foundational + US1 (opera sobre
  facturas que US1 genera)
- **US4 (Fase 6, P2)**: depende solo de Foundational -- independiente de
  US1-US3 (módulo separado, `aerohub_passenger`), puede desarrollarse en
  paralelo a US1-US3 si hay más de un desarrollador
- **Polish (Fase 7)**: depende de todas las historias que se decida
  incluir en el sprint

### Oportunidades de paralelismo

- Dentro de Foundational: T006-T009 en paralelo (archivos distintos)
- US1 y US4 pueden desarrollarse en paralelo completo (módulos
  independientes) una vez cerrado Foundational
- US2 es mayormente verificación de lo que US1 ya construye -- casi todo
  su trabajo es de pruebas (T022-T023), mínimo código nuevo (T024-T025)
- Dentro de cada historia, todas las tareas de dominio [P] y de pruebas
  [P] en paralelo; `application/`, `api/router.py` y el montaje en el
  Gateway son secuenciales (dependen del dominio/infraestructura)

---

## Implementation Strategy

### MVP primero (US1 + US2)

1. Fase 1: Setup
2. Fase 2: Foundational (crítico, bloquea todo)
3. Fase 3: US1 -- motor de facturación básico
4. Fase 4: US2 -- verificación de inmutabilidad (casi gratis sobre US1)
5. **Validar**: Escenario 1 y 2 de `quickstart.md`
6. Esto ya cubre el requisito de integridad financiera central del
   módulo -- entregable mínimo con valor real

### Entrega incremental

1. Setup + Foundational -> esquema `billing` listo
2. US1 + US2 -> motor de facturación con inmutabilidad garantizada (MVP)
3. US3 -> revisión humana y conciliación (cierra el ciclo de CU-O17)
4. US4 -> M6 completo, en paralelo a US1-US3 si hay capacidad
5. Polish -> vista Angular, regresión, cierre de sprint

---

## Notes

- `role_support` sin acceso a `billing` (FR-008) se verifica en T005
  (grants), T009/T034 (alcances G1/G2) y T029/T040 (pruebas de
  integración) -- tres capas independientes, no solo una convención
  documentada.
- La inmutabilidad (US2) es deliberadamente una fase casi toda de
  pruebas: el diseño correcto ya está en T014-T018 de US1; lo que falta
  es la prueba explícita que lo demuestre contra MonetDB real (Principio
  III de la constitución).
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes -- regla de `CLAUDE.md`, no repetir por sprint.
- T047 (panel Angular de tiempos de espera) queda sin implementar --
  confirmado como stretch/no bloqueante en Assumptions de `spec.md`; M6 es
  verificable end-to-end vía API (contracts/passenger-api.md) y las
  pruebas de integración sin necesidad de UI dedicada.
- T051 queda pendiente hasta que el usuario pida el commit del sprint --
  se completa en ese momento junto con el hash real.
