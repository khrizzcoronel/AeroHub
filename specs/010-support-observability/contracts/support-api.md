# Contrato: API de soporte (`aerohub_support`)

Montado en el Gateway con prefijo `/support`. Todas las rutas requieren
JWT válido (`AutenticacionJWTMiddleware`); ninguna requiere licencia de
módulo (research.md Decisión 7). Scopes nuevos: `support:leer`,
`support:escribir` (agregados a los emitidos por `aerohub_tenancy` al
autenticar, mismo mecanismo que `compliance:leer`/`compliance:escribir`
de S1.7).

## Tickets

- `POST /support/tickets` — crea un ticket (US1). Body: `categoria_id`,
  `severidad`, `asunto`, `cuerpo_inicial`. Responde `201` con el
  `ticket_id` (string) y el `sla_objetivo_min` calculado (FR-002).
  Requiere `support:escribir`. Tenant tomado de `contexto_tenant_id()`.
- `GET /support/tickets/{id}` — detalle de un ticket con su hilo de
  mensajes. Un usuario de tenant solo ve sus propios tickets (404 si es
  de otro tenant, PN-01); `role_support` ve cualquiera
  (`alcance_global`, research.md Decisión 5). Requiere `support:leer`.
- `GET /support/tickets` — lista tickets. Tenant: los propios.
  `role_support`: todos, con filtro opcional `?estado=` y
  `?severidad=`. Requiere `support:leer`.
- `POST /support/tickets/{id}/mensajes` — agrega un mensaje al hilo.
  Body: `cuerpo`, `es_interno` (solo `role_support` puede marcar
  `es_interno=true`; un usuario de tenant que lo intente recibe `403`).
  Si es el primer mensaje de `role_support` en el ticket, fija
  `primera_respuesta_en` (FR-003). Requiere `support:escribir`.
- `PATCH /support/tickets/{id}/estado` — transición de estado
  (`en_progreso`, `esperando_cliente`, `resuelto`, `cerrado`).
  Rechaza transiciones inválidas (data-model.md). Exclusivo
  `role_support`. Requiere `support:escribir`.

## Base de conocimientos

- `POST /support/kb/articulos` — publica un artículo nuevo o una nueva
  versión. Exclusivo `role_support`/`role_platform_admin`. Requiere
  `support:escribir`.
- `GET /support/kb/articulos?q=&etiqueta=` — busca artículos
  publicados por texto (`ILIKE` en `titulo`/`cuerpo`) y/o etiqueta.
  Público para cualquier usuario autenticado (no filtra por tenant —
  `articulo_kb` es global). Requiere `support:leer`.
- `GET /support/kb/articulos/{id}` — detalle de un artículo publicado.

## Changelog

- `POST /support/changelog` — publica una entrada de changelog con sus
  ítems. Exclusivo `role_platform_admin`. Requiere `support:escribir`.
- `GET /support/changelog` — lista changelog publicado, visible a
  cualquier tenant sin importar licencia de módulo (FR-016). Requiere
  `support:leer`.

## Observabilidad

- `GET /support/observabilidad/uptime?servicio=aodb|fids` — uptime del
  mes en curso y consumo de error budget, calculado a demanda contra
  Prometheus (research.md Decisión 1). Requiere `support:leer` o
  `compliance:leer` (mismo público que consulta post-mortems).
