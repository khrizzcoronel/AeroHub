# Guía de Validación -- M5 Revenue & Billing + M6 Passenger Experience

**Feature**: [spec.md](./spec.md) | **Contratos**:
[billing-api.md](./contracts/billing-api.md),
[passenger-api.md](./contracts/passenger-api.md)

## Prerrequisitos

Todo el stack corre en Docker (regla de `CLAUDE.md`, nunca suelto en el
host):

```bash
docker compose -f infra/docker-compose.yml up -d monetdb gateway web fids-player
```

Seeds de desarrollo (tenants canario `MEC`/`UIO`, ahora incluyendo
`concepto_cargo` sembrados):

```bash
docker compose -f infra/docker-compose.yml exec gateway uv run python -m db.seeds.generate
```

JWT de prueba (sin login real todavía):

```python
from aerohub_gateway.infrastructure import codificar_jwt
token = codificar_jwt(rol="role_billing_officer", tenant_id=<id_MEC>, usuario_id=1, scopes=["billing:write"])
```

## Escenario 1: Inmutabilidad de tarifas históricas (compuerta de pruebas obligatoria)

1. Crear y activar un `tarifario` con un `tarifario_concepto` de
   `tarifa_unitaria = 100.0000`.
2. `POST /billing/facturacion/calcular` para un vuelo del periodo -> anotar
   `cargo_aeronautico.tarifa_aplicada` y `.monto_calculado`.
3. `UPDATE tarifario_concepto SET tarifa_unitaria = 999.0000` directamente
   contra MonetDB (simulando un cambio de tarifa posterior).
4. Releer el `cargo_aeronautico` del paso 2.
5. **Esperado**: `tarifa_aplicada`/`monto_calculado` idénticos al paso 2 --
   NO reflejan `999.0000`.

## Escenario 2: Conciliación factura vs. movimientos, diferencia cero

1. `POST /billing/conciliaciones` con `pax_reportado_aerolinea ==
   pax_registrado_sistema`.
2. `GET` la conciliación -> `diferencia` calculada debe ser `0`.
3. `POST /billing/conciliaciones/{id}/conciliar` -> `200`, se fija
   `conciliado_en`.
4. Repetir con conteos distintos -> `POST .../conciliar` debe responder
   `409` (no se puede conciliar con diferencia != 0).

## Escenario 3: PN-11 -- cero PII en M6

1. `POST /passenger/tiempos-espera/recalcular` para un terminal con
   turnarounds/asignaciones de puerta recientes.
2. `GET /passenger/tiempos-espera` -> inspeccionar el JSON de respuesta.
3. **Esperado**: únicamente `terminal_id`, `fecha`, `franja_inicio`,
   `franja_fin`, `minutos_estimados`, `muestra_n`, `calculado_en`. Ningún
   campo de pasajero, vuelo o agente.
4. Verificación complementaria a nivel de esquema: consultar
   `information_schema.columns` de `billing.tiempo_espera_agregado` y
   confirmar que el conjunto de columnas coincide exactamente con
   `data-model.md`.

## Escenario 4: Segregación de funciones -- `role_support` sin acceso a billing

1. Mintar un JWT con `rol="role_support"`.
2. `GET /billing/facturas` con ese token.
3. **Esperado**: `404` (PN-01 -- nunca `403`, no se confirma que el
   recurso exista).
4. Repetir contra `GET /passenger/tiempos-espera` -> mismo resultado
   esperado (`role_support` tampoco tiene alcance sobre `aerohub_passenger`).

## Escenario 5: Frescura de tiempos de espera (RF-O17, <= 15 min)

1. `POST /passenger/tiempos-espera/recalcular`.
2. Inmediatamente, `GET /passenger/tiempos-espera` para la misma franja.
3. **Esperado**: `calculado_en` está a menos de 15 minutos de `now()`.

## Verificación de calidad (antes de cerrar el sprint)

```bash
docker compose -f infra/docker-compose.yml exec gateway uv run ruff check .
docker compose -f infra/docker-compose.yml exec gateway uv run mypy .
docker compose -f infra/docker-compose.yml exec gateway uv run bandit -r services/billing services/passenger
docker compose -f infra/docker-compose.yml exec gateway uv run lint-imports
docker compose -f infra/docker-compose.yml exec gateway uv run pytest services/billing services/passenger tests/cross_tenant
```

Todos en verde, más los 5 escenarios anteriores verificados empíricamente
contra MonetDB real (no mocks) -- per Principio III de la constitución y
regla de verificación empírica de `CLAUDE.md`.
