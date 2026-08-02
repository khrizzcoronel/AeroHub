# Contrato: puerto de envío de correo

Declarado en `packages/contracts/aerohub_contracts/correo.py` — mismo
lugar y misma razón que `requiere_scope` (S1.2): lo necesita un módulo de
negocio y no puede vivir dentro de otro sin romper la independencia de
módulos.

## El puerto

Una operación: enviar un mensaje ya compuesto (destinatario, asunto,
cuerpo en texto y cuerpo en HTML). El puerto **no** conoce plantillas,
SMTP, credenciales ni reintentos — solo el contrato.

`application/` de `aerohub_tenancy` depende del puerto, nunca del
adaptador. El adaptador concreto se inyecta desde el borde
(`services/gateway/main.py`), igual que cualquier otra dependencia de
infraestructura.

## El adaptador SMTP

`aerohub_tenancy/infrastructure/correo_smtp.py`, con `smtplib` +
`email.message` de la biblioteca estándar (research.md Decisión 6).
Configuración por entorno, nunca en el repositorio:

| Variable | Para qué |
|:---|:---|
| `AEROHUB_SMTP_HOST` | `smtp.gmail.com` en real; `mailpit` en desarrollo |
| `AEROHUB_SMTP_PORT` | `587` (STARTTLS) en real; `1025` en desarrollo |
| `AEROHUB_SMTP_USUARIO` | cuenta emisora |
| `AEROHUB_SMTP_PASSWORD` | **contraseña de aplicación** de Gmail — secreto, nunca commiteada |
| `AEROHUB_SMTP_TLS` | `true` en real; `false` contra el servidor de prueba |
| `AEROHUB_SMTP_REMITENTE` | dirección que figura como origen |
| `AEROHUB_URL_BASE_APP` | base para construir los enlaces del correo |

## Las cuatro plantillas

| Plantilla | Cuándo | Contiene |
|:---|:---|:---|
| Invitación | un admin invita a alguien a su tenant | enlace de aceptación, quién invita, organización, vencimiento |
| Verificación de correo | la persona pide verificar su dirección | enlace de verificación, vencimiento |
| Recuperación de contraseña | la persona olvidó su clave | enlace de restablecimiento, vencimiento, aviso de "si no fuiste tú, ignora este mensaje" |
| Aviso de acceso | inicio de sesión desde un origen no visto antes | fecha, hora y origen aproximado; **sin** enlace de acción |

Ninguna plantilla incluye la contraseña ni el token fuera del enlace.

## Fallo de envío

Si el envío falla, la operación que lo originó **falla también** y lo
reporta (`502` en la API). No se registra una invitación cuyo correo nunca
saldrá (spec.md, Edge Cases). No hay cola de reintentos en este alcance —
introducir una exigiría un mecanismo de trabajos en segundo plano que el
proyecto no tiene y que no corresponde a este sprint.

## Verificación

Las pruebas envían contra `mailpit` (SMTP real en Docker) y consultan su
API para comprobar que el mensaje llegó, a quién, y qué enlace contiene —
no se usa un *mock* de `smtplib` (research.md Decisión 7, Principio III de
la constitución).
