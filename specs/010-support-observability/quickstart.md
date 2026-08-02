# Quickstart: validación de S1.8

Prerrequisito: stack en Docker corriendo
(`docker compose -f infra/docker-compose.yml up -d monetdb gateway web
prometheus loki grafana`), DDL y seeds aplicados, JWT de prueba minteado
por tenant y por `role_support` (`aerohub_gateway.infrastructure.codificar_jwt`,
ver CLAUDE.md "Entorno de desarrollo").

## Escenario 1 — Ticket con SLA (US1)

1. Como usuario de tenant MEC: `POST /support/tickets` con
   `severidad="alta"`, categoría "AODB". Verificar `sla_objetivo_min <
   120`.
2. Como `role_support`: `POST /support/tickets/{id}/mensajes` con el
   primer mensaje. Verificar que `GET /support/tickets/{id}` ahora
   muestra `primera_respuesta_en` no nulo.
3. Repetir el paso 2 con un segundo mensaje. Verificar que
   `primera_respuesta_en` NO cambió.
4. Como usuario de tenant UIO: `GET /support/tickets/{id}` del ticket
   de MEC → `404` (PN-01).

## Escenario 2 — Uptime y error budget (US2)

1. `GET /support/observabilidad/uptime?servicio=aodb` — verificar que
   responde un porcentaje de uptime y un porcentaje de error budget
   consumido del mes en curso, reflejando las métricas ya expuestas en
   `/metrics` del Gateway.
2. Verificar en Grafana (`localhost:3000`) que el dashboard de uptime
   AODB/FIDS lee de Prometheus como *data source* sin configuración
   manual adicional.

## Escenario 3 — Bloqueo automático de despliegue (US3)

1. Simular consumo de error budget > 80 % (fixture de métricas en el
   test de integración, sin depender de tráfico real).
2. `uv run python tools/verificar_error_budget.py --servicio aodb` →
   código de salida `1`.
3. Repetir con `--override --motivo "prueba"` → código de salida `0` y
   verificar en `compliance.log_auditoria` un evento nuevo
   `esquema='observabilidad'`.
4. Repetir con `--override` sin `--motivo` → código de salida `2`, sin
   fila nueva en `log_auditoria`.

## Escenario 4 — Base de conocimientos y changelog (US4/US5)

1. Como `role_support`: publicar un artículo con dos etiquetas.
2. Como usuario de cualquier tenant: `GET /support/kb/articulos?etiqueta=...`
   → el artículo aparece.
3. Como `role_platform_admin`: publicar un changelog con un ítem de
   módulo `M5` (Billing).
4. Como usuario de un tenant SIN licencia vigente de `M5`:
   `GET /support/changelog` → el ítem de `M5` sigue visible (FR-016,
   el changelog no depende de licencia).
