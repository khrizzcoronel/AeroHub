# Contrato -- Verificación de licencia (Gateway) y rotación de API Keys (`aerohub_tenancy`)

## Verificación de licencia (transversal, sin endpoint propio)

No es un endpoint nuevo -- es un control que `AutenticacionJWTMiddleware`
aplica a TODA petición cuyo primer segmento de ruta mapea a un módulo
licenciable (`/billing`, `/rampa`, `/puertas`, `/fids`, `/vuelos`,
`/passenger`).

**Comportamiento**:
- Licencia vigente (`activa_desde <= ahora < activa_hasta`, o
  `activa_hasta` nula) -> la petición continúa normalmente.
- Sin fila de licencia, o vencida -> `403` con
  `{"detail": "modulo sin licencia vigente"}`, y una fila nueva en
  `compliance.log_auditoria` (`operacion='DENY'`... ver Nota).

**Nota de `operacion`**: `log_auditoria.operacion` YA admite el valor
`'DENEGADO'` desde S1.2 (PN-06, agregado exactamente para el caso de una
API Key revocada/expirada) -- se reutiliza tal cual, sin ampliar el CHECK.
`tabla='licencia'`, `registro_id=tenant_id`, `valores_nuevos`
(`{"modulo": "BILL", "resultado": "sin_licencia_vigente"}`).

## `POST /api-keys/{id}/rotar` (`aerohub_tenancy`)

Rota una API Key existente: inserta una fila nueva (secreto nuevo) y
marca la anterior `estado='revocada'`, `rotada_en=now()`.
`role_platform_admin`/`role_tenant_admin`.

Response `201`:
```json
{"api_key_id": "...", "api_key_en_claro": "prefijo.secreto"}
```

El secreto en claro se muestra UNA sola vez, mismo patrón que
`POST /tenants/api-keys` (creación).
