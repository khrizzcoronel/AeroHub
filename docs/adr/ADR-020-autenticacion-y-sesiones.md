# ADR-020 — Autenticación por credenciales propias y sesiones revocables

| Campo | Contenido |
|:---|:---|
| **Estado** | Aceptado |
| **Fecha** | 2026-08-02 |
| **Decide sobre** | Mecanismo de autenticación humana (login real), vigencia y revocación de sesión, ciclo de vida de contraseñas y tokens de un solo uso |
| **Deriva de** | AEROHUB-SRS-001 v2.0 §2.2 (roles), §8.2 (RNF-S03..S06 editoriales) · ADR-014 (P2, control compensatorio de tenant vía JWT) |
| **Requisitos relacionados** | RF-IA01..RF-IA08, RNF-S06 |

---

## Contexto

Desde S1.1 hasta S1.9, ningún actor humano tenía credenciales propias: cada sesión de prueba/demo pegaba un JWT minteado a mano
(`aerohub_gateway.infrastructure.codificar_jwt`) en un textarea (`apps/web/src/app/tenants/tenant-creation`). Esto era deliberado
— el plan de implementación no incluía login real hasta este sprint — pero dejaba dos huecos reales: un tenant nuevo no tenía forma
de que su segundo usuario existiera (sin invitaciones), y ningún JWT emitido podía revocarse antes de su `exp` natural.

Este ADR decide el mecanismo completo: login con correo/contraseña, sesión revocable, invitaciones por correo, verificación de
correo, y recuperación de contraseña — el sprint que cierra "todavía no hay login real" como deuda documentada en `CLAUDE.md`.

## Decisión

### JWT + sesión revocable (no solo JWT con `exp` corto)

Un JWT firmado (HS256, mismo secreto y algoritmo que el JWT de S1.1/S1.2 — `aerohub_contracts.jwt_sesion` decodifica interoperablemente
con `aerohub_gateway.infrastructure.jwt_`) lleva un claim adicional `sesion_id`, que referencia una fila en `tenants.sesion`
(`revocada_en`, `expira_en`). El middleware del Gateway verifica en **cada petición autenticada** que esa sesión siga vigente
(specs/012-identidad-y-acceso/research.md Decisión 5) — sin esto, "cerrar sesión" o "restablecer contraseña" solo tendrían efecto
en la base, nunca en un JWT ya emitido.

**Costo asumido, declarado explícitamente**: una consulta adicional a la base por petición autenticada (join `sesion` + `usuario`,
una sola consulta, no dos). Consistente con lo que el sistema ya hace desde S1.7 (`verificar_licencia`). Optimización (cache corto,
consulta combinada) queda documentada como posible pero no implementada — no se optimiza antes de medir.

### Argon2id reutilizado para contraseñas y tokens de un solo uso

`aerohub_kernel.hash_credencial`/`verificar_credencial` (ya en uso desde S0.2 para `tenants.usuario.hash_credencial` y
`tenants.api_key.hash_secreto`) se reutiliza para hashear `tenants.token_acceso.hash_token` — ningún token de invitación,
verificación o recuperación se almacena en claro (mismo modelo de amenaza que una API Key: un volcado o snapshot de continuidad
(ADR-018) no debe convertirse en una toma de control de cuentas).

### Política mínima de contraseña

10 caracteres, al menos una letra y un dígito (`aerohub_tenancy.domain.password.validar_password`) — sin reglas de complejidad
adicionales (mayúsculas obligatorias, símbolos) que la evidencia de la industria (NIST 800-63B) ya desaconseja por incentivar
patrones predecibles. Se puede endurecer más adelante sin romper compatibilidad — el motivo del rechazo siempre se comunica.

### Bloqueo por fuerza bruta: 5 intentos fallidos en 15 minutos, bloqueo de 15 minutos

Ventanas deliberadamente iguales y cortas — un intento legítimo que fallo por error tipográfico no debería esperar más de 15
minutos, y 5 intentos es suficientemente bajo para frenar un ataque de diccionario trivial sin generar soporte innecesario.

### Vencimientos de tokens de un solo uso

| Tipo | Vencimiento | Razón |
|:---|:---|:---|
| Invitación | 7 días | Tiempo razonable para que alguien revise su correo sin presión, acorde a onboarding empresarial típico |
| Verificación de correo | 24 horas | Acción de baja fricción, no hay urgencia de seguridad en acortarla |
| Recuperación de contraseña | 1 hora | Ventana de exposición mínima para el flujo más sensible (quien lo recibe podría no ser el dueño de la cuenta) |

### Por qué NO se adopta OAuth/SSO/MFA todavía

- **OAuth/SSO (Google Workspace, Azure AD, SAML)**: ningún tenant piloto lo exige todavía; agregar un IdP externo antes de tener
  un cliente real que lo pida es trabajo especulativo (constitución: "no diseñar para requisitos hipotéticos"). El puerto
  `EnviarCorreo` y el modelo de `usuario`/`sesion` no bloquean agregarlo después — un proveedor SSO se sumaría como otro `tipo` de
  autenticación, no reemplazaría el existente.
- **MFA (TOTP, WebAuthn)**: mismo criterio — sin caso de uso concreto que lo exija en el alcance de S1.10, y añade una superficie
  de recuperación de cuenta (códigos de respaldo) que este sprint no tiene tiempo de diseñar con el mismo cuidado que el resto del
  flujo. Se deja como extensión futura explícita del modelo `tenants.usuario`, no descartada, solo no construida todavía.

### Adaptador de correo: SMTP con la biblioteca estándar, sin proveedor transaccional

`smtplib` + `email.message` (Python estándar) contra Gmail vía contraseña de aplicación en producción, `mailpit` en desarrollo —
ver `docs/runbooks/correo-smtp.md`. Migrar a un proveedor transaccional (SendGrid, SES, Postmark) es un cambio de adaptador, no de
arquitectura: `aerohub_tenancy/application/` depende únicamente del puerto `EnviarCorreo`
(`packages/contracts/aerohub_contracts/correo.py`), nunca de `smtplib` directamente.

## Consecuencias

- Toda ruta autenticada paga el costo de una consulta extra de verificación de sesión — aceptado, medido en la compuerta de
  pruebas de este sprint (RNF-P01 re-medido).
- `role_platform_admin` es el único rol con privilegio de motor sobre `tenants.sesion`/`tenants.token_acceso`
  (`99_grants_identidad.sql`) — todo flujo de identidad (login, cambio de contraseña, invitación, verificación, recuperación)
  corre bajo `alcance_global(rol="role_platform_admin")`, auditado con un `motivo` distinto por flujo.
- Sin OAuth/SSO/MFA, la superficie de ataque del login sigue siendo "correo + contraseña" — mitigada por el bloqueo por fuerza
  bruta y por Argon2id, no por un segundo factor. Riesgo aceptado explícitamente, no ignorado.
