# services/analytics_api — M7 — consumo analitico

| Campo | Valor |
|:---|:---|
| Departamento propietario | D4 |
| Esquema de datos | `ClickHouse (solo lectura)` |
| Paquete instalable | `aerohub_analytics_api` |

Estructura de capas (ADR-017 §5.4 — regla de dependencia verificada por `import-linter`):

```
api ──► application ──► domain ◄── infrastructure ──► packages/repository
```

- `aerohub_analytics_api/domain/` — entidades e invariantes puros. **No importa** FastAPI, SQLAlchemy ni ningun driver.
- `aerohub_analytics_api/application/` — casos de uso (CU-*), orquestacion, limites transaccionales. Importa `domain`; nunca `api`.
- `aerohub_analytics_api/api/` — routers FastAPI, DTOs Pydantic v2. Importa `application`; **nunca** `infrastructure` ni `packages/repository` directamente.
- `aerohub_analytics_api/infrastructure/` — adaptadores. **Unico** subpaquete que invoca `packages/repository` (P1, PN-15).

Prohibido importar `domain` o `application` de otro modulo de `services/`; la comunicacion inter-modulo es por puerto o evento declarado en `packages/contracts`.
