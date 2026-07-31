# services/ramp — M4 — Ground Operations

| Campo | Valor |
|:---|:---|
| Departamento propietario | D2 |
| Esquema de datos | `rampa` |
| Paquete instalable | `aerohub_ramp` |

Estructura de capas (ADR-017 §5.4 — regla de dependencia verificada por `import-linter`):

```
api ──► application ──► domain ◄── infrastructure ──► packages/repository
```

- `aerohub_ramp/domain/` — entidades e invariantes puros. **No importa** FastAPI, SQLAlchemy ni ningun driver.
- `aerohub_ramp/application/` — casos de uso (CU-*), orquestacion, limites transaccionales. Importa `domain`; nunca `api`.
- `aerohub_ramp/api/` — routers FastAPI, DTOs Pydantic v2. Importa `application`; **nunca** `infrastructure` ni `packages/repository` directamente.
- `aerohub_ramp/infrastructure/` — adaptadores. **Unico** subpaquete que invoca `packages/repository` (P1, PN-15).

Prohibido importar `domain` o `application` de otro modulo de `services/`; la comunicacion inter-modulo es por puerto o evento declarado en `packages/contracts`.
