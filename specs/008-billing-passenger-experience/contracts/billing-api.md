# Contrato de API -- `aerohub_billing` (`/billing`)

Convenciones heredadas de `services/ramp/aerohub_ramp/api/router.py`:
Pydantic para forma de request/response, IDs Snowflake siempre `str` en
JSON, `tenant_id` nunca en el body (de `contexto_tenant_id()`), excepciones
de `application/` traducidas a códigos HTTP por el router (sin regla de
negocio en `api/`).

## `POST /billing/tarifarios`

Crea un tarifario en estado `borrador`. Requiere scope de
`role_billing_officer` o `role_platform_admin`.

Request:
```json
{"nombre": "Tarifario 2026 USD", "moneda": "USD", "vigente_desde": "2026-09-01", "vigente_hasta": null}
```

Response `201`:
```json
{"tarifario_id": "7123456789012345"}
```

## `POST /billing/tarifarios/{tarifario_id}/conceptos`

Agrega/actualiza un `tarifario_concepto` (upsert por `(tarifario_id,
concepto_cargo_id)`).

Request:
```json
{"concepto_cargo_id": "1", "tarifa_unitaria": "125.5000", "monto_minimo": null, "monto_maximo": null}
```

Response `200`: `{"tarifario_concepto_id": "..."}`

## `POST /billing/tarifarios/{tarifario_id}/activar`

Transiciona `borrador` -> `vigente`. Falla (409) si ya existe otro
`tarifario` `vigente` para el mismo `(tenant_id, moneda)`.

## `POST /billing/facturacion/calcular`

Ejecuta CU-O17: para cada vuelo del `aerolinea_id` en el periodo, calcula
`cargo_aeronautico` (si no existe ya uno para ese `(vuelo_id,
concepto_cargo_id)`) usando el `tarifario` vigente en la fecha del vuelo, y
agrupa los cargos no facturados en una `factura` nueva o existente en
estado `borrador` para ese periodo.

Request:
```json
{"aerolinea_id": "42", "periodo_inicio": "2026-08-01", "periodo_fin": "2026-08-31"}
```

Response `200`:
```json
{"factura_id": "...", "cargos_calculados": 118, "cargos_ya_existentes": 0}
```

Errores: `422` si `periodo_fin < periodo_inicio`; `409` si no hay
`tarifario` vigente para algún vuelo del periodo (no se calcula
parcialmente -- todo o nada, transacción única).

## `POST /billing/facturas/{factura_id}/emitir`

Transiciona `borrador` -> `emitida`, fija `emitida_en`/`vence_en`.
Idempotente si ya está `emitida` (200, sin cambios).

## `GET /billing/facturas`

Lista facturas del tenant (`role_tenant_admin`: solo propias por
aerolínea asociada; `role_billing_officer`: todas del tenant;
`role_airline_coordinator`: solo sus cargos, ver matriz).

Query params: `aerolinea_id?`, `estado?`, `periodo_inicio?`, `periodo_fin?`.

Response: incluye `total` **calculado** (agregación de `factura_linea`,
no columna) por cada factura.

## `GET /billing/facturas/{factura_id}`

Detalle con líneas (`factura_linea`) y `total` derivado.

## `POST /billing/facturas/{factura_id}/disputar`

Único método de mutación disponible para `role_billing_officer` sobre una
factura ya emitida (matriz: "Up (disputas)"). Transiciona a `disputada`.

Request: `{"motivo": "..."}`

## `POST /billing/conciliaciones`

Registra un `conciliacion_pax` para `(tenant_id, vuelo_id, periodo)`.

Request:
```json
{"vuelo_id": "...", "periodo": "2026-08", "pax_reportado_aerolinea": 180, "pax_registrado_sistema": 180, "fuente_reporte": "manifiesto_aerolinea"}
```

Response: incluye `diferencia` **calculada** (no columna).

## `POST /billing/conciliaciones/{conciliacion_id}/conciliar`

Marca `conciliado_en`/`conciliado_por_usuario_id` (de
`contexto_usuario_id()`). Solo permitido si `diferencia == 0` -- de lo
contrario `409` (compuerta de pruebas: diferencia cero es condición de
éxito, no un estado que se pueda forzar).

## Segregación de funciones (verificación negativa)

Ningún endpoint de este contrato otorga acceso a `role_support`: cualquier
request con ese rol resuelve `404` (guardián G1/G2, sin alcance
registrado para `role_support` sobre `billing`, PN-01).
