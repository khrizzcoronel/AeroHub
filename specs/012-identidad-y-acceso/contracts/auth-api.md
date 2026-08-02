# Contrato: API de identidad y acceso

Montado en el Gateway. Las rutas marcadas **públicas** se agregan a
`RUTAS_EXENTAS` del middleware (hoy solo `/metrics` está exenta) — no
exigen credencial previa, por definición (FR-026). El resto exige JWT
válido **y sesión vigente** (research.md Decisión 5).

## Reglas transversales

- Ningún error de autenticación distingue correo inexistente de
  contraseña incorrecta: mismo código y mismo mensaje (FR-003).
- Ningún cuerpo de respuesta ni registro de aplicación incluye contraseñas
  ni tokens en claro (FR-025).
- Todos los ids viajan como string en JSON (Snowflake de 64 bits, regla
  del proyecto desde S1.1).
- Todo evento de identidad se audita en `compliance.log_auditoria`
  (FR-024).

## Sesión

### `POST /auth/login` — pública

Body: `email`, `password`.

- `200`: `token` (JWT), `expira_en`, y el perfil de acceso completo
  (mismo cuerpo que `GET /auth/yo`, para evitar una segunda llamada
  inmediata), más `debe_cambiar_password`.
- `401`: credencial inválida, cuenta inactiva, cuenta bloqueada o sin rol
  vigente — **el mismo cuerpo en los cuatro casos**. El motivo real queda
  en `tenants.intento_acceso.resultado`, no en la respuesta.
- `429`: límite de frecuencia excedido (reutiliza el limitador de S1.2).

Efectos: registra el intento en `tenants.intento_acceso`; si es exitoso,
crea `tenants.sesion`, actualiza `tenants.usuario.ultimo_acceso_en` y
reinicia el conteo de fallos; si falla, evalúa si corresponde fijar
`bloqueado_hasta`.

### `POST /auth/logout` — autenticada

Revoca la sesión del JWT presentado (`motivo_revocacion='cierre_sesion'`).
`200` idempotente: cerrar una sesión ya cerrada no es un error.

### `GET /auth/yo` — autenticada

Perfil de acceso de quien llama. Ver
[perfil-acceso.md](./perfil-acceso.md) para el cuerpo exacto.

## Contraseña

### `POST /auth/cambiar-password` — autenticada

Body: `password_actual`, `password_nueva`.

- `200`: cambia la credencial, pone `debe_cambiar_password=false`, revoca
  **las demás** sesiones del usuario (la actual sigue viva).
- `422`: la contraseña nueva no cumple la política mínima — el detalle
  indica qué requisito falta (FR-013).
- `401`: `password_actual` incorrecta.

**Único endpoint permitido** mientras `debe_cambiar_password=true`: el
resto de rutas autenticadas responde `403` indicando que debe cambiarla
primero (FR-012).

### `POST /auth/recuperar` — pública

Body: `email`. **Siempre `202`**, exista o no una cuenta con ese correo
(FR-021) — no se puede usar para descubrir qué correos están registrados.
Si existe, emite un token de tipo `recuperacion` e invalida los anteriores
del mismo tipo, y envía el correo.

### `POST /auth/restablecer` — pública

Body: `token`, `password_nueva`.

- `200`: fija la contraseña nueva, consume el token y **revoca todas las
  sesiones** del usuario (`motivo_revocacion='restablecer_password'`,
  FR-022).
- `410`: token inexistente, ya consumido o vencido.
- `422`: la contraseña nueva no cumple la política.

## Correo

### `POST /auth/verificar-correo` — pública

Body: `token`. `200` marca `email_verificado_en`; `410` si el token es
inexistente, ya consumido o vencido.

### `POST /auth/solicitar-verificacion` — autenticada

Emite un token de tipo `verificacion` y envía el correo. `202`.

## Usuarios

### `POST /usuarios/invitaciones` — autenticada, exclusivo `role_tenant_admin`

Body: `email`, `rol_codigo`.

- `201`: crea la invitación y su token, envía el correo. Devuelve el
  `invitacion_id` y su `expira_en`. **Nunca** devuelve el token.
- `403`: quien llama no administra el tenant.
- `409`: ese correo ya corresponde a una cuenta existente (FR-016) — es
  el único caso donde sí se confirma la existencia de un correo, y es
  deliberado: quien llama ya está autenticado como administrador y
  necesita saberlo para actuar.
- `502`: el correo no pudo enviarse; la invitación **no** queda registrada
  (spec.md, Edge Cases: no dejar una invitación cuyo mensaje nunca
  llegará).

### `POST /usuarios/aceptar-invitacion` — pública

Body: `token`, `nombre`, `password`.

- `201`: crea el usuario en el tenant de la invitación con el rol
  indicado, lo marca con correo verificado (llegó por ese correo) y
  `debe_cambiar_password=false` (acaba de elegir la suya), consume el
  token y marca la invitación como aceptada — todo en una transacción.
- `410`: token inexistente, ya consumido o vencido (invitación caducada).
- `422`: la contraseña no cumple la política.
