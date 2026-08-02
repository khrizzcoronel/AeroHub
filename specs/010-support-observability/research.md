# Research: Soporte D6 y observabilidad (S1.8)

## Decisión 1 — Dónde vive el cálculo de uptime/error budget

**Decisión**: el uptime y el consumo de error budget de AODB/FIDS se
calculan a demanda a partir de las métricas Prometheus ya emitidas por
`services/gateway` (`/metrics`, activo desde S0.1/S1.2) — no se
introduce una tabla nueva que persista el estado de uptime.

**Razón**: la pila Prometheus/Loki/Grafana ya está desplegada en
`infra/docker-compose.yml` desde S0.1 y el Gateway ya expone `/metrics`
con el registro global de `prometheus_client` (patrón usado por
`aerohub_fids/metricas.py` en S1.3). Modelar uptime/error-budget como
filas persistidas en MonetDB duplicaría una fuente de verdad que
Prometheus ya mantiene con retención y agregación temporal — y ninguna
regla de negocio del proyecto necesita consultar el histórico de uptime
desde `aerohub_repository`. Es la aplicación de la misma idea que
motivó no crear una tabla para "estado de conexión WS" en S1.2: si un
sistema de observabilidad ya lo mide, no se reimplementa en el esquema
operacional.

**Alternativas consideradas**: (a) tabla `observability.uptime_periodo`
con un job que la puebla — rechazada por duplicar la fuente de verdad
sin necesidad de negocio que la consuma; (b) servicio de observabilidad
nuevo (Mimir/Tempo) para completar la pila "LGTM" literal — rechazada
por alcance: el sprint pide dashboards de uptime y alertas, no trazas
distribuidas (Tempo) ni métricas de largo plazo multi-tenant (Mimir);
Prometheus + Loki + Grafana ya cubren el requisito tal como está
redactado en el SRS.

## Decisión 2 — Mecanismo de bloqueo automático de despliegues

**Decisión**: el bloqueo es un paso de CI (`tools/verificar_error_budget.py`)
que consulta la API HTTP de Prometheus (`/api/v1/query`) por el
consumo de error budget del servicio a desplegar y termina con código
de salida distinto de cero si supera 80 %, salvo que se invoque con un
override explícito (`--override --motivo "..."`) — en cuyo caso dejar
un registro de auditoría es OBLIGATORIO antes de continuar, escrito con
`aerohub_repository.audit.registrar_auditoria(esquema="observabilidad",
tabla="bloqueo_despliegue", registro_id=<id sintético>,
operacion="DENEGADO"|"UPDATE", ...)` — mismo patrón de reutilización de
`compliance.log_auditoria` ya usado en S1.7 para la denegación de
licencia, sin crear tabla física para el evento.

**Razón**: el repositorio no tiene todavía un pipeline de *despliegue*
real (solo `ci.yml` de integración continua) — construir un CD completo
está fuera del alcance de este sprint y del plan de arquitectura (no
hay acción fuente que lo pida). La compuerta de pruebas de S1.8 exige
verificar el bloqueo "en escenario simulado", no en un despliegue real.
Un script de verificación reusable, invocable tanto desde CI como a
mano, satisface el requisito y queda listo para conectarse a un job de
CD el día que exista, sin necesitar rediseño.

**Alternativas consideradas**: (a) middleware en `aerohub_gateway` que
rechace requests si el error budget está agotado — rechazada, es un
control de *despliegue* (tiempo de build/release), no de *tráfico en
producción*; mezclar ambos viola la responsabilidad única del
middleware de licenciamiento (S1.7); (b) tabla de estado
"desplegable/bloqueado" por servicio consultada por un hipotético CD —
rechazada por la misma razón que la Decisión 1: el estado es derivado,
no debe persistirse como fuente de verdad aparte de Prometheus.

## Decisión 3 — Alertas Sev1–Sev3

**Decisión**: reglas de alerta declarativas de Prometheus
(`infra/prometheus/alertas.yml`, cargado por `prometheus.yml`), sin
componente de aplicación nuevo. Grafana ya está enlazado a Prometheus
como *data source* (`depends_on: prometheus` en `docker-compose.yml`)
para visualizar el estado de las alertas.

**Razón**: Prometheus Alertmanager es el mecanismo estándar para reglas
basadas en umbrales sobre series temporales ya recolectadas — no hay
lógica de negocio (no toca `tenant_id`, no es un caso de uso de
`aerohub_support`), por lo que no corresponde a ningún módulo de
`services/`. Los umbrales de severidad (Sev1/Sev2/Sev3) y el proceso de
post-mortem posterior ya se definieron en S1.7 (`compliance.post_mortem`)
— este sprint solo genera la señal que puede disparar esa incidencia,
no duplica su gestión.

## Decisión 4 — `ticket_mensaje` sin `tenant_id` propio

**Decisión**: `ticket_mensaje` se registra con `alcance='interno'` en
el guardián G1/G2 (no `'tenant'`), igual que `post_mortem_accion` en
S1.7 — el aislamiento se hereda transitivamente a través de
`ticket_id` → `ticket.tenant_id`, verificado en `application/` al
resolver el ticket padre antes de insertar el mensaje.

**Razón**: el SDD (§11.1–11.3) no incluye `tenant_id` en
`ticket_mensaje` — es exactamente el mismo patrón de tabla hija sin
columna de tenant propia ya resuelto en S1.7 (`post_mortem_accion`), no
un caso nuevo.

## Decisión 5 — Acceso cross-tenant de `role_support`

**Decisión**: las consultas de `role_support` sobre `ticket` usan
`alcance_global(motivo="atencion_de_soporte", rol="role_support")`
para leer/actualizar tickets de cualquier tenant, en vez de quedar
limitadas al tenant del JWT del especialista.

**Razón**: `role_support` es un rol de **plataforma** (`tenants.rol` id
6, alcance `'plataforma'` desde S0.2 — ver
`db/ddl/monetdb/02_tenants.sql:140`), no un rol de tenant. Es la misma
categoría que los procesos de aprovisionamiento o el monitor de señal
FIDS: un especialista de soporte necesariamente atiende tickets de
múltiples tenants. Cada uso de `alcance_global()` queda auditado con
motivo y rol explícitos (Principio I de la constitución), igual que
todos los usos previos desde S0.2.

**Alternativa considerada**: exigir que cada especialista tenga un JWT
por tenant y cambie de sesión para atender cada ticket — rechazada por
UX y porque no refleja cómo opera un equipo de soporte real (un mismo
turno atiende tickets de varios tenants sin re-autenticarse).

## Decisión 6 — Búsqueda de la base de conocimientos

**Decisión**: búsqueda por coincidencia de texto (`ILIKE` sobre
`titulo`/`cuerpo`) y por `etiqueta`, combinadas con `OR`. La columna
`embedding_ref` se persiste pero no se popula ni se consulta en este
sprint.

**Razón**: documentado como asunción de `spec.md` — la integración de
un almacén vectorial no tiene acción fuente en el plan de
implementación para S1.8 y RF-O14 es prioridad "C" (deseable) en el
SRS. `ILIKE` sobre dos columnas de texto con índice es suficiente para
el volumen esperado de artículos de una base de conocimientos interna.

## Decisión 7 — Licenciamiento no aplica a `aerohub_support`

**Decisión**: no se modifica `PREFIJO_A_CODIGO_MODULO`
(`aerohub_gateway/domain/licencia.py`, S1.7). Las rutas de
`aerohub_support` (`/support/...`) no se agregan al mapa de módulos
licenciables.

**Razón**: el licenciamiento (RF-O18, S1.7) aplica a los módulos de
negocio M1–M6 que un tenant contrata; D6 (Soporte) y M8 (Observability)
no son módulos licenciables según el propio catálogo `catalogo.modulo`
sembrado en S0.1 — son capacidades de plataforma disponibles para todo
tenant activo, igual que ya ocurre con `tenants`/`compliance`. Como
`resolver_modulo_de_ruta` devuelve `None` para cualquier prefijo no
mapeado, el middleware de licencia ya deja pasar estas rutas sin
cambio de código — se documenta la decisión para que quede explícito
que es intencional, no un olvido.
