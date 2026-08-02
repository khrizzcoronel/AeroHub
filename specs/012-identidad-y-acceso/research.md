# Research: Identidad y acceso (S1.10)

## Decisión 1 — Ampliar `aerohub_tenancy`, no crear `services/identidad`

**Decisión**: todo el backend de identidad se implementa dentro del módulo
existente `services/tenancy/aerohub_tenancy/`, respetando sus 4 capas.

**Razón**: las tablas que la autenticación necesita leer y escribir
(`tenants.usuario`, `tenants.rol`, `tenants.usuario_rol`) **ya son
propiedad de `aerohub_tenancy`**, con sus `Table()` declarados y sus
alcances G1 registrados en `aerohub_tenancy/infrastructure/alcances.py`.
Un módulo nuevo tendría que redeclararlas todas localmente y re-registrar
sus alcances de forma idempotente — el patrón de redeclaración existe
para permitir que un módulo LEA una tabla ajena de forma puntual (p. ej.
`ops.vuelo` desde `gates`/`ramp`), no para partir en dos la propiedad de
un conjunto de tablas que ya tiene dueño claro.

**Alternativas consideradas**: (a) `services/identidad` nuevo —
rechazada por lo anterior, además de que la autenticación necesita
ESCRIBIR sobre `usuario` (bloqueo, último acceso, verificación), no solo
leerla, y la propiedad de escritura repartida entre dos módulos sobre la
misma tabla es exactamente lo que la independencia de módulos evita; (b)
ponerlo en `aerohub_gateway` — rechazada: el gateway es el compositor y el
guardián de la petición, no el dueño de datos de negocio; hoy solo lee
`tenants.api_key`/`licencia` de forma redeclarada y puntual, y darle la
gestión completa del ciclo de vida del usuario lo convertiría en un
módulo de negocio encubierto.

## Decisión 2 — Migración de unicidad del correo: verificada empíricamente antes de planificar

**Decisión**: la restricción `uq_usuario_tenant_email UNIQUE(tenant_id,
email)` se reemplaza por `uq_usuario_email UNIQUE(email)` mediante
`ALTER TABLE ... DROP CONSTRAINT` + `ALTER TABLE ... ADD CONSTRAINT`, en
un archivo DDL de migración separado (`17_migracion_email_unico.sql`), no
editando `02_tenants.sql` en su lugar.

**Razón / hallazgo empírico**: era el riesgo mayor del sprint —MonetDB
tiene huecos conocidos de DDL (no soporta `SELECT ... FOR UPDATE` ni
`EXCLUDE USING gist`, hallazgos de S1.4)— así que **se probó contra el
motor real antes de escribir este plan**, sobre una tabla temporal:

- `ALTER TABLE ... DROP CONSTRAINT <uq>` → `operation successful`
- `ALTER TABLE ... ADD CONSTRAINT <uq> UNIQUE (email)` → `operation successful`
- `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT FALSE` → `operation successful`
- Un `INSERT` que viola la restricción nueva falla con
  `INSERT INTO: UNIQUE constraint 'tabla.uq_...' violated`

Además se consultó el estado real de los datos: **hoy no existe ningún
correo duplicado** en `tenants.usuario`
(`GROUP BY email HAVING COUNT(*) > 1` devuelve 0 filas), así que la
migración no encuentra colisiones en el entorno actual.

**Por qué un archivo de migración separado y no editar el DDL original**:
`db/migrations/apply.py` aplica los `.sql` en orden lexicográfico sobre
una base **nueva**; editar `02_tenants.sql` dejaría inconsistente
cualquier base ya creada. El archivo `17_` aplica el cambio a las bases
existentes y es idempotente-por-orden en una base nueva (crea la tabla con
la restricción vieja y la migra acto seguido) — el costo es una operación
redundante en instalaciones nuevas, a cambio de un único camino de
migración válido para todas.

**Salvaguarda obligatoria**: la migración DEBE detectar colisiones y
abortar con un informe legible ANTES de intentar el `ADD CONSTRAINT`, en
vez de fallar a mitad con el error crudo del motor (spec.md, Edge Cases).

**Alternativas consideradas**: (a) conservar la unicidad por tenant y
pedir el código de tenant en el login — rechazada por el usuario en la
consulta explícita previa a este sprint; (b) unicidad global mediante un
índice único sin restricción declarada — rechazada, MonetDB soporta la
restricción declarativa, que además documenta la intención en el esquema.

## Decisión 3 — El login corre bajo `alcance_global()`, con precedente directo

**Decisión**: `iniciar_sesion`, `aceptar_invitacion`, `verificar_correo` y
`recuperar/restablecer` se ejecutan dentro de
`alcance_global(motivo=<propio de cada flujo>, rol="role_platform_admin")`.

**Razón**: `tenants.usuario` está registrada con alcance G1 `'tenant'`, y
el guardián G2 aborta cualquier consulta sobre una tabla de ese alcance
sin filtro explícito de `tenant_id`. En el login, por definición, todavía
NO se sabe a qué tenant pertenece quien intenta entrar — ese es el dato
que la consulta debe descubrir. Es el mismo problema que ya resolvió
`verificar_api_key` (S1.2), que corre bajo
`alcance_global(motivo="autenticacion_api_key", rol="role_platform_admin")`
por la razón idéntica. Se sigue ese precedente en vez de inventar un
mecanismo nuevo.

**Cada flujo lleva su propio `motivo`** (`autenticacion_login`,
`aceptacion_invitacion`, `verificacion_correo`, `recuperacion_password`),
no un `motivo` genérico compartido: la superficie de excepción debe seguir
siendo una lista finita y revisable en auditoría (Principio I), y un
motivo único por flujo permite distinguirlos al revisar
`compliance.log_auditoria`.

**Alternativas consideradas**: (a) declarar `tenants.usuario` con alcance
`'interno'` para no necesitar la excepción — rechazada, sería degradar una
protección real (el aislamiento de usuarios entre tenants) por comodidad
de un único flujo; (b) una conexión administrativa directa por `pymonetdb`
como hace `aerohub_continuidad` (S1.9) — rechazada, aquí sí existe un
modelo tipado por `Table()` y el guardián sí sabe inspeccionarlo; saltarlo
sería perder la verificación en todas las consultas POSTERIORES al login
dentro del mismo flujo.

## Decisión 4 — El mapeo rol→módulos vive en `aerohub_contracts`

**Decisión**: se crea `packages/contracts/aerohub_contracts/roles_modulos.py`
con la tabla de decisión explícita rol → (módulos, scopes), como dato
versionado en código, no en base de datos.

**Razón**: lo consumen DOS paquetes que no pueden importarse entre sí
(`.importlinter`, contrato "ningún módulo importa domain/application de
otro"): `aerohub_tenancy` lo necesita para resolver los scopes del JWT y
los módulos visibles del perfil; `aerohub_gateway` lo necesita para
razonar sobre la identidad autenticada. `aerohub_contracts` existe
exactamente para eso — su docstring lo declara: "una utilidad que TODO
módulo de negocio necesita y que ninguno puede importar de otro módulo sin
romper la independencia". Es el mismo lugar y la misma razón por la que
ahí vive `requiere_scope` desde S1.2.

**Por qué en código y no en una tabla nueva**: es una decisión de
arquitectura de permisos, no un dato operativo que un tenant configure.
Ponerla en base de datos la volvería editable en caliente sin revisión de
código ni trazabilidad en el historial de Git — lo contrario de lo que un
control de acceso necesita. La matriz Rol × Esquema de Análisis v6.0
§4.3.1 ya vive como DDL de `GRANT`s versionados por la misma razón.

**Alternativas consideradas**: (a) tabla `tenants.rol_modulo` — rechazada
por lo anterior; (b) derivarlo de los `GRANT`s de MonetDB — rechazada, los
grants son permisos de ESQUEMA (eje departamental), no de módulo
funcional; un rol puede tener `SELECT` sobre `ops` sin que le corresponda
ver el módulo M3 en el menú.

## Decisión 5 — La revocación de sesión se verifica en cada petición

**Decisión**: el JWT lleva el identificador de la sesión; el middleware
del gateway verifica en cada petición autenticada que esa sesión siga
vigente (no revocada, no vencida) antes de dejar pasar la petición.

**Razón**: sin esta verificación, "cerrar sesión" solo borraría la
credencial del navegador mientras el JWT sigue siendo válido hasta su
`exp` — es decir, no sería un cierre de sesión real (FR-023), y el
restablecimiento de contraseña no podría invalidar sesiones abiertas
(FR-022), que es un requisito de seguridad concreto, no una comodidad.

**Costo asumido, declarado explícitamente**: una consulta adicional a la
base por petición autenticada. Es consistente con lo que el sistema ya
hace desde S1.7: `verificar_licencia` abre su propia `sesion()` en cada
petición dentro del mismo middleware. Este sprint lleva el costo de una a
dos consultas por request. **Vía de optimización documentada, no
implementada aquí**: ambas verificaciones podrían resolverse en una única
sesión/consulta combinada, o cachearse por un intervalo corto — se deja
fuera de alcance porque optimizar antes de medir sería especulativo, y
RNF-P01 se re-mide en la compuerta de pruebas de este sprint.

**Alternativas consideradas**: (a) no revocar y confiar en un `exp` corto
— rechazada, incumple FR-022/FR-023 de forma directa; (b) lista de
revocación en memoria del proceso — rechazada, se pierde al reiniciar y no
funciona con más de una instancia del gateway, que es el objetivo de
despliegue declarado.

## Decisión 6 — Adaptador SMTP con la biblioteca estándar, sin dependencia nueva

**Decisión**: el puerto `EnviarCorreo` se declara en
`aerohub_contracts/correo.py` (sin I/O, solo el contrato y el tipo de
mensaje); el adaptador vive en
`aerohub_tenancy/infrastructure/correo_smtp.py` y usa `smtplib` +
`email.message` de la biblioteca estándar de Python.

**Razón**: enviar un correo por SMTP autenticado con STARTTLS es
exactamente lo que `smtplib.SMTP` + `starttls()` + `login()` resuelve en
unas pocas líneas; una dependencia externa añadiría superficie de
mantenimiento y de auditoría de seguridad (Trivy/Bandit en CI) sin aportar
nada para cuatro plantillas de correo. El día que se migre a un proveedor
transaccional con API HTTP, el cambio es un adaptador nuevo que implementa
el mismo puerto — la razón de ser del puerto.

**Alternativas consideradas**: `fastapi-mail` u otra librería de
conveniencia — rechazada por lo anterior; además arrastra su propia
configuración y su propio modelo de plantillas, duplicando decisiones que
el proyecto ya toma.

## Decisión 7 — Servidor SMTP de prueba en Docker (`mailpit`), no Gmail en las pruebas

**Decisión**: `infra/docker-compose.yml` incorpora `mailpit` (servidor
SMTP de prueba con bandeja web y API de consulta). La suite de integración
envía contra él y **consulta su API para verificar que el correo llegó y
qué enlace contiene**. Gmail se configura por variables de entorno para el
uso real, nunca para las pruebas.

**Razón**: la constitución exige verificación empírica contra servicios
reales en Docker (Principio III) — un *mock* de `smtplib` probaría que
llamamos a una función, no que el correo sale bien formado. Pero apuntar
la suite a Gmail real sería inaceptable por tres motivos: consumiría el
cupo diario de la cuenta, exigiría conectividad externa y credenciales
válidas en CI, y enviaría correos de verdad a direcciones de prueba.
`mailpit` es un SMTP real (protocolo real, TLS real) que no entrega hacia
afuera — cumple el principio sin ninguno de esos costos.

**Alternativas consideradas**: (a) mock de `smtplib` — rechazada, viola
Principio III; (b) `MailHog` — equivalente funcional, `mailpit` es su
sucesor mantenido; (c) probar contra Gmail real — rechazada por lo
anterior.

## Decisión 8 — Los tokens de un solo uso se guardan hasheados, y el correo lleva el valor en claro

**Decisión**: `tenants.token_acceso` almacena `hash_token` (Argon2id, el
mismo `hash_credencial` ya usado para contraseñas y API Keys), nunca el
token en claro. El valor en claro se genera con `secrets.token_urlsafe`,
viaja UNA vez dentro del enlace del correo y no se persiste en ningún
lado.

**Razón**: es el mismo modelo de amenaza que las API Keys ya resuelven en
este proyecto desde S1.2 (`tenants.api_key.hash_secreto`, con el secreto
en claro mostrado una sola vez). Un token de recuperación de contraseña
guardado en claro convierte cualquier lectura de la base —un volcado, un
snapshot de continuidad, un log— en una toma de control de cuentas.
Reutilizar el mecanismo existente evita inventar un segundo estándar de
almacenamiento de secretos en el mismo sistema.

**Consecuencia operativa**: no se puede "reenviar el mismo enlace" —
reenviar significa emitir un token nuevo e invalidar el anterior. Está
alineado con el caso borde de spec.md (solo el enlace más reciente sirve).

**Alternativas consideradas**: guardar el token en claro con acceso
restringido por `GRANT` — rechazada, la protección por rol de motor no
sobrevive a un volcado lógico ni a un snapshot de continuidad (ADR-018),
que por diseño copian todas las tablas.

## Decisión 9 — Alcance G1 de las tablas nuevas: tres `interno`, una `tenant`

**Decisión**: `sesion`, `token_acceso` e `intento_acceso` se registran con
alcance G1 `'interno'`; `invitacion` con alcance `'tenant'`.

**Razón**: las tres primeras se consultan **antes de saber quién es el
usuario** (validar una sesión, canjear un token, registrar un intento
fallido de un correo que quizá ni existe) — declararlas `'tenant'`
obligaría a envolver cada petición autenticada del sistema en
`alcance_global()`, convirtiendo la excepción nominal en la regla y
vaciando de sentido el guardián. Además, un usuario de plataforma
(`role_platform_admin`) tiene `tenant_id` NULL, así que su sesión no
podría portar el filtro que el alcance `'tenant'` exige. `invitacion`, en
cambio, siempre la crea un administrador ya autenticado dentro de su
propio tenant y siempre pertenece a uno — ahí el alcance `'tenant'` sí es
verificable y protege un dato real (a quién invitó cada organización).

**Alternativas consideradas**: declarar las cuatro `'tenant'` por
uniformidad — rechazada por lo anterior; declarar las cuatro `'interno'`
— rechazada, dejaría `invitacion` sin la protección que sí puede tener.

## Decisión 10 — Identificadores `RF-IA##` en el SRS, no `RF-O20+`

**Decisión**: los requisitos nuevos se numeran `RF-IA01`…`RF-IA08`
(familia "Identidad y Acceso") más `RNF-S06`, en vez de continuar la
secuencia `RF-O19 → RF-O20`.

**Razón**: el SRS reserva explícitamente `RF-O20`, `RF-O21` y `RF-O22` en
su **Apéndice A** como capacidades "cuya numeración normativa permanecía
en disputa", pendientes de confirmación formal. Usar esos identificadores
para requisitos de identidad rompería la trazabilidad de la errata abierta
y crearía una colisión con la fuente documental. El SRS ya establece el
precedente de familias editoriales claramente marcadas (RNF-R02–R04,
RNF-P01–P05, RNF-M01–M03, etc. son "identificadores editoriales acuñados
por el equipo, que no existen en el documento fuente") — `RF-IA##` sigue
esa misma convención, y se documenta como tal en la propia sección.

`RNF-S06` sí continúa la secuencia de seguridad (S01–S05 están tomados,
S06 está libre y no aparece en el Apéndice A).

**Alternativas consideradas**: (a) `RF-O20+` — rechazada por la colisión;
(b) meter todo dentro de `RNF-S01` (aislamiento) — rechazada, la
autenticación es capacidad funcional, no solo un atributo de calidad.

## Nota sobre el uso de Gmail (restricción operativa asumida)

El usuario eligió Gmail explícitamente. Se implementa, y se documenta en
`docs/runbooks/correo-smtp.md` lo que condiciona su uso real: exige una
**contraseña de aplicación** (Google retiró el acceso por contraseña
normal en 2022) y por tanto **segundo factor activo** en la cuenta
emisora; el cupo de envío ronda los 500 mensajes diarios en cuenta
personal y 2000 en Workspace; y la credencial es un secreto de entorno que
no entra al repositorio. Ninguno de esos límites bloquea el desarrollo ni
un piloto, pero sí harían inviable un despliegue con volumen real de
invitaciones — por eso el envío queda detrás del puerto de la Decisión 6,
para que migrar a un proveedor transaccional sea un adaptador nuevo y no
una reescritura.
