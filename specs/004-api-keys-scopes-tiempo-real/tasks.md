# Tasks: API del AODB -- API Keys, scopes, rate limiting y WebSocket en tiempo real

**Input**: Design documents from `specs/004-api-keys-scopes-tiempo-real/`

**Estado**: retroactivo -- todas las tareas completadas y commiteadas en `14d75ab`.

## Phase 1: Autenticación dual y scopes (US1, US2) 🎯

**Goal**: JWT corto o API Key, con scopes de grano fino verificados por endpoint.

- [X] T001 [P] [US1] `services/tenancy/aerohub_tenancy/domain/api_key.py`
- [X] T002 [P] [US1] `db/ddl/monetdb`: tabla `tenants.api_key`
- [X] T003 [US1] `services/tenancy/aerohub_tenancy/application/gestionar_api_key.py`
      (crear/revocar, secreto se muestra una sola vez)
- [X] T004 [US1] `services/gateway/aerohub_gateway/infrastructure/api_key.py`:
      validación de `X-Api-Key`
- [X] T005 [US1] `services/gateway/aerohub_gateway/api/middleware.py`:
      autenticación dual (Bearer JWT o `X-Api-Key`)
- [X] T006 [US1] JWT ahora de corta vida (15 min) con claim `scopes`
- [X] T007 [P] [US2] `packages/contracts/aerohub_contracts/scopes.py`:
      `requiere_scope()`
- [X] T008 [US2] Aplicar `requiere_scope` a los endpoints de `services/aodb`
- [X] T009 [US2] Verificar PN-06 (API Key revocada/expirada → 401 auditado)
- [X] T010 [US2] Verificar PN-07 (JWT expirado o scope insuficiente →
      401/403 sin fuga de información)

**Checkpoint**: autenticación dual + scopes verificados con PN-06/PN-07 reales.

## Phase 2: Rate limiting (US4)

- [X] T011 `services/gateway/aerohub_gateway/infrastructure/limitador.py`:
      cubo de fichas en memoria por tenant+rol
- [X] T012 `services/gateway/aerohub_gateway/application/limitar_tasa.py`
- [X] T013 Verificar 429 al agotar cupo

**Checkpoint**: rate limiting verificado con HTTP real.

## Phase 3: WebSocket de estado en tiempo real (US3)

- [X] T014 [P] [US3] `packages/contracts/aerohub_contracts/ws_auth.py`:
      `autenticar_websocket()` (JWT por query string)
- [X] T015 [US3] `services/aodb/aerohub_aodb/infrastructure/eventos.py`:
      broadcaster en proceso (`queue.Queue` por tenant)
- [X] T016 [US3] `services/aodb/aerohub_aodb/application/tiempo_real.py`:
      suscribir/desuscribir
- [X] T017 [US3] `services/aodb/aerohub_aodb/api/router.py`: WS
      `/vuelos/ws/estado`
- [X] T018 [US3] `apps/web/src/app/vuelos/estado-tiempo-real/`: vista Angular mínima
- [X] T019 [US3] Fixture `servidor_real` (subprocess uvicorn) para medir
      RNF-P01 -- `TestClient` in-process produce deadlock WS+HTTP
- [X] T020 [US3] Medir RNF-P01: 100 cambios de estado concurrentes, latencia
      máxima de propagación < 1s
- [X] T021 [US3] Corregir hallazgo: MonetDB aborta con SQLSTATE 40001 bajo
      escritura concurrente sobre tablas transversales -- agregar
      `aerohub_repository.reintentar_en_conflicto` (backoff + jitter) a las
      3 mutaciones de negocio principales
- [X] T022 [US3] Documentar el hallazgo y el límite de paralelismo sostenible
      (~3 escritores) en `docs/runbooks/monetdb.md`

**Checkpoint**: WS de estado de vuelo verificado en navegador real, RNF-P01
medido y en verde.

## Phase N: Contrato OpenAPI y polish

- [X] T023 `tools/generar_openapi.py`: genera `docs/api/openapi.yaml` desde
      la app FastAPI
- [X] T024 `.spectral.yaml`: reglas de lint sobre el OpenAPI generado, 0 errores
- [X] T025 Verificación final: 211/211 tests, ruff/mypy/bandit/import-linter
      en verde, build/lint/test de Angular en verde

## Notes

- Commit real: `14d75ab` -- "S1.2 -- API del AODB, OpenAPI 3.1 y tiempo real"
- El patrón "servidor uvicorn real vía subprocess para medir latencia WS bajo
  carga" se reutiliza en S1.3 (RNF-P02) y S1.4 (PN-05 concurrente).
