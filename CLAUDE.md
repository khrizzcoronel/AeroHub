# AeroHub — contexto persistente

Mapa de continuidad entre sesiones, para no tener que re-derivar el estado
del proyecto ni releer todo el historial cada vez que el contexto se
reinicia. La fuente de verdad de arquitectura/requisitos sigue siendo
`docs/PLAN_IMPLEMENTACION_v2.0.md`, `docs/srs/`, `docs/sdd/`, `docs/adr/`
y `docs/estrategia/` — este archivo no los duplica, apunta a ellos y
registra lo que esos documentos no capturan (progreso real, hallazgos
empíricos, reglas de trabajo).

**Al empezar una sesión nueva**: leer este archivo primero. Si el pedido
es "seguir con el siguiente sprint", ir directo a `docs/PLAN_IMPLEMENTACION_v2.0.md`
§8.`<N+1>` (la sección del sprint siguiente al último completado abajo) en
vez de re-explorar el repo entero.

## Metodología: Spec-Driven Development (GitHub Spec Kit) -- OBLIGATORIA desde S1.6

El proyecto usa Spec Kit (`.specify/`, skills `speckit-*` en
`.claude/skills/`). `specs/NNN-<slug>/{spec.md,plan.md,tasks.md}` documenta
cada sprint -- S0.1 a S1.5 se documentaron RETROACTIVAMENTE
(`specs/001-` a `specs/007-`, pedido explícito del usuario el 2026-08-01).

**A partir de S1.6, todo sprint nuevo sigue el flujo Spec Kit ANTES/DURANTE
la implementación, nunca después**: `/speckit-specify` (spec.md a partir de
la sección correspondiente de `docs/PLAN_IMPLEMENTACION_v2.0.md` §8) →
`/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. El siguiente
directorio a crear es `specs/008-<slug>/` para S1.6. Esto es una regla de
trabajo tan firme como "verificar contra MonetDB real" o "todo servicio en
Docker" -- no es opcional ni se retoma "cuando convenga".

La constitución del proyecto vive en `.specify/memory/constitution.md`
(v1.0.0, ratificada 2026-08-01) y formaliza principios ya vigentes desde
S0.1 (aislamiento fail-closed, arquitectura modular, verificación empírica,
calidad en verde, aprobación explícita) -- no inventa reglas nuevas, y ante
cualquier discrepancia con este archivo, la constitución prevalece.

## Estado del plan (`docs/PLAN_IMPLEMENTACION_v2.0.md` §8)

| Sprint | Contenido | Commit |
|---|---|---|
| S0.1 | Fundación del monorepo: arquitectura, workspace, CI | `181b610` |
| S0.2 | Capa de repositorio: guardián de tenant, roles, DDL fundacional | `0cdc813` |
| S1.1 | AODB backend + Angular mínimo (alta de tenant, alta de vuelo) | `72488fe` |
| S1.2 | API Keys, scopes JWT, rate limiting, WS de estado de vuelo | `14d75ab` |
| S1.3 | M2 FIDS: plantillas/pantallas en tiempo real, sin-señal | `55a9e95` |
| S1.4 | M3 Gate Manager: asignación de puertas, PuLP, tablero Angular | `dbe3b23` |
| S1.5 | M4 Ground Operations (turnaround) + dockerización del stack | `0d95b2e` |
| S1.6 | M5 Billing (motor de facturación, tarifarios, conciliación) + M6 Passenger Experience (tiempos de espera sin PII) | `b4c619f` |
| S1.7 | Licenciamiento por módulo (gateway) + M9 Compliance Hub (post-mortem, incidentes, reportes DGAC, SOC2) + rotación de API Keys | `c0ec739` |
| **S1.8** | **Siguiente sprint** | **siguiente** |

Actualizar esta tabla (fila + commit) cada vez que un sprint se cierra con
commit. Es la única fuente de "dónde vamos" que hace falta leer antes de
retomar.

## Reglas de trabajo establecidas (no releer el historial para redescubrirlas)

- Implementar cada sprint DE VERDAD (código real corriendo), no solo
  documentarlo.
- Verificar empíricamente contra MonetDB real (Docker) antes de dar una
  tarea por terminada — nunca confiar solo en tests unitarios/mocks para
  cerrar un sprint.
- Mantener ruff, mypy, bandit, import-linter y pytest en verde en todo
  momento; correrlos antes de reportar cualquier tarea como completa.
- Presentar el diff/resumen de cambios ANTES de commitear. Nunca commitear
  sin que el usuario lo pida explícitamente, aunque el trabajo esté listo.
- **Todo servicio que se use para verificar corre en Docker**
  (`infra/docker-compose.yml`, servicios `gateway`/`web`/`fids-player`),
  nunca suelto en el host (`uv run uvicorn` / `npx nx serve`). Ver
  "Entorno de desarrollo" abajo para los comandos.
- **Usar el skill `frontend-design` siempre que se vaya a desarrollar o
  rediseñar una vista** (`apps/web`, `apps/fids-player`) -- dirección
  estética deliberada, no defaults genéricos de framework.
- **Usar el skill `find-skills` cuando haga falta buscar/evaluar otro skill**
  del ecosistema abierto antes de instalarlo con `npx skills add`.
- Responder siempre en español.

## Patrones arquitectónicos establecidos

Referencia más completa y reciente: `services/ramp/aerohub_ramp/` (S1.5).

- Cada módulo de negocio: `services/<modulo>/aerohub_<modulo>/{domain,application,infrastructure,api}`.
  `domain/` puro (sin SQLAlchemy/FastAPI); `infrastructure/` es el ÚNICO
  subpaquete que importa `aerohub_repository`; `api/` solo traduce HTTP
  ↔ `application/`, ninguna regla de negocio ahí (verificado por
  `.importlinter`).
- Independencia de módulos (`.importlinter`, `sin-importacion-cruzada-entre-modulos`):
  ningún módulo importa `domain`/`application` de otro. Si un módulo
  necesita leer una tabla "propiedad" de otro (p. ej. `ops.vuelo` desde
  `gates`/`ramp`), se REDECLARA la `Table()` localmente en el propio
  `infrastructure/tablas.py` y se re-registra su alcance G1 de forma
  idempotente (ver `aerohub_gates/infrastructure/alcances.py` o
  `aerohub_ramp/infrastructure/alcances.py`).
- IDs: Snowflake de 64 bits (`aerohub_kernel.generar_id`) — SIEMPRE viajan
  como string en JSON (request y response), nunca como número JSON (pierde
  precisión en el navegador por encima de `Number.MAX_SAFE_INTEGER`).
- Mutaciones: domain valida primero (fail fast, antes de tocar la base) →
  `with sesion() as conn:` hace el INSERT/UPDATE + `escribir_journal` +
  `registrar_auditoria` en la MISMA transacción → los eventos de dominio
  se publican DESPUÉS de que la transacción confirma. Decorar con
  `@reintentar_en_conflicto()` toda mutación de negocio (ver hallazgos de
  MonetDB abajo).
- Tenant: nunca se acepta `tenant_id` del body/parámetro — siempre
  `contexto_tenant_id()` (poblado por el middleware del Gateway desde el
  JWT). El guardián G1/G2 (`aerohub_repository.guard`) aborta cualquier
  consulta sobre una tabla de alcance `'tenant'` sin filtro explícito.
  `alcance_global()` es la ÚNICA excepción nominal (procesos de plataforma
  sin tenant ambiente), siempre con `motivo`+`rol` explícitos y auditada.
- 404, nunca 403, cuando un recurso es de otro tenant/usuario (PN-01):
  nunca confirmar que el recurso ajeno existe.
- Mínimo privilegio dentro de un mismo tenant (p. ej. `role_ramp_agent`
  sobre sus propias tareas, S1.5): se implementa en `infrastructure/`
  filtrando por `contexto_usuario_id()` cuando el rol activo lo exige, no
  en el motor (MonetDB no tiene RLS).
- Frontend (`apps/web`, `apps/fids-player`): sin login real todavía — el
  JWT se pega a mano en un textarea. Patrón de componente: standalone,
  todo el estado en `signal()`, `inject()` para DI, manejo de error
  uniforme vía `mensajeDeError(err)` que prioriza `err.error?.detail`.
  `<input type="datetime-local">` no lleva zona horaria — convertir a UTC
  con un helper tipo `aUtcIso()` antes de enviar al backend (si no, el
  backend rechaza con 422 por datetime naive).

## Hallazgos empíricos de MonetDB (ver también `docs/runbooks/monetdb.md`)

- No soporta `SELECT ... FOR UPDATE` ni `EXCLUDE USING gist`. El "bloqueo
  de fila" se simula con un `UPDATE` sin efecto sobre la fila a proteger
  (ver `aerohub_gates/infrastructure/comandos.py::bloquear_puerta_para_asignacion`).
- Concurrencia optimista: dos escrituras concurrentes reales pueden
  abortar con SQLSTATE `40001` ("...will ROLLBACK instead") **o** `42000`
  ("Update failed due to conflict with another transaction") — dos formas
  distintas del mismo fenómeno. `aerohub_repository.reintentar_en_conflicto`
  reconoce ambas.
- `mclient` (CLI) falla con "invalid multibyte sequence" en archivos con
  caracteres UTF-8 (§, acentos) pasados por argumento/heredoc. Para
  aplicar DDL nuevo con esos caracteres, usar `pymonetdb` directo desde
  Python, no `mclient`.

## Entorno de desarrollo

- El binario `uv` **no** está en el PATH del host — dentro de la imagen
  Docker del gateway sí (`services/gateway/Dockerfile` lo instala). Si
  hace falta actualizar `uv.lock`, reconstruir la imagen del gateway y
  copiar el lock resultante (`docker cp aerohub-gateway:/app/uv.lock .`),
  no intentarlo en el host.
- Todo el stack corre en Docker:
  ```bash
  docker compose -f infra/docker-compose.yml up -d monetdb gateway web fids-player
  ```
  Gateway en `:8000`, `web` en `:4200`, `fids-player` en `:4300`.
- Seeds de desarrollo: `uv run python -m db.seeds.generate` (dentro de un
  entorno con `uv`, p. ej. el contenedor del gateway). Tenants canario
  fijos: `MEC` y `UIO` (código/email/vuelos estables, usados por
  `tests/cross_tenant/` y por los `datos_canario` de casi toda la suite de
  integración).
- Verificación manual de endpoints: mintar un JWT de prueba con
  `aerohub_gateway.infrastructure.codificar_jwt(rol=..., tenant_id=...,
  usuario_id=..., scopes=[...])` — no hay login real todavía.
