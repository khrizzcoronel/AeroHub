# Runbook — Correo saliente (SMTP)

| Campo | Contenido |
|:---|:---|
| Sprint de origen | S1.10 (identidad y acceso, ADR-020) |
| Motivo | Invitaciones, verificación de correo y recuperación de contraseña dependen de un adaptador SMTP real; este runbook fija cómo se configura en desarrollo (`mailpit`) y qué cambia al migrar a Gmail/un proveedor real |
| Servicios relacionados | `mailpit` (desarrollo), `gateway` (adaptador SMTP inyectado en `services/gateway/main.py`) |

## Arranque en desarrollo

```bash
docker compose -f infra/docker-compose.yml up -d mailpit gateway
```

`mailpit` expone SMTP en `:1025` (sin TLS, sin credenciales) y una interfaz web en `:8025` para leer los correos que el gateway
envía durante desarrollo o pruebas de integración — no hace falta ninguna cuenta de correo real para probar invitaciones,
verificación o recuperación de contraseña de punta a punta.

## Variables de entorno

Todas se leen en `services/tenancy/aerohub_tenancy/infrastructure/correo_smtp.py::crear_adaptador_smtp_desde_entorno`, nunca
hardcodeadas:

| Variable | Desarrollo (`mailpit`) | Producción (ejemplo Gmail) |
|:---|:---|:---|
| `AEROHUB_SMTP_HOST` | `mailpit` | `smtp.gmail.com` |
| `AEROHUB_SMTP_PORT` | `1025` | `587` (STARTTLS) |
| `AEROHUB_SMTP_USUARIO` | (vacío) | la cuenta de Gmail emisora |
| `AEROHUB_SMTP_PASSWORD` | (vacío) | **contraseña de aplicación**, nunca la contraseña de la cuenta |
| `AEROHUB_SMTP_TLS` | `false` | `true` |
| `AEROHUB_SMTP_REMITENTE` | `no-responder@aerohub.test` | dirección real que debe figurar como origen |
| `AEROHUB_URL_BASE_APP` | `http://localhost:4200` | dominio real de `apps/web` en ese entorno |

**Ninguna de estas variables se commitea con un valor real** — `infra/docker-compose.yml` solo fija los valores de desarrollo
(sin secreto, apuntando a `mailpit`); los valores de producción se inyectan desde el entorno de despliegue, nunca desde el
repositorio.

## Generar la contraseña de aplicación de Gmail

Gmail exige verificación en dos pasos (2FA) habilitada en la cuenta antes de poder generar una contraseña de aplicación:

1. Activar 2FA en la cuenta de Google que va a enviar los correos (`myaccount.google.com/security`).
2. Generar una contraseña de aplicación (`myaccount.google.com/apppasswords`) con un nombre descriptivo (p. ej. "AeroHub SMTP").
3. Usar ese valor de 16 caracteres como `AEROHUB_SMTP_PASSWORD` — nunca la contraseña normal de la cuenta, que ni siquiera
   funcionaría con 2FA activo.

## Límites de envío conocidos

Gmail limita el envío SMTP normal a ~500 mensajes/día por cuenta (~2000 con Google Workspace) — suficiente para el volumen de
invitaciones/recuperaciones de un piloto, pero **no** es un proveedor transaccional dimensionado para volumen de producción real.
No hay cola de reintentos en este sprint (contracts/correo-puerto.md, "Fallo de envío"): si el SMTP rechaza o se satura, la
operación que originó el correo falla también (`502` en la API) y no queda una invitación fantasma sin correo enviado.

## Migrar a un proveedor transaccional (SendGrid, SES, Postmark)

Es un cambio de **adaptador**, no de arquitectura (ADR-020): `aerohub_tenancy/application/` depende únicamente del puerto
`EnviarCorreo` (`packages/contracts/aerohub_contracts/correo.py`), nunca de `smtplib` directamente. Escribir un nuevo adaptador
en `infrastructure/correo_<proveedor>.py` que implemente el mismo `Protocol`, e inyectarlo en `services/gateway/main.py` en vez
de `crear_adaptador_smtp_desde_entorno()` — ningún caso de uso de `application/` cambia.

## Verificación manual

Con el stack en Docker, abrir `http://localhost:8025` (interfaz web de mailpit) y disparar cualquier flujo que envíe correo
(`POST /usuarios/invitaciones`, `POST /auth/solicitar-verificacion`, `POST /auth/recuperar`) — el mensaje aparece de inmediato en
la bandeja de mailpit, con el enlace real que la plantilla generó (`AEROHUB_URL_BASE_APP` + token en claro).
