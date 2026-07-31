# ADR-017 — Arquitectura de aplicación: módulos de dominio con capas internas

| Campo | Contenido |
|:---|:---|
| **Estado** | Aceptado |
| **Fecha** | 2026-07-30 |
| **Decide sobre** | Organización estructural del código de la plataforma |
| **Deriva de** | AEROHUB-SRS-001 v2.0 §2.2, §2.3, §2.6, §6.1 · Análisis Estratégico v6.0 §7.1, §8.1–8.2 |
| **Requisitos relacionados** | RNF-M01, RNF-M02, RNF-S02, RNF-U02, RNF-PO01 |
| **Supersede a** | ADR-001 local (monorepo y stack, basado en SRS v1.0/PostgreSQL) — **eliminado** |

---

## Contexto

La SRS v2.0 fija tres restricciones estructurales que cualquier organización del código debe respetar simultáneamente:

1. **Propiedad departamental (§2.2, §3):** cada módulo M1–M9 pertenece a un departamento D1–D6, que es también propietario de su esquema en MonetDB y de los roles que operan sobre él. La segregación de funciones (ISO/IEC 27002, 8.2/8.3) exige que esa propiedad tenga reflejo estructural, no solo documental.
2. **Único emisor de SQL (§2.6, ADR-014):** ningún componente fuera de la capa de repositorio puede emitir SQL hacia MonetDB. Es puerta de release verificada por análisis estático (PN-15).
3. **Frontend único (RNF-U02) con reproductor FIDS como build ligero del mismo monorepo (RNF-PO01).**

La pregunta planteada fue si organizar el sistema por **capas**, por **módulos**, o por ambos, y si procede una división de primer nivel del tipo `front / back / bff / etl`.

### Sobre el BFF

**No se incorpora una capa BFF.** El patrón Backend-for-Frontend estuvo presente en v4.0 bajo Next.js y fue **retirado explícitamente** (SRS v2.0 §6.4; Análisis v6.0 §8.4, ADR-002 de la fuente), con el motivo declarado de "eliminación de doble framework frontend y doble runtime backend". Su función —fachada de agregación y adaptación para el cliente— la cumple hoy el **API Gateway FastAPI**, que además concentra AuthN/AuthZ, rate limiting, validación de licencia por módulo (RF-O18) y la inyección obligatoria del `tenant_id` desde el token (ADR-014). Reintroducir un BFF exigiría un ADR que revierta explícitamente esa decisión (SRS §6.4: *"ningún componente de esta tabla puede reintroducirse sin un nuevo ADR que revierta la decisión correspondiente"*), y duplicaría el punto de inyección de tenant, que es precisamente el control que sustituye al RLS perdido.

---

## Decisión

Se adopta **arquitectura de módulos de dominio con capas internas** (*modular monolith* con corte vertical por bounded context y corte horizontal por responsabilidad), sobre una división de primer nivel por **naturaleza de ejecución**:

```
apps/       → presentación      (Angular: portal, tableros, FIDS player)
services/   → backend           (Gateway + un módulo por bounded context)
packages/   → transversal       (capa de repositorio, contratos, kernel de dominio)
pipelines/  → ETL / orquestación (Airflow, contratos de datos, reconciliación)
ml/         → modelos y MLOps
db/         → DDL y migraciones (MonetDB y ClickHouse)
infra/      → infraestructura declarativa y observabilidad
tests/      → pruebas transversales (negativas, cruzadas, E2E)
```

### Eje vertical — módulos

Un módulo por **bounded context**, en correspondencia 1:1 con el módulo de producto, el departamento propietario y el esquema de datos:

| Módulo de servicio | Módulo de producto | Departamento | Esquema MonetDB |
|:---|:---|:---|:---|
| `services/aodb` | M1 — AODB | D1 | `ops` |
| `services/fids` | M2 — FIDS Management | D1 | `ops` (plantillas/pantallas) |
| `services/gates` | M3 — Terminal & Gate | D1 | `ops` (asignaciones) |
| `services/ramp` | M4 — Ground Operations | D2 | `rampa` |
| `services/billing` | M5 — Revenue & Billing | D3 | `billing` |
| `services/passenger` | M6 — Passenger Experience | D1 | `billing.tiempo_espera_agregado` |
| `services/compliance` | M9 — Compliance Hub | D5 | `compliance` |
| `services/tenancy` | Aprovisionamiento y licencias | D5 | `tenants` |
| `services/support` | Soporte y documentación | D6 | `support` |
| `services/people` | Talento interno | D5 (hosting) | `people` |
| `services/analytics_api` | M7 — consumo analítico | D4 | ClickHouse (lectura) |
| `pipelines/` | M7 — ETL | D4 | `etl_control` + medallion |
| `infra/` + `services/gateway` | M8 — Observability | D5 | — |

### Eje horizontal — capas internas por módulo

```
services/<modulo>/
├─ api/             # routers FastAPI, DTOs Pydantic v2, códigos HTTP
├─ application/     # casos de uso (CU-*), orquestación, límites transaccionales
├─ domain/          # entidades, invariantes, reglas puras — sin framework ni SQL
└─ infrastructure/  # adaptadores; único punto que invoca packages/repository
```

### Regla de dependencias (verificada en CI con `import-linter`)

```
api ──► application ──► domain ◄── infrastructure ──► packages/repository ──► MonetDB
```

1. `domain` **no importa** FastAPI, SQLAlchemy, Airflow ni ningún driver. Es código puro y testeable sin infraestructura.
2. `application` importa `domain` y declara *puertos*; nunca importa `api`.
3. `api` importa `application`; **nunca** `infrastructure` ni `packages/repository` directamente.
4. `infrastructure` es el **único** que importa `packages/repository`, que a su vez es el único que emite SQL (P1, PN-15).
5. **Ningún módulo importa el `domain` o `application` de otro módulo.** La comunicación inter-módulo ocurre por puerto declarado o por evento, respetando la tabla de dependencias de la SRS §2.3 (M2→M1, M3→M1, M4→M1/M3, M5→M1/M3, M6→M2, M7→M1/M4/M5, M9→M1). Una importación cruzada no declarada hace fallar el build.

---

## Alternativas consideradas

| Alternativa | Motivo de descarte |
|:---|:---|
| **Solo capas** (n-tier horizontal global: `presentacion/`, `negocio/`, `datos/`) | Disuelve la propiedad departamental: un cambio en facturación toca los mismos paquetes que operaciones. La segregación de funciones exigida por ISO/IEC 27002 8.2/8.3 y la matriz RBAC por esquema perderían todo reflejo estructural, quedando como convención documental. |
| **Solo módulos** (vertical slices sin capas internas) | Cada módulo resolvería su propio acceso a datos, y el control "único emisor de SQL" tendría N puntos de instalación en lugar de uno. Haría imposible el guardián de tenant de ADR-019 y debilitaría PN-15 hasta volverlo declarativo. |
| **Microservicios desde el inicio** | Equipo de 3–5 personas; la fragmentación en despliegues independientes añade coste operativo (red, consistencia distribuida, observabilidad) sin resolver ninguna restricción de la SRS. El corte modular deja la puerta abierta a extraer un módulo si el volumen lo justifica. |
| **`front / back / bff / etl`** | El `bff` está retirado por decisión vigente (§6.4). Además, un `back` indiferenciado colapsa los nueve módulos y sus seis propietarios departamentales en un único bloque, reintroduciendo el problema de "solo capas". La división por naturaleza de ejecución se conserva (`apps` / `services` / `pipelines`), pero el corte de dominio ocurre **dentro** de `services`. |

---

## Consecuencias

**Positivas**

- El eje departamental de la matriz RBAC tiene correspondencia directa y verificable con el árbol de directorios: auditar "qué código toca `billing`" es una operación de sistema de archivos.
- `packages/repository` como capa transversal obligatoria hace que P1, PN-15 y el guardián de ADR-019 tengan **un único punto de instalación**.
- `domain` sin dependencias de infraestructura permite pruebas unitarias rápidas de las reglas de negocio (no solapamiento de puertas, cálculo de tarifas, transiciones de estado) sin levantar MonetDB.
- Extraer un módulo a servicio independiente en fase Scale es una operación mecánica, no una reescritura.

**Negativas y costes asumidos**

- Más ceremonia por módulo: cuatro directorios y un puerto declarado incluso para módulos pequeños (`people`, `passenger`). Se acepta a cambio de uniformidad verificable.
- La prohibición de importación cruzada entre módulos obliga a definir puertos explícitos para dependencias reales (M4 necesita ETA y puerta asignada de M1/M3). Es trabajo adicional que hace visible el acoplamiento en lugar de esconderlo.
- `import-linter` debe mantenerse actualizado con cada módulo nuevo; se incorpora a la DoD genérica.
