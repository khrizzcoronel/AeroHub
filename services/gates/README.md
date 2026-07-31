# services/gates — M3 — Terminal & Gate Manager

| Campo | Valor |
|:---|:---|
| Departamento propietario | D1 |
| Esquema de datos | `ops` |
| Paquete instalable | `aerohub_gates` |

Estructura de capas (ADR-017 §5.4 — regla de dependencia verificada por `import-linter`):

```
api ──► application ──► domain ◄── infrastructure ──► packages/repository
```

- `aerohub_gates/domain/` — entidades e invariantes puros. **No importa** FastAPI, SQLAlchemy ni ningun driver.
- `aerohub_gates/application/` — casos de uso (CU-*), orquestacion, limites transaccionales. Importa `domain`; nunca `api`.
- `aerohub_gates/api/` — routers FastAPI, DTOs Pydantic v2. Importa `application`; **nunca** `infrastructure` ni `packages/repository` directamente.
- `aerohub_gates/infrastructure/` — adaptadores. **Unico** subpaquete que invoca `packages/repository` (P1, PN-15).

Prohibido importar `domain` o `application` de otro modulo de `services/`; la comunicacion inter-modulo es por puerto o evento declarado en `packages/contracts`.
