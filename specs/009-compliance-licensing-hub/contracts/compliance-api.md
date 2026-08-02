# Contrato de API -- `aerohub_compliance` (`/compliance`)

Convenciones heredadas de `services/billing/aerohub_billing/api/router.py`.

## `POST /compliance/incidentes`

Registra un `incidente_seguridad`. `role_sre`/`role_platform_admin`.

Request: `{"tipo_incidente_id": "...", "descripcion": "...", "severidad": "alta", "detectado_en": "2026-08-02T10:00:00Z"}`

Response `201`: `{"incidente_id": "..."}`

## `GET /compliance/incidentes`

Lista incidentes del tenant. `role_sre`/`role_regulatory_auditor`.

## `POST /compliance/post-mortems`

Crea un post-mortem en `estado='en_progreso'`. Exclusivo `role_sre`
(FR-006).

Request: `{"incidente_ref": "INC-2026-014", "severidad": "alta", "iniciado_en": "2026-08-02T10:00:00Z"}`

Response `201`: `{"post_mortem_id": "..."}`

## `PATCH /compliance/post-mortems/{id}`

Edita `causa_raiz`. Exclusivo `role_sre`; cada edición genera una fila en
`compliance.log_auditoria` (FR-007).

Request: `{"causa_raiz": "..."}`

Response `200`

## `POST /compliance/post-mortems/{id}/acciones`

Agrega una `post_mortem_accion` en `estado='pendiente'`.

Request: `{"descripcion": "...", "responsable_usuario_id": "...", "vence_en": "...", "ticket_ref": "..."}`

Response `201`: `{"accion_id": "..."}`

## `POST /compliance/post-mortems/{id}/acciones/{accion_id}/completar`

Transiciona una acción a `estado='completada'`, `completada_en=now()`.

## `POST /compliance/post-mortems/{id}/publicar`

Transiciona a `estado='publicado'`, `publicado_en=now()`. Rechaza (`409`)
si alguna `post_mortem_accion` no está `completada` (FR-005).

## `GET /compliance/post-mortems/{id}`

Detalle con acciones.

## `POST /compliance/reportes-dgac`

Registra un `reporte_dgac` (hash SHA-256 del artefacto ya generado fuera
de este sprint -- la generación del artefacto no está en alcance, solo su
registro append-only).

## `POST /compliance/accesos-auditor`

Otorga una ventana de acceso a un `role_regulatory_auditor`.
`role_platform_admin`.

## `POST /compliance/evidencia-soc2`

Registra evidencia de un control SOC 2, opcionalmente referenciando una
fila de `log_auditoria`.

## Segregación de funciones y append-only (verificación negativa)

Ningún endpoint de este contrato expone `PUT`/`PATCH`/`DELETE` sobre
`incidente_seguridad`, `reporte_dgac`, `acceso_auditor` ni
`evidencia_soc2` -- solo `POST` de alta. `PATCH` existe únicamente para
`post_mortem`, exclusivo `role_sre`.
