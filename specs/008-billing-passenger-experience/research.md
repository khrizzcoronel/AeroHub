# Fase 0 -- Investigación: M5 Revenue & Billing + M6 Passenger Experience

**Feature**: [spec.md](./spec.md) | **Fecha**: 2026-08-01

No quedan `[NEEDS CLARIFICATION]` en `spec.md` (checklist 16/16 en la
primera pasada) -- CU-O17/CU-O19 ya resolvían las ambigüedades previstas.
Esta fase documenta las decisiones técnicas que sí hacía falta fijar antes
de diseñar `data-model.md`.

## Decisión 1: Motor de facturación como caso de uso "Sistema", sin cron

- **Decisión**: `calcular_cargos_periodo(tenant_id, aerolinea_id,
  periodo_inicio, periodo_fin)` es un caso de uso de `application/`
  invocado vía endpoint HTTP (`POST /billing/facturacion/calcular`), no un
  job periódico ni un ciclo de fondo.
- **Racional**: CU-O17 define el actor como "Sistema (motor de
  facturación)", pero eso describe la AUSENCIA de intervención humana en el
  cálculo (nadie edita montos a mano), no que deba ser un cron. El plan de
  sprint no pide programación automática, y mantenerlo como acción
  explícita conserva el patrón ya usado en S1.4/S1.5 (`finalizar_tarea`,
  `asignar_puerta`): domain valida -> transacción única -> eventos después
  del commit. Introducir un scheduler sería una dependencia de
  infraestructura nueva no pedida por ningún requisito (RF-O15/RF-O17/RF-T10
  no mencionan periodicidad de ejecución, solo periodicidad de vigencia de
  tarifas y de agregación de tiempos de espera).
- **Alternativas consideradas**: (a) Celery/APScheduler con cron mensual --
  rechazada, complejidad no solicitada y sin precedente en el stack
  (ningún otro módulo usa un scheduler); (b) trigger de base de datos --
  rechazada, MonetDB no soporta triggers equivalentes (mismo hallazgo que
  motivó el patrón append-only de `compliance.log_auditoria`).

## Decisión 2: Estimación de tiempos de espera como cálculo agregado bajo demanda con ventana de frescura

- **Decisión**: `POST /passenger/tiempos-espera/recalcular` (invocable
  manualmente o por un futuro scheduler externo, fuera de alcance de este
  sprint) recorre `ops.asignacion_puerta` + `rampa.turnaround` para la
  ventana horaria solicitada y hace UPSERT en
  `billing.tiempo_espera_agregado` por `(tenant_id, terminal_id, fecha,
  franja_inicio)`. `GET /passenger/tiempos-espera` sirve lecturas.
- **Racional**: RF-O17 exige frescura <= 15 minutos, no un mecanismo de
  cálculo específico. Mantener el cálculo como caso de uso invocable
  (mismo patrón que Decisión 1) permite verificar la frescura empíricamente
  sin depender de infraestructura de scheduling nueva; la responsabilidad
  de invocarlo cada <= 15 min es operativa (Docker healthcheck/cron del
  host), no del dominio.
- **Alternativas consideradas**: cálculo síncrono en cada `GET` -- rechazada,
  reconstruir el agregado en cada lectura no es lo que describe CU-O19
  ("Sistema" como actor que produce el agregado, no el lector).

## Decisión 3: Propiedad de `billing.tiempo_espera_agregado` por `aerohub_passenger`, no por `aerohub_billing`

- **Decisión**: la tabla vive físicamente en el esquema SQL `billing` (así
  la nombra el SDD §9.8), pero el módulo que la declara, escribe y expone
  es `aerohub_passenger` (M6), no `aerohub_billing` (M5).
- **Racional**: el nombre del esquema SQL agrupa por dominio de negocio
  (D3, Tarifación y Facturación) tal como lo hace `ops` para D1 -- ya hay
  precedente de que un módulo de negocio (`aerohub_gates`, `aerohub_ramp`)
  escribe en un esquema (`ops`) sin que ese esquema lleve su nombre. M6 es
  conceptualmente independiente de M5 (RF-O17 no depende de RF-O15), así
  que exigir que pase por `aerohub_billing` violaría la independencia de
  módulos (`.importlinter`) sin necesidad real. `aerohub_billing` no
  importa ni expone esta tabla.
- **Alternativas consideradas**: mover `tiempo_espera_agregado` a un
  esquema `passenger` nuevo -- rechazada, el SDD (fuente de verdad del
  esquema físico) ya fija el nombre `billing.tiempo_espera_agregado`, y
  esta feature no tiene mandato para modificar el DDL ya especificado.

## Decisión 4: Segregación de funciones -- `role_support` sin acceso a `billing`

- **Decisión**: ningún alcance (`ALCANCE`) de `aerohub_billing` ni
  `aerohub_passenger` se registra para `role_support`. La matriz de
  privilegios (`docs/estrategia/...v6.0.md` §4.3.1) marca la celda
  `role_support` x `billing` como `—` explícitamente.
- **Racional**: es una prueba negativa explícita del sprint (compuerta de
  pruebas), igual que el patrón de mínimo privilegio ya probado para
  `role_ramp_agent` en S1.5 -- se verifica con un test de integración que
  intenta una consulta con `role_support` y espera 403/404 del guardián
  G1/G2, no solo lectura de la matriz.
- **Alternativas consideradas**: ninguna -- es un requisito explícito, no
  una decisión de diseño abierta.

## Decisión 5: Inmutabilidad financiera vía denormalización deliberada, sin recálculo

- **Decisión**: `cargo_aeronautico.tarifa_aplicada` /
  `.monto_calculado` y `factura_linea.precio_unitario` / `.monto` se
  escriben una sola vez, en el momento del cálculo, y nunca se
  recalculan desde `tarifario_concepto` ni desde `cargo_aeronautico`.
- **Racional**: exactamente como lo especifica el SDD §9.4 --
  "denormalización deliberada, instantánea inmutable" -- y como lo exige
  RNF de integridad financiera (ISO/IEC 27002 8.15, citado en el propio
  SDD). Verificado empíricamente en el sprint con un test que cambia
  `tarifario_concepto.tarifa_unitaria` DESPUÉS de calcular un cargo y
  confirma que el cargo y la factura ya emitida no cambian.
- **Alternativas consideradas**: vista calculada (`JOIN` a
  `tarifario_concepto` en el momento de leer) -- rechazada explícitamente
  por el propio SDD, que documenta el riesgo de alterar cargos históricos
  si la tarifa vigente cambia.

## Decisión 6: `factura`/`conciliacion_pax` sin columnas derivadas (3NF)

- **Decisión**: `factura.total` se calcula por agregación de
  `factura_linea.monto` en el momento de leer (no se persiste);
  `conciliacion_pax.diferencia` se calcula como
  `pax_reportado_aerolinea - pax_registrado_sistema` en el momento de leer.
- **Racional**: así lo fija el SDD §9.5 y §9.7 explícitamente ("factura sin
  total", "sin diferencia"), y es consistente con el patrón ya usado en
  módulos previos de preferir 3NF sobre denormalización salvo justificación
  explícita (que sí existe para `cargo_aeronautico`/`factura_linea`, ver
  Decisión 5, pero no para estos dos totales).
- **Alternativas consideradas**: columna persistida + trigger de
  recálculo -- rechazada, MonetDB no soporta triggers (mismo hallazgo que
  Decisión 1).

## Stack técnico (sin alternativas nuevas -- hereda del proyecto)

- **Lenguaje/Runtime**: Python 3.12, FastAPI, SQLAlchemy Core (sin ORM,
  patrón establecido desde S0.2).
- **Storage**: MonetDB, esquema `billing` (`db/ddl/monetdb/12_billing.sql`
  nuevo).
- **Testing**: `pytest` unit (dominio: cálculo de cargos, derivación de
  `total`/`diferencia`, `excede_estandar`-style helpers) + integration
  (inmutabilidad, conciliación diferencia-cero, PN-11, segregación de
  funciones) vía `TestClient` contra MonetDB real en Docker.
- **Frontend**: Angular standalone, `signal()`/`inject()`, mismo patrón de
  `apps/web/src/app/rampa/panel-turnaround/` -- vista de revisión/disputa
  de facturas para `role_billing_officer` (`frontend-design` skill
  aplicado al diseñarla, per regla de `CLAUDE.md`).
