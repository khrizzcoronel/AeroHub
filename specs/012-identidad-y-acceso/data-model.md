# Data Model: Identidad y acceso (S1.10)

Amplía el esquema `tenants` (SDD-DATA-001 §6). Alcances G1 según
research.md Decisión 9: `sesion`/`token_acceso`/`intento_acceso` son
`'interno'` (se consultan antes de conocer al usuario, y un usuario de
plataforma tiene `tenant_id` NULL); `invitacion` es `'tenant'`.

## Cambios sobre `tenants.usuario` (existente)

| Columna | Tipo | Nulo | Nota |
|:---|:---|:---|:---|
| `email_verificado_en` | TIMESTAMPTZ | SÍ | NULL = correo sin verificar |
| `debe_cambiar_password` | BOOLEAN | NO | DEFAULT TRUE; `aprovisionar_tenant` y la aceptación de invitación lo fijan según el caso |
| `bloqueado_hasta` | TIMESTAMPTZ | SÍ | NULL = sin bloqueo; futuro = bloqueado por intentos fallidos |

**Restricción migrada** (research.md Decisión 2):
`uq_usuario_tenant_email UNIQUE (tenant_id, email)` →
`uq_usuario_email UNIQUE (email)`.

`ultimo_acceso_en` y `mfa_habilitado` **ya existen** en la tabla desde
S0.2 y hasta ahora no se usaban: este sprint empieza a escribir
`ultimo_acceso_en`; `mfa_habilitado` sigue sin uso (MFA fuera de alcance).

## `tenants.sesion`

Alcance G1 `'interno'`. Una fila por inicio de sesión; permite revocar
antes del vencimiento natural del JWT (FR-022, FR-023).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK — viaja en el JWT como identificador de sesión |
| `usuario_id` | BIGINT | NO | FK → `tenants.usuario.id` |
| `emitida_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `expira_en` | TIMESTAMPTZ | NO | coincide con el `exp` del JWT emitido |
| `revocada_en` | TIMESTAMPTZ | SÍ | NULL = vigente |
| `motivo_revocacion` | VARCHAR(30) | SÍ | CHK IN ('cierre_sesion','restablecer_password','revocacion_admin') |
| `ip_origen` | VARCHAR(45) | SÍ | |

**Vigencia**: `revocada_en IS NULL AND expira_en > ahora`. El middleware
la verifica en cada petición autenticada (research.md Decisión 5).

## `tenants.token_acceso`

Alcance G1 `'interno'`. Enlaces de un solo uso enviados por correo. El
token **nunca** se guarda en claro (research.md Decisión 8).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `usuario_id` | BIGINT | SÍ | FK → `tenants.usuario.id`. NULL para invitación: el usuario aún no existe |
| `tipo` | VARCHAR(20) | NO | CHK IN ('verificacion','invitacion','recuperacion') |
| `hash_token` | VARCHAR(255) | NO | Argon2id, mismo mecanismo que `hash_credencial` |
| `emitido_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `expira_en` | TIMESTAMPTZ | NO | |
| `consumido_en` | TIMESTAMPTZ | SÍ | NULL = sin usar |

**Canjeable**: `consumido_en IS NULL AND expira_en > ahora`. Emitir un
token nuevo del mismo `tipo` para el mismo destinatario invalida los
anteriores (spec.md, Edge Cases: solo el más reciente sirve).

## `tenants.invitacion`

Alcance G1 `'tenant'`. Propuesta de incorporación de una persona a un
tenant con un rol determinado.

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `tenant_id` | BIGINT | NO | FK → `tenants.tenant.id` |
| `email` | VARCHAR(254) | NO | destinatario |
| `rol_id` | BIGINT | NO | FK → `tenants.rol.id` — rol que tendrá al aceptar |
| `invitado_por_usuario_id` | BIGINT | NO | FK → `tenants.usuario.id` |
| `token_acceso_id` | BIGINT | NO | FK → `tenants.token_acceso.id` |
| `estado` | VARCHAR(20) | NO | CHK IN ('pendiente','aceptada','caducada','revocada') |
| `creada_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `aceptada_en` | TIMESTAMPTZ | SÍ | |

**Transición de estado**: `pendiente` → (`aceptada` \| `caducada` \|
`revocada`), sin retorno. Al aceptar se crea el `tenants.usuario` y su
`tenants.usuario_rol` en la MISMA transacción que marca la invitación
como aceptada y consume el token (P8).

## `tenants.intento_acceso`

Alcance G1 `'interno'`. Append-only. Base del bloqueo por intentos
fallidos (FR-004) y evidencia de auditoría de accesos (RNF-S04).

| Columna | Tipo | Nulo | Restricción |
|:---|:---|:---|:---|
| `id` | BIGINT | NO | PK |
| `email_intentado` | VARCHAR(254) | NO | se registra aunque no exista ninguna cuenta con ese correo |
| `usuario_id` | BIGINT | SÍ | FK → `tenants.usuario.id`. NULL si el correo no corresponde a ninguna cuenta |
| `resultado` | VARCHAR(20) | NO | CHK IN ('exitoso','credencial_invalida','cuenta_bloqueada','cuenta_inactiva','sin_rol_vigente') |
| `ocurrido_en` | TIMESTAMPTZ | NO | DEFAULT now() |
| `ip_origen` | VARCHAR(45) | SÍ | |

**Nota de diseño**: `resultado` distingue el motivo **en el registro
interno**, pero la respuesta HTTP al cliente es idéntica en todos los
casos de fallo (FR-003) — mismo criterio que PN-06 ya aplica a las API
Keys desde S1.2: se audita el detalle, no se le revela al atacante.

**Regla de bloqueo**: N intentos con `resultado != 'exitoso'`
consecutivos para el mismo `usuario_id` dentro de una ventana → se fija
`tenants.usuario.bloqueado_hasta`. Un intento exitoso reinicia el conteo.

## Correspondencia rol → módulos (sin tabla)

Vive en `packages/contracts/aerohub_contracts/roles_modulos.py` como dato
versionado en código, no en base de datos (research.md Decisión 4).
Estructura: por cada uno de los 16 roles de `tenants.rol`, el conjunto de
códigos de módulo (`M1`…`M9`, de `catalogo.modulo`) y el conjunto de
scopes (`vuelos:leer`, `billing:escribir`, …) que le corresponden.

Los **módulos visibles** de una persona se calculan como:

```
modulos_del_rol(rol)  ∩  modulos_con_licencia_vigente(tenant)
```

reutilizando `existe_licencia_vigente()` de S1.7 sin modificarla. Un
usuario de plataforma (`tenant_id` NULL) no pasa por el filtro de
licencia: no pertenece a ningún tenant.
