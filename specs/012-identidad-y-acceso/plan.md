# Implementation Plan: Identidad y acceso

**Branch**: `main` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/012-identidad-y-acceso/spec.md`

## Summary

Cierra el hueco de autenticación que el proyecto arrastra desde S1.1:
emite JWT contra credenciales reales (hoy `codificar_jwt()` solo se invoca
desde tests y el frontend pide pegar el token a mano), resuelve el rol
vigente desde `tenants.usuario_rol`, y expone `GET /auth/yo` con los
módulos visibles ya resueltos como intersección de rol × licencia
(research.md Decisión 4). Habilita que un tenant tenga más de un usuario
—hoy imposible, no existe endpoint alguno para crear el segundo— mediante
invitaciones por correo, y cierra el ciclo de vida de la credencial
(cambio obligatorio de la temporal, verificación de correo, recuperación,
cierre de sesión revocable). Todo el trabajo se hace **ampliando
`services/tenancy`**, sin módulo nuevo (research.md Decisión 1).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Angular 22
(frontend — este sprint SÍ tiene vistas nuevas, a diferencia de S1.8/S1.9)

**Primary Dependencies**: FastAPI, SQLAlchemy Core, `pyjwt` (ya presente
desde S1.1), `argon2-cffi` vía `aerohub_kernel.credenciales` (ya presente
desde S0.2), `smtplib`/`email` de la biblioteca estándar para el adaptador
SMTP (sin dependencia externa nueva de correo, research.md Decisión 6)

**Storage**: MonetDB — 4 tablas nuevas en el esquema `tenants`
(`sesion`, `token_acceso`, `invitacion`, `intento_acceso`), 3 columnas
nuevas en `tenants.usuario` (`email_verificado_en`,
`debe_cambiar_password`, `bloqueado_hasta`) y una **migración de
restricción**: `uq_usuario_tenant_email UNIQUE(tenant_id, email)` →
`uq_usuario_email UNIQUE(email)` global (research.md Decisión 2, con
verificación empírica del soporte de `ALTER TABLE` en MonetDB)

**Testing**: `pytest` unit (política de contraseña, resolución de rol
vigente, cálculo de módulos visibles, vigencia de token) + integration
(ciclo completo de login contra MonetDB real, bloqueo por intentos,
invitación end-to-end con servidor SMTP de prueba en Docker, expiración y
un-solo-uso de tokens) + negative (PN-01 tras login real, y una PN nueva
sobre no distinguir correo inexistente de contraseña incorrecta) — ver
[quickstart.md](./quickstart.md)

**Target Platform**: Docker Compose. Servicio nuevo `mailpit` (servidor
SMTP de prueba con interfaz web) para verificar el envío de correo en
desarrollo sin depender de Gmail real ni de conectividad externa en CI
(research.md Decisión 7); Gmail se configura por variables de entorno para
el uso real.

**Performance Goals**: el login no es un camino caliente (una vez por
sesión); la verificación de sesión revocada SÍ corre en cada petición
autenticada — se acepta el costo de una consulta adicional por request,
consistente con la verificación de licencia que ya corre por request desde
S1.7 (research.md Decisión 5, con su vía de optimización documentada).

**Constraints**: el login consulta `tenants.usuario` (alcance G1
`'tenant'`) **antes** de que exista contexto de tenant — debe correr bajo
`alcance_global()`, exactamente el mismo patrón que `verificar_api_key`
ya usa desde S1.2 (research.md Decisión 3). Ninguna respuesta de error
puede distinguir correo inexistente de contraseña incorrecta (FR-003) ni
revelar si una cuenta existe al recuperar (FR-021). Ninguna contraseña ni
token viaja o se persiste en claro (FR-025).

**Scale/Scope**: 1 módulo ampliado (`aerohub_tenancy`), 9 endpoints
nuevos, 1 puerto nuevo en `aerohub_contracts` + su adaptador SMTP, 4
tablas + 1 migración de restricción, 5 vistas Angular nuevas + shell con
menú dinámico + interceptor + guard, 1 servicio Docker nuevo, y **7
documentos normativos a actualizar** (pedido explícito del usuario).

## Constitution Check

*GATE: Debe cumplirse antes de Fase 0. Re-evaluado después de Fase 1.*

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE, con una
  ampliación deliberada de la superficie de `alcance_global()`. El login,
  la aceptación de invitación, la verificación de correo y la recuperación
  ocurren ANTES de que exista un tenant en contexto — igual que la
  autenticación por API Key (S1.2) y el aprovisionamiento de tenant
  (S1.1), ambos ya bajo `alcance_global()` con `motivo`+`rol` explícitos y
  auditados. Cada nuevo uso lleva su propio `motivo` distinguible
  (`autenticacion_login`, `aceptacion_invitacion`, …), no se reutiliza un
  motivo genérico. Una vez emitido el JWT, TODA petición posterior pasa
  por el guardián normal con `tenant_id` del token — el aislamiento de
  negocio no se relaja en ningún punto. PN-01 se refuerza: por primera vez
  se prueba con una sesión obtenida por login real, no con un token
  fabricado en el test.
- **Principio II (Arquitectura Modular por Capas)**: CUMPLE. Se amplía
  `aerohub_tenancy` con las 4 capas ya existentes; el puerto `EnviarCorreo`
  se declara en `packages/contracts` (su propósito declarado: "puertos
  entre módulos") y su adaptador SMTP vive en
  `aerohub_tenancy/infrastructure/`. `domain/` sigue puro: la política de
  contraseña y la vigencia de token son funciones sin I/O. El mapeo
  rol→módulos también vive en `aerohub_contracts` porque lo consumen DOS
  paquetes (`aerohub_tenancy` para emitir el perfil y `aerohub_gateway`
  para el JWT) y ninguno puede importar al otro (research.md Decisión 4).
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE, y ya
  aplicado en la fase de planificación: el soporte de `ALTER TABLE DROP
  CONSTRAINT`/`ADD CONSTRAINT` en MonetDB —el riesgo mayor de este
  sprint— se verificó contra el motor real ANTES de escribir el plan, no
  se asumió (research.md Decisión 2). El correo se verifica contra un SMTP
  real en Docker, no con un mock.
- **Principio IV (Calidad Continua en Verde)**: aplica sin excepción.
- **Principio V (Aprobación Explícita Antes de Acciones Irreversibles)**:
  aplica con énfasis: este sprint incluye una **migración destructiva de
  esquema** (`DROP CONSTRAINT` sobre una tabla con datos reales). Se
  presenta el diff antes de commitear y la migración detecta y reporta
  colisiones ANTES de intentar aplicarse (spec.md, Edge Cases).
- **Requisitos Tecnológicos y de Infraestructura**: CUMPLE — todo corre en
  Docker, incluido el servidor SMTP de prueba. La credencial de Gmail es
  un secreto de entorno que nunca entra al repositorio.

Sin violaciones que justificar — no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-identidad-y-acceso/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── auth-api.md
    ├── perfil-acceso.md
    └── correo-puerto.md
```

### Source Code (repository root)

```text
db/ddl/monetdb/16_identidad.sql             # 4 tablas nuevas + columnas nuevas
db/ddl/monetdb/17_migracion_email_unico.sql # DROP/ADD CONSTRAINT (migracion)
db/ddl/monetdb/99_grants_identidad.sql      # grants de las tablas nuevas
db/seeds/generate.py                        # + rol al usuario canario

packages/contracts/aerohub_contracts/
├── correo.py                # puerto EnviarCorreo + Mensaje (sin I/O)
└── roles_modulos.py         # mapeo rol -> modulos/scopes (artefacto versionado)

services/tenancy/aerohub_tenancy/
├── domain/
│   ├── password.py          # politica minima de contrasena (puro)
│   ├── sesion.py            # vigencia/revocacion (puro)
│   └── token_acceso.py      # tipos, vigencia, un-solo-uso (puro)
├── infrastructure/
│   ├── tablas.py            # + sesion, token_acceso, invitacion, intento_acceso
│   ├── alcances.py          # + registro G1 de las 4 tablas nuevas
│   ├── consultas_identidad.py
│   ├── comandos_identidad.py
│   └── correo_smtp.py       # adaptador SMTP del puerto EnviarCorreo
├── application/
│   ├── iniciar_sesion.py    # login, bloqueo, ultimo acceso, rol vigente
│   ├── cerrar_sesion.py
│   ├── gestionar_password.py  # cambio obligatorio, recuperacion, restablecer
│   ├── gestionar_invitacion.py
│   ├── verificar_correo.py
│   └── consultar_perfil.py  # GET /auth/yo -- modulos visibles
└── api/router_auth.py       # 9 endpoints nuevos

services/gateway/aerohub_gateway/
├── api/middleware.py        # + rutas exentas de auth, + verificacion de sesion
└── application/             # + validacion de sesion revocada

apps/web/src/app/
├── auth/
│   ├── auth.service.ts      # signals, persistencia, login/logout
│   ├── auth.interceptor.ts  # Authorization automatico
│   ├── auth.guard.ts        # canActivate
│   ├── login/               # vista de acceso
│   ├── cambiar-password/
│   ├── recuperar/
│   ├── restablecer/
│   ├── verificar-correo/
│   └── aceptar-invitacion/
├── shell/                   # layout + menu dinamico desde /auth/yo
├── usuarios/invitar/        # vista de invitacion (role_tenant_admin)
├── app.routes.ts            # + guard en rutas de negocio
├── app.config.ts            # + provideHttpClient(withInterceptors(...))
└── tenants/tenant-creation/ # - textarea del JWT manual

infra/docker-compose.yml     # + mailpit (SMTP de prueba) + variables de correo

tests/unit/tenancy/
tests/integration/test_login_sesion.py
tests/integration/test_invitacion_correo.py
tests/integration/test_perfil_modulos_visibles.py
tests/negative/test_pn16_login_no_revela_existencia.py
```

### Documentación normativa a actualizar

```text
docs/adr/ADR-020-autenticacion-y-sesiones.md   # NUEVO
docs/srs/AEROHUB-SRS-001-v2.0.md               # + RF-IA01..RF-IA08, + RNF-S06
docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md  # + 4 tablas, + columnas
docs/PLAN_IMPLEMENTACION_v2.0.md               # + Sec 8.10 (S1.10)
docs/runbooks/correo-smtp.md                   # NUEVO
docs/api/openapi.yaml                          # regenerado
CLAUDE.md                                      # + fila de sprint, + regla de secretos
```

**Structure Decision**: se amplía `aerohub_tenancy` en vez de crear
`services/identidad` porque las tablas de identidad (`usuario`, `rol`,
`usuario_rol`) ya son suyas — un módulo nuevo tendría que redeclararlas
todas y re-registrar sus alcances G1, precisamente el costo que el patrón
de redeclaración local existe para evitar, no para provocar (research.md
Decisión 1). El puerto de correo y el mapeo rol→módulos van a
`aerohub_contracts` porque los consumen dos paquetes que no pueden
importarse entre sí.

## Complexity Tracking

Sin violaciones que justificar.
