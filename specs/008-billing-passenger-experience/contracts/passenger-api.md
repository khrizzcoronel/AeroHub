# Contrato de API -- `aerohub_passenger` (`/passenger`)

Mismas convenciones que [billing-api.md](./billing-api.md). Módulo
independiente (`.importlinter`): no importa `domain`/`application` de
`aerohub_billing`, aunque su tabla física resida en el esquema SQL
`billing` (ver [../research.md](../research.md) Decisión 3).

## `POST /passenger/tiempos-espera/recalcular`

Ejecuta CU-O19: recorre `ops.asignacion_puerta` (ocupación de puerta) +
`rampa.turnaround` (duración real de procesos) del `terminal_id` y
ventana solicitados, agrega en franjas horarias y hace UPSERT en
`billing.tiempo_espera_agregado` por `(tenant_id, terminal_id, fecha,
franja_inicio)`.

Requiere scope de `role_operations_controller` o `role_platform_admin`
(actor "Sistema" en CU-O19 -- invocado por un proceso operativo, no por
`role_support`, que no tiene acceso a ningún dato de `billing`).

Request:
```json
{"terminal_id": "3", "fecha": "2026-08-01", "franja_minutos": 30}
```

Response `200`:
```json
{"franjas_actualizadas": 48, "franjas_descartadas_por_muestra_insuficiente": 2}
```

Una franja se descarta (no se escribe fila) si `muestra_n == 0` -- evita
publicar una estimación de 0 minutos que en realidad es "sin datos".

## `GET /passenger/tiempos-espera`

Lectura pública dentro del tenant (cualquier rol autenticado del tenant;
no expone PII por diseño, así que no requiere un scope más restrictivo
que pertenencia al tenant).

Query params: `terminal_id`, `fecha`.

Response:
```json
{
  "terminal_id": "3",
  "fecha": "2026-08-01",
  "franjas": [
    {"franja_inicio": "08:00:00", "franja_fin": "08:30:00", "minutos_estimados": "12.50", "muestra_n": 34, "calculado_en": "2026-08-01T08:31:02Z"}
  ]
}
```

**Verificación RF-O17 (frescura <= 15 min)**: el test de integración
invoca `recalcular`, espera, y confirma que `calculado_en` de la franja
leída está a menos de 15 minutos de `now()`.

**Verificación PN-11 (0 PII)**: el modelo Pydantic de respuesta
(`FranjaTiempoEsperaResponse`) solo expone los campos de la tabla listados
en `data-model.md` -- ningún campo de pasajero, vuelo o agente individual.
