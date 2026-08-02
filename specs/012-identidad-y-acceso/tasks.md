# Tasks: Identidad y acceso

**Input**: Design documents from `specs/012-identidad-y-acceso/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: incluidas -- Principio III/IV de la constitución.

**Organización**: por historia de usuario (US1-US7 de `spec.md`), en
orden de prioridad (P1, P1, P2, P2, P3, P3, P3).

## Phase 1: Setup

- [X] T001 [P] `packages/contracts/aerohub_contracts/roles_modulos.py`:
      mapeo versionado rol -> (módulos, scopes, ruta del frontend) para
      los 16 roles de `tenants.rol` y los módulos M1-M9 de
      `catalogo.modulo` (research.md Decisión 4; data-model.md sección
      final). Exportarlo desde `aerohub_contracts/__init__.py`
- [X] T002 [P] `packages/contracts/aerohub_contracts/correo.py`: puerto
      `EnviarCorreo` + tipo `Mensaje` (destinatario, asunto, cuerpo texto,
      cuerpo HTML), sin I/O -- solo el contrato
      ([contracts/correo-puerto.md](./contracts/correo-puerto.md))
- [X] T003 [P] `infra/docker-compose.yml`: agregar servicio `mailpit`
      (SMTP de prueba en `:1025`, interfaz web en `:8025`) y las variables
      `AEROHUB_SMTP_*` + `AEROHUB_URL_BASE_APP` del servicio `gateway`,
      **sin** incluir ninguna contraseña real (research.md Decisión 7)
- [X] T004 [P] Confirmar que `.importlinter` no requiere contrato nuevo:
      `aerohub_tenancy` ya tiene su contrato de capas y
      `aerohub_contracts` ya es root package -- verificar y documentar si
      hace falta algún ajuste

---

## Phase 2: Foundational (bloqueante para US1-US7)

**Propósito**: esquema de identidad + migración de unicidad del correo.
Ninguna historia puede implementarse sin esto.

**⚠️ CRÍTICO**: T006 es una **migración destructiva** sobre datos reales
(`DROP CONSTRAINT`). Debe detectar colisiones y abortar ANTES de aplicar.

- [X] T005 `db/ddl/monetdb/16_identidad.sql`: las 4 tablas nuevas de
      [data-model.md](./data-model.md) (`sesion`, `token_acceso`,
      `invitacion`, `intento_acceso`) con sus CHECK/FK, más las 3
      columnas nuevas de `tenants.usuario` (`email_verificado_en`,
      `debe_cambiar_password`, `bloqueado_hasta`) vía `ALTER TABLE ADD
      COLUMN` (sintaxis ya verificada contra MonetDB real, research.md
      Decisión 2)
- [X] T006 `db/ddl/monetdb/17_migracion_email_unico.sql`: migrar
      `uq_usuario_tenant_email UNIQUE(tenant_id, email)` a
      `uq_usuario_email UNIQUE(email)`. DEBE incluir la consulta de
      detección de colisiones documentada en research.md Decisión 2 y
      abortar con informe legible si encuentra alguna
- [X] T007 `db/ddl/monetdb/99_grants_identidad.sql`: grants de las 4
      tablas nuevas. `role_platform_admin` escribe todas (corre los flujos
      de identidad bajo `alcance_global`); `role_tenant_admin` con
      SELECT/INSERT sobre `invitacion`; `role_sre` con SELECT sobre
      `intento_acceso` (diagnóstico); nunca DELETE (P5)
- [X] T008 [P] `services/tenancy/aerohub_tenancy/infrastructure/alcances.py`:
      registrar G1 de las 4 tablas nuevas -- `sesion`/`token_acceso`/
      `intento_acceso` como `'interno'`, `invitacion` como `'tenant'`
      (research.md Decisión 9, con el razonamiento en el docstring)
- [X] T009 [P] `services/tenancy/aerohub_tenancy/infrastructure/tablas.py`:
      `Table()` de las 4 tablas nuevas + las columnas nuevas de `usuario`
- [X] T010 Verificación empírica: aplicar `16_` y `17_` contra MonetDB
      real en Docker (primario, standby y restore-test, mismo pipeline
      versionado que exige S1.9), confirmar las 4 tablas, las 3 columnas
      y que la restricción de correo quedó global (Principio III)

**Checkpoint**: esquema de identidad listo -- US1-US7 pueden empezar.

---

## Phase 3: User Story 1 - Iniciar sesión con credenciales propias (Priority: P1) 🎯 MVP (parte 1/2)

**Goal**: emitir un JWT real contra correo + contraseña, con bloqueo por
intentos fallidos y sin revelar si el correo existe.

**Independent Test**: crear un tenant, iniciar sesión con el correo y la
contraseña temporal del admin, y consultar un dato de negocio real --
Escenario 1 de `quickstart.md`.

### Tests para US1

- [X] T011 [P] [US1] Test unitario: política mínima de contraseña
      (longitud, composición, mensaje del requisito que falta) en
      `tests/unit/tenancy/test_password.py`
- [X] T012 [P] [US1] Test unitario: resolución de rol vigente -- uno
      vigente OK, ninguno vigente error, varios vigentes error de
      inconsistencia, uno expirado se ignora, en
      `tests/unit/tenancy/test_rol_vigente.py`
- [X] T013 [P] [US1] Test de integración: ciclo completo de login contra
      MonetDB real -- credenciales válidas emiten JWT usable contra un
      endpoint de negocio; contraseña incorrecta y correo inexistente
      devuelven cuerpos idénticos; cuenta inactiva rechazada; bloqueo tras
      N fallos rechaza incluso con la contraseña correcta; se actualiza
      `ultimo_acceso_en`, en `tests/integration/test_login_sesion.py`
- [X] T014 [P] [US1] Test negativo PN-16 (nuevo): el login no revela la
      existencia de una cuenta -- respuestas byte a byte iguales entre
      correo inexistente y contraseña incorrecta, en
      `tests/negative/test_pn16_login_no_revela_existencia.py`

### Implementación de US1

- [X] T015 [P] [US1] `services/tenancy/aerohub_tenancy/domain/password.py`:
      política mínima de contraseña -- puro, sin I/O
- [X] T016 [P] [US1] `services/tenancy/aerohub_tenancy/domain/sesion.py`:
      vigencia de sesión (`revocada_en IS NULL AND expira_en > ahora`) --
      puro
- [X] T017 [US1] `services/tenancy/aerohub_tenancy/infrastructure/consultas_identidad.py`
      (parcial): `obtener_usuario_por_email`, `listar_roles_vigentes`,
      `contar_intentos_fallidos_recientes`
- [X] T018 [US1] `services/tenancy/aerohub_tenancy/infrastructure/comandos_identidad.py`
      (parcial): `insertar_intento_acceso`, `insertar_sesion`,
      `actualizar_ultimo_acceso`, `fijar_bloqueo`
- [X] T019 [US1] `services/tenancy/aerohub_tenancy/application/iniciar_sesion.py`:
      caso de uso completo bajo
      `alcance_global(motivo="autenticacion_login", rol="role_platform_admin")`
      (research.md Decisión 3); emite el JWT con `codificar_jwt` incluyendo
      el id de sesión; audita el evento (depende de T015-T018)
- [X] T020 [US1] **FIX**: `services/tenancy/aerohub_tenancy/application/aprovisionar_tenant.py`
      debe insertar en `tenants.usuario_rol` asignando `role_tenant_admin`
      al usuario admin, en la MISMA transacción -- hoy no lo hace y ese
      usuario no podría loguearse nunca (spec.md FR-014)
- [X] T021 [US1] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (parcial): `POST /auth/login`
      ([contracts/auth-api.md](./contracts/auth-api.md))
- [X] T022 [US1] `services/gateway/aerohub_gateway/api/middleware.py`:
      agregar las rutas públicas de auth a `RUTAS_EXENTAS` y montar
      `router_auth` en `services/gateway/main.py`
- [X] T023 [US1] `db/seeds/generate.py`: asignar rol a los usuarios
      canario (`role_tenant_admin` a MEC/UIO) y fijar una contraseña
      conocida, para que la suite de integración pueda loguearse

**Checkpoint**: US1 funcional -- SC-001/SC-002/SC-003 verificables.

---

## Phase 4: User Story 2 - Ver únicamente los módulos que me corresponden (Priority: P1) 🎯 MVP (parte 2/2)

**Goal**: `GET /auth/yo` devuelve el perfil con los módulos visibles ya
resueltos, y el frontend construye su menú desde ahí.

**Independent Test**: dos usuarios de roles distintos ven menús
distintos; un módulo sin licencia desaparece aunque el rol lo permita --
Escenario 2 de `quickstart.md`.

### Tests para US2

- [X] T024 [P] [US2] Test unitario: cálculo de módulos visibles como
      intersección rol × licencia -- rol sin el módulo, tenant sin
      licencia, ambos, ninguno; usuario de plataforma sin tenant, en
      `tests/unit/tenancy/test_modulos_visibles.py`
- [X] T025 [P] [US2] Test de integración: `GET /auth/yo` tras login real
      devuelve exactamente los módulos esperados; retirar la licencia de
      un módulo lo elimina del resultado; dos roles distintos devuelven
      conjuntos distintos, en
      `tests/integration/test_perfil_modulos_visibles.py`

### Implementación de US2

- [X] T026 [US2] `services/tenancy/aerohub_tenancy/infrastructure/consultas_identidad.py`
      (resto): lectura de `tenants.licencia`/`catalogo.modulo`
      redeclaradas localmente -- reutilizar la lógica de vigencia de
      `existe_licencia_vigente()` de S1.7 sin modificar ese código
- [X] T027 [US2] `services/tenancy/aerohub_tenancy/application/consultar_perfil.py`:
      arma el perfil completo (usuario, tenant, rol, scopes, módulos
      visibles) según
      [contracts/perfil-acceso.md](./contracts/perfil-acceso.md)
      (depende de T001 y T026)
- [X] T028 [US2] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (parcial): `GET /auth/yo`; y devolver el mismo perfil en la
      respuesta de `POST /auth/login` para evitar una segunda llamada
- [X] T029 [P] [US2] `apps/web/src/app/auth/auth.service.ts`: signals de
      sesión y perfil, `login()`, `logout()`, persistencia en
      `localStorage`
- [X] T030 [P] [US2] `apps/web/src/app/auth/auth.interceptor.ts`: agrega
      `Authorization: Bearer` automáticamente; redirige a `/login` ante
      401
- [X] T031 [P] [US2] `apps/web/src/app/auth/auth.guard.ts`: `canActivate`
      que exige sesión
- [X] T032 [US2] `apps/web/src/app/auth/login/`: vista de acceso (correo +
      contraseña). **Usar el skill `frontend-design`** antes de escribirla
      (regla de trabajo del proyecto)
- [X] T033 [US2] `apps/web/src/app/shell/`: layout con menú lateral
      dinámico alimentado por el perfil de `AuthService` -- sin lógica de
      permisos propia (FR-028)
- [X] T034 [US2] `apps/web/src/app/app.routes.ts` + `app.config.ts`:
      registrar el interceptor, aplicar el guard a las rutas de negocio,
      envolverlas en el shell, y agregar la ruta pública `/login`
- [X] T035 [US2] `apps/web/src/app/tenants/tenant-creation/`: eliminar el
      textarea del JWT manual y el signal `tokenJwt`; el token ahora sale
      del interceptor (FR-029). Ajustar `tenant.service.ts` para no
      recibir el token por parámetro

**Checkpoint**: US1+US2 = MVP del sprint -- SC-004 verificado, la app deja
de pedir un token pegado a mano.

---

## Phase 5: User Story 3 - Cambiar la contraseña temporal en el primer acceso (Priority: P2)

**Goal**: mientras `debe_cambiar_password` sea true, la sesión solo
permite el endpoint de cambio.

**Independent Test**: login con contraseña temporal, cualquier endpoint de
negocio responde 403, tras cambiarla todo funciona -- Escenario 3 de
`quickstart.md`. Depende de US1.

### Tests para US3

- [X] T036 [US3] Test de integración: endpoint de negocio bloqueado con
      403 mientras `debe_cambiar_password`; contraseña débil rechazada con
      422 y el requisito faltante; tras el cambio queda todo disponible y
      las demás sesiones del usuario quedan revocadas, en
      `tests/integration/test_cambio_password.py`

### Implementación de US3

- [X] T037 [US3] `services/tenancy/aerohub_tenancy/application/gestionar_password.py`
      (parcial): `cambiar_password` -- valida la actual, aplica la política
      de T015, revoca las demás sesiones, audita
- [X] T038 [US3] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (parcial): `POST /auth/cambiar-password`
- [X] T039 [US3] `services/gateway/aerohub_gateway/api/middleware.py`:
      bloquear toda ruta autenticada distinta del cambio de contraseña
      cuando la sesión trae `debe_cambiar_password` (FR-012)
- [X] T040 [US3] `apps/web/src/app/auth/cambiar-password/`: vista de
      cambio + redirección automática desde el login cuando corresponde

**Checkpoint**: US3 funcional -- se cierra el riesgo de la contraseña
temporal permanente.

---

## Phase 6: User Story 4 - Invitar personas a mi organización (Priority: P2)

**Goal**: un `role_tenant_admin` invita por correo; la persona acepta,
fija su contraseña y opera en ese tenant.

**Independent Test**: invitar, leer el correo en `mailpit`, aceptar,
iniciar sesión con la cuenta nueva -- Escenario 4 de `quickstart.md`.
Depende de US1 y de la infraestructura de correo.

### Tests para US4

- [X] T041 [P] [US4] Test unitario: vigencia y un-solo-uso de token
      (`consumido_en IS NULL AND expira_en > ahora`) en
      `tests/unit/tenancy/test_token_acceso.py`
- [X] T042 [P] [US4] Test de integración end-to-end contra `mailpit`
      real: invitar -> el correo llega con su enlace -> aceptar crea el
      usuario con el rol correcto -> reusar el token da 410 -> invitar un
      correo existente da 409 -> invitar sin ser admin da 403, en
      `tests/integration/test_invitacion_correo.py`

### Implementación de US4

- [X] T043 [P] [US4] `services/tenancy/aerohub_tenancy/domain/token_acceso.py`:
      tipos, vigencia y regla de un-solo-uso -- puro
- [X] T044 [US4] `services/tenancy/aerohub_tenancy/infrastructure/correo_smtp.py`:
      adaptador SMTP del puerto `EnviarCorreo` con `smtplib` +
      `email.message`, configurado por las variables `AEROHUB_SMTP_*`
      (research.md Decisión 6)
- [X] T045 [P] [US4] Plantillas de correo (invitación, verificación,
      recuperación, aviso de acceso) --
      [contracts/correo-puerto.md](./contracts/correo-puerto.md)
- [X] T046 [US4] `services/tenancy/aerohub_tenancy/infrastructure/comandos_identidad.py`
      (resto): `insertar_token_acceso` (con el token **hasheado**,
      research.md Decisión 8), `consumir_token`, `invalidar_tokens_previos`,
      `insertar_invitacion`, `marcar_invitacion_aceptada`,
      `insertar_usuario_invitado`
- [X] T047 [US4] `services/tenancy/aerohub_tenancy/application/gestionar_invitacion.py`:
      `invitar_usuario` (exclusivo `role_tenant_admin`, falla si el correo
      ya existe, falla si el correo no se pudo enviar) y
      `aceptar_invitacion` (crea usuario + rol + consume token + marca
      invitación, todo en una transacción, bajo
      `alcance_global(motivo="aceptacion_invitacion", ...)`)
- [X] T048 [US4] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (parcial): `POST /usuarios/invitaciones`,
      `POST /usuarios/aceptar-invitacion`
- [X] T049 [US4] `services/gateway/main.py`: inyectar el adaptador SMTP
      como implementación del puerto en el arranque de la app
- [X] T050 [P] [US4] `apps/web/src/app/usuarios/invitar/`: vista de
      invitación (solo visible para `role_tenant_admin`)
- [X] T051 [P] [US4] `apps/web/src/app/auth/aceptar-invitacion/`: vista
      pública de aceptación (nombre + contraseña)

**Checkpoint**: US4 funcional -- SC-005/SC-006 verificados; un tenant
puede tener más de un usuario por primera vez.

---

## Phase 7: User Story 5 - Verificar que el correo es real (Priority: P3)

**Goal**: confirmar la titularidad del correo con un enlace de un solo
uso.

**Independent Test**: solicitar verificación, seguir el enlace, la cuenta
queda verificada; reusar el enlace falla -- Escenario 5 de
`quickstart.md`. Depende de US4 (comparte tokens y correo).

### Tests para US5

- [X] T052 [US5] Test de integración: solicitar -> correo en `mailpit` ->
      verificar marca `email_verificado_en` -> reusar da 410 -> token
      vencido da 410, en `tests/integration/test_verificacion_correo.py`

### Implementación de US5

- [X] T053 [US5] `services/tenancy/aerohub_tenancy/application/verificar_correo.py`:
      `solicitar_verificacion` y `verificar_correo` (depende de T043,
      T044, T046)
- [X] T054 [US5] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (parcial): `POST /auth/solicitar-verificacion`,
      `POST /auth/verificar-correo`
- [X] T055 [US5] `apps/web/src/app/auth/verificar-correo/`: vista pública
      que consume el enlace y reporta el resultado

**Checkpoint**: US5 funcional.

---

## Phase 8: User Story 6 - Recuperar el acceso si olvidé mi contraseña (Priority: P3)

**Goal**: recuperación autoservicio por correo, que invalida las sesiones
abiertas al restablecerse.

**Independent Test**: solicitar, seguir el enlace, fijar contraseña
nueva, iniciar sesión con ella y no con la anterior -- Escenario 6 de
`quickstart.md`. Depende de US4 (tokens y correo) y US3 (política de
contraseña).

### Tests para US6

- [X] T056 [US6] Test de integración: solicitar con correo existente e
      inexistente devuelve **202 idéntico**; restablecer cambia la
      contraseña, invalida la anterior y revoca las sesiones previas;
      token reusado o vencido da 410, en
      `tests/integration/test_recuperacion_password.py`

### Implementación de US6

- [X] T057 [US6] `services/tenancy/aerohub_tenancy/application/gestionar_password.py`
      (resto): `solicitar_recuperacion` (respuesta idéntica exista o no la
      cuenta, FR-021) y `restablecer_password` (revoca TODAS las sesiones,
      FR-022)
- [X] T058 [US6] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (parcial): `POST /auth/recuperar`, `POST /auth/restablecer`
- [X] T059 [P] [US6] `apps/web/src/app/auth/recuperar/` y
      `apps/web/src/app/auth/restablecer/`: vistas públicas

**Checkpoint**: US6 funcional -- SC-008 verificado.

---

## Phase 9: User Story 7 - Cerrar sesión de verdad (Priority: P3)

**Goal**: revocar la sesión al instante, sin esperar al vencimiento del
JWT.

**Independent Test**: iniciar sesión, cerrar sesión, comprobar que el
token anterior ya no sirve -- Escenario 7 de `quickstart.md`. Depende de
US1.

### Tests para US7

- [X] T060 [US7] Test de integración: tras `POST /auth/logout` el mismo
      token es rechazado por un endpoint de negocio; cerrar una sesión ya
      cerrada es idempotente, en `tests/integration/test_cierre_sesion.py`

### Implementación de US7

- [X] T061 [US7] `services/tenancy/aerohub_tenancy/application/cerrar_sesion.py`:
      revoca la sesión del JWT presentado
- [X] T062 [US7] `services/tenancy/aerohub_tenancy/api/router_auth.py`
      (resto): `POST /auth/logout`
- [X] T063 [US7] `services/gateway/aerohub_gateway/`: verificación de
      sesión vigente en CADA petición autenticada dentro del middleware
      (research.md Decisión 5) -- rechaza sesión revocada o vencida
- [X] T064 [US7] `apps/web/src/app/shell/`: botón de cerrar sesión que
      llama al endpoint y limpia el estado local

**Checkpoint**: US7 funcional -- SC-009 verificado. Las 7 historias
completas.

---

## Phase 10: Documentación normativa (pedido explícito del usuario)

**Propósito**: "que todo quede registrado". No es opcional ni posterior
al sprint -- es entregable de este sprint.

- [X] T065 [P] `docs/adr/ADR-020-autenticacion-y-sesiones.md` NUEVO:
      decide JWT + sesión revocable, Argon2id reutilizado, política de
      contraseñas, vencimientos, puerto de correo, y **por qué NO** se
      adopta OAuth/SSO/MFA todavía. Formato de los ADR-017/018/019
- [X] T066 [P] `docs/srs/AEROHUB-SRS-001-v2.0.md`: agregar la familia
      `RF-IA01`..`RF-IA08` y `RNF-S06`, marcadas como identificadores
      editoriales igual que las familias editoriales ya existentes, con la
      nota de por qué NO se usan `RF-O20/21/22` (reservados en el Apéndice
      A) -- research.md Decisión 10
- [X] T067 [P] `docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md`: las 4
      tablas nuevas, las 3 columnas nuevas de `usuario` y la migración de
      la restricción de unicidad del correo
- [X] T068 [P] `docs/PLAN_IMPLEMENTACION_v2.0.md`: sección §8.10 nueva
      (Sprint S1.10) con objetivo, entregables, compuerta de pruebas y
      DoD, en el formato de §8.1-§8.9
- [X] T069 [P] `docs/runbooks/correo-smtp.md` NUEVO: cómo generar la
      contraseña de aplicación de Gmail (exige 2FA), variables de
      entorno, límites de envío conocidos, `mailpit` en desarrollo, y qué
      cambiaría al migrar a un proveedor transaccional
- [X] T070 `docs/api/openapi.yaml`: regenerar con
      `tools/generar_openapi.py` incluyendo las rutas nuevas

---

## Phase 11: Polish & Cross-Cutting

- [X] T071 Regresión completa PN-01..PN-16 y suite cruzada -- **PN-01
      ahora con sesión obtenida por login real**, no con token fabricado
      (Escenario 8 de `quickstart.md`)
- [X] T072 Re-medir RNF-P01 con la verificación de sesión activa por
      petición (dos consultas por request en vez de una, research.md
      Decisión 5) y documentar el resultado en `docs/runbooks/monetdb.md`
- [X] T073 `ruff check .`, `mypy .`, `bandit -r services packages tools`,
      `lint-imports` en verde dentro del contenedor del gateway
- [X] T074 Ejecutar los 8 escenarios de [quickstart.md](./quickstart.md)
      completos contra Docker real (MonetDB + mailpit + gateway + web)
- [ ] T075 Actualizar `CLAUDE.md`: fila S1.10 con el hash del commit, y
      una regla de trabajo nueva sobre secretos de correo (nunca
      commitear credenciales SMTP)

---

## Dependencies & Execution Order

### Fases

- **Setup (Fase 1)**: sin dependencias
- **Foundational (Fase 2)**: depende de Setup -- BLOQUEA US1-US7
- **US1 (Fase 3, P1)**: depende de Foundational -- MVP junto con US2
- **US2 (Fase 4, P1)**: depende de US1 (necesita una sesión real que
  consultar) y de T001 (mapeo rol→módulos)
- **US3 (Fase 5, P2)**: depende de US1
- **US4 (Fase 6, P2)**: depende de US1 + infraestructura de correo (T044)
- **US5 (Fase 7, P3)**: depende de US4 (comparte tokens y adaptador de
  correo)
- **US6 (Fase 8, P3)**: depende de US4 (tokens/correo) y US3 (política de
  contraseña)
- **US7 (Fase 9, P3)**: depende de US1
- **Documentación (Fase 10)**: puede escribirse en paralelo a las
  historias; se cierra al final para reflejar lo realmente construido
- **Polish (Fase 11)**: depende de todas las historias

### Oportunidades de paralelismo

- Fase 1 completa en paralelo (4 archivos distintos)
- Dentro de Foundational: T008/T009 en paralelo; T005→T006→T007
  secuenciales (mismo esquema)
- Dentro de cada historia: `domain/` [P] y tests [P] en paralelo;
  `router_auth.py` es compartido por US1/US2/US3/US4/US5/US6/US7 -- esas
  tareas concretas son secuenciales entre sí
- Frontend (T029-T035, T050-T051, T055, T059) en paralelo con el backend
  una vez que el contrato de la API está fijado
- Toda la Fase 10 en paralelo (documentos distintos), salvo T070 que
  necesita las rutas ya implementadas

---

## Parallel Example: User Story 1

```bash
# Tests de US1 en paralelo:
Task: "Test de politica de password en tests/unit/tenancy/test_password.py"
Task: "Test de rol vigente en tests/unit/tenancy/test_rol_vigente.py"
Task: "Test de login en tests/integration/test_login_sesion.py"
Task: "PN-16 en tests/negative/test_pn16_login_no_revela_existencia.py"

# Dominio de US1 en paralelo:
Task: "domain/password.py"
Task: "domain/sesion.py"
```

---

## Implementation Strategy

### MVP primero (US1 + US2)

1. Fase 1: Setup
2. Fase 2: Foundational (incluye la migración destructiva -- máxima
   atención)
3. Fase 3: US1 -- login real (SC-001/SC-002/SC-003)
4. Fase 4: US2 -- menú por rol × licencia (SC-004)
5. **Validar**: Escenarios 1 y 2 de `quickstart.md`
6. En ese punto la aplicación deja de pedir un JWT pegado a mano: es el
   primer momento en que el producto es entregable a un usuario real

### Entrega incremental

1. Setup + Foundational → esquema de identidad listo
2. US1 → login real
3. US2 → menú dinámico (MVP completo)
4. US3 → cambio obligatorio de contraseña temporal
5. US4 → invitaciones (un tenant deja de estar limitado a un usuario)
6. US5 → verificación de correo
7. US6 → recuperación de contraseña
8. US7 → cierre de sesión revocable
9. Documentación → los 7 documentos normativos
10. Polish → regresión, calidad, medición, cierre

---

## Notes

- **T006 es una migración destructiva sobre datos reales.** Antes de
  aplicarla contra cualquier base con datos, verificar la detección de
  colisiones. Hoy no hay correos duplicados (verificado empíricamente en
  la fase de plan), pero eso puede cambiar antes de ejecutarla.
- La superficie de `alcance_global()` crece en este sprint (4 flujos
  nuevos). Cada uno lleva su propio `motivo` distinguible -- revisar que
  ninguno reutilice un motivo genérico (Principio I).
- Las vistas nuevas usan el skill `frontend-design` antes de escribirse
  (regla de trabajo del proyecto para `apps/web`).
- Ninguna credencial SMTP real entra al repositorio, en ningún archivo,
  en ningún momento.
- Commit solo cuando el usuario lo pida explícitamente, con diff
  presentado antes (Principio V).
- **Hallazgo real de verificación empírica (retomado tras corte de
  sesión)**: `iniciar_sesion` insertaba `intento_acceso` y lanzaba
  `CredencialesInvalidas` dentro del mismo `with sesion()`, así que
  `sesion()` revertía la fila junto con la excepción (P8) -- el bloqueo
  tras N fallos y la auditoría de intentos fallidos nunca funcionaron
  hasta que `tests/integration/test_login_sesion.py` lo hizo evidente.
  Corregido capturando la excepción DENTRO del bloque (para que la
  transacción cierre en commit) y relanzándola DESPUÉS. T063
  (verificación de sesión por request) tampoco estaba implementado pese
  a que US7 lo exige para que `logout` sea real -- ambos cerrados en
  esta continuación de sesión, con tests que los cubren.
