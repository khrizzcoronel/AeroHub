# Guía de Validación -- S1.7 Licenciamiento, credenciales y Compliance Hub

**Feature**: [spec.md](./spec.md)

## Prerrequisitos

```bash
docker compose -f infra/docker-compose.yml up -d monetdb gateway web fids-player
docker compose -f infra/docker-compose.yml exec gateway uv run python -m db.seeds.generate
```

## Escenario 1: PN-09 -- módulo sin licencia deniega con 403

1. Tenant canario `MEC` SIN fila de `tenants.licencia` para el módulo
   `BILL` (estado inicial tras seed -- no se siembra ninguna licencia por
   defecto).
2. `GET /billing/facturas` con un token válido de ese tenant.
3. **Esperado**: `403`. Confirmar una fila nueva en
   `compliance.log_auditoria` con `tabla='licencia'`.
4. Insertar una fila de `tenants.licencia` vigente para `(MEC, BILL)`.
5. Repetir el paso 2 -> **Esperado**: `200` (o el código normal del
   endpoint, ya no bloqueado por licencia).
6. Insertar una licencia YA VENCIDA (`activa_hasta` en el pasado) ->
   repetir -> **Esperado**: `403` de nuevo.

## Escenario 2: Post-mortem con excepción de mutabilidad (ADR-009)

1. `role_sre` crea un post-mortem -> `estado='en_progreso'`.
2. Agrega 2 acciones de remediación.
3. Intenta publicar con acciones pendientes -> `409`.
4. Completa ambas acciones.
5. Publica -> `200`, `publicado_en` poblado.
6. Verificar en `compliance.log_auditoria` que la edición de `causa_raiz`
   del paso 1/2 quedó registrada.
7. Repetir el paso 1 con `role_support` -> **Esperado**: rechazo (no es
   `role_sre`).

## Escenario 3: PN-04 reforzada -- append-only por análisis estático

Ejecutar `tests/negative/test_pn04_compliance_append_only.py` (nuevo,
mismo patrón que `test_pn15_sql_fuera_del_repositorio.py`): recorre
`aerohub_compliance.infrastructure` y falla si aparece cualquier función
de mutación sobre `incidente_seguridad`/`reporte_dgac`/`acceso_auditor`/
`evidencia_soc2`.

## Escenario 4: Rotación de API Key auditada

1. `POST /tenants/api-keys` -> crea una key activa.
2. `POST /tenants/api-keys/{id}/rotar` -> nueva key activa, la anterior
   pasa a `estado='revocada'` con `rotada_en` poblado.
3. Confirmar una fila nueva en `compliance.log_auditoria` con
   `tabla='api_key'`, `operacion='UPDATE'`.

## Verificación de calidad

```bash
docker compose -f infra/docker-compose.yml exec gateway uv run ruff check .
docker compose -f infra/docker-compose.yml exec gateway uv run mypy .
docker compose -f infra/docker-compose.yml exec gateway uv run bandit -r services/compliance services/tenancy services/gateway
docker compose -f infra/docker-compose.yml exec gateway uv run lint-imports
docker compose -f infra/docker-compose.yml exec gateway uv run pytest tests/ -q
```

Todos en verde, más los 4 escenarios verificados empíricamente contra
MonetDB real (no mocks).
