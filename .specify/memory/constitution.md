<!--
Sync Impact Report
- Version change: (none) → 1.0.0 (ratificación inicial)
- Principios agregados:
  I. Aislamiento Multi-Tenant Fail-Closed
  II. Arquitectura Modular por Capas e Independencia de Módulos
  III. Verificación Empírica Obligatoria
  IV. Calidad Continua en Verde
  V. Aprobación Explícita Antes de Acciones Irreversibles
- Secciones agregadas: Requisitos Tecnológicos y de Infraestructura,
  Flujo de Trabajo de Desarrollo, Governance
- Secciones removidas: ninguna (primera ratificación)
- TODOs pendientes: ninguno
- Nota: esta constitución no inventa reglas nuevas -- formaliza por
  escrito principios ya vigentes desde el Sprint S0.1 (ADR-014, ADR-017,
  ADR-019) y practicas de trabajo ya seguidas en cada sprint hasta S1.5,
  documentadas previamente solo en CLAUDE.md.
-->

# AeroHub Constitution

## Core Principles

### I. Aislamiento Multi-Tenant Fail-Closed
Todo dato operacional pertenece a un tenant. El `tenant_id` NUNCA se acepta
desde el cuerpo de una petición, un parámetro de URL, ni ningún dato que el
cliente pueda inventar -- se lee exclusivamente de `contexto_tenant_id()`,
poblado por el middleware del Gateway a partir del JWT ya validado
(ADR-014, control compensatorio 2). Toda consulta sobre una tabla de
alcance `'tenant'` DEBE llevar un filtro explícito de `tenant_id`; el
guardián G1/G2 (`aerohub_repository.guard`) aborta en tiempo de ejecución
cualquier sentencia que no lo cumpla, incluso si el código de aplicación
lo omitió por error -- fail-closed, no fail-open (ADR-019). La única
excepción es `alcance_global()`, reservada a procesos de plataforma sin
tenant propio (aprovisionamiento, monitores de fondo, extracción técnica),
siempre invocada con `motivo` y `rol` explícitos y auditada en
`compliance.log_auditoria` -- una lista finita y revisable de excepciones
nominales, nunca una convención implícita. Un recurso de otro tenant (o de
otro usuario cuando aplica mínimo privilegio dentro del mismo tenant)
responde 404, NUNCA 403: revelar que el recurso ajeno existe ya es una
fuga de información (PN-01).

### II. Arquitectura Modular por Capas e Independencia de Módulos
Cada módulo de negocio vive en `services/<modulo>/aerohub_<modulo>/` con
cuatro subpaquetes de responsabilidad estricta: `domain/` (entidades e
invariantes puros, sin SQLAlchemy ni FastAPI, testeable sin levantar la
base), `application/` (casos de uso, límites transaccionales, orquesta
`domain/` + `infrastructure/`), `infrastructure/` (el ÚNICO subpaquete
autorizado a importar `aerohub_repository` -- toda sentencia SQL vive
aquí), y `api/` (routers FastAPI y DTOs Pydantic, traduce HTTP ↔
`application/` sin contener ninguna regla de negocio) (ADR-017 §5.4).
Ningún módulo importa `domain/` ni `application/` de otro módulo de
negocio -- la comunicación entre módulos, cuando existe, pasa por
`packages/contracts/`, nunca por import directo. Si un módulo necesita
leer una tabla "propiedad" de otro módulo, REDECLARA su propio objeto
`Table()` en su propio `infrastructure/tablas.py` y re-registra su alcance
G1 de forma idempotente, en vez de importar la definición ajena. Esta
independencia se verifica en cada build con `import-linter`
(`.importlinter`), no solo se documenta: una violación rompe el pipeline.

### III. Verificación Empírica Obligatoria
Ninguna tarea se considera terminada por tener tests unitarios en verde o
por "parecer correcta" en la lectura del código. Todo caso de uso nuevo o
modificado se ejercita contra una instancia real de MonetDB (vía Docker)
con datos reales antes de reportarse como completo -- incluyendo los
casos límite documentados como hallazgo empírico (p. ej. comportamiento de
concurrencia optimista, límites de sintaxis del motor, codificación de
`mclient`). Cuando el hallazgo revela una limitación real del motor o del
entorno (no solo del código propio), se documenta en
`docs/runbooks/monetdb.md` o en `CLAUDE.md` para no tener que
redescubrirla en el siguiente sprint.

### IV. Calidad Continua en Verde
`ruff`, `mypy`, `bandit`, `import-linter` y la suite completa de `pytest`
DEBEN pasar sin errores antes de reportar cualquier tarea o sprint como
completo. Un hallazgo de `bandit`, aunque sea de severidad baja, se
corrige en el código (nunca se silencia con un comentario de supresión
sin justificación explícita registrada). La regresión completa de
`pytest` se corre al cerrar cada sprint, no solo los tests nuevos del
sprint en curso.

### V. Aprobación Explícita Antes de Acciones Irreversibles
El diff (o un resumen fiel de los cambios) se presenta al usuario ANTES de
cualquier `git commit`. Nunca se commitea trabajo, por completo y
verificado que esté, sin que el usuario lo pida explícitamente en esa
misma conversación -- una aprobación anterior no se extiende a cambios
posteriores. La misma cautela aplica a cualquier otra acción de alto
impacto o difícil de revertir (force-push, `git reset --hard`, borrado de
datos, cambios de configuración compartida): se transparenta la acción y
se espera confirmación antes de ejecutarla.

## Requisitos Tecnológicos y de Infraestructura

Backend en Python 3.12 con FastAPI y SQLAlchemy Core (nunca el ORM) contra
MonetDB como motor operacional (ADR-013); ClickHouse para la capa
analítica dual (ADR-012). Frontends en Angular standalone components con
signals, sin framework de estado adicional. IDs de negocio son Snowflake
de 64 bits (`aerohub_kernel.generar_id`) y SIEMPRE viajan como string en
JSON (request y response) -- un id como número JSON pierde precisión en
el navegador por encima de `Number.MAX_SAFE_INTEGER` (hallazgo empírico
de S1.1, no una preferencia estética).

Todo servicio que se use para desarrollo o verificación corre en Docker
(`infra/docker-compose.yml`): MonetDB primario y standby, ClickHouse,
MinIO, Airflow, Prometheus, Loki, Grafana, y desde S1.5 también el
gateway compuesto (`services/gateway`) y los frontends
(`apps/web`, `apps/fids-player`). Ningún servicio se ejecuta suelto en el
host (`uv run uvicorn` / `npx nx serve`) como método de verificación
soportado -- el binario `uv` ni siquiera está garantizado en el PATH del
host de desarrollo de este proyecto.

## Flujo de Trabajo de Desarrollo

El desarrollo avanza sprint por sprint según `docs/PLAN_IMPLEMENTACION_v2.0.md`
§8, en el orden ahí definido. Cada sprint se implementa de verdad (código
funcionando, no solo documentado), se verifica empíricamente (Principio
III), se le agregan las pruebas negativas (PN-*) y de requisito no
funcional (RNF-*) que su compuerta de pruebas exige, y solo entonces se
presenta para commit (Principio V). El estado de avance (qué sprint está
hecho, con qué commit) se mantiene en `CLAUDE.md`, no se re-deriva
explorando el repo en cada sesión nueva. Toda comunicación con el usuario
es en español.

## Governance

Esta constitución tiene precedencia sobre cualquier práctica ad-hoc o
atajo conveniente en el momento; en caso de conflicto entre una
instrucción puntual y un principio aquí ratificado, se señala la tensión
al usuario en vez de resolverla en silencio a favor de la conveniencia.
Las enmiendas requieren: (1) razón documentada del cambio, (2) impacto en
principios existentes evaluado explícitamente, (3) actualización de
`CLAUDE.md` si el cambio afecta el resumen operativo ahí mantenido. El
versionado sigue semver: MAJOR para remoción o redefinición incompatible
de un principio; MINOR para agregar un principio o ampliar materialmente
una guía existente; PATCH para aclaraciones y correcciones de redacción
sin cambio de sustancia. `CLAUDE.md` es la guía operativa de uso diario
derivada de esta constitución; ante una discrepancia entre ambos, esta
constitución prevalece y `CLAUDE.md` se corrige para alinearse.

**Version**: 1.0.0 | **Ratified**: 2026-08-01 | **Last Amended**: 2026-08-01
