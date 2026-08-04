# Research: Contrato de API y superficie del AODB (S1.15)

## Decisión 1 — El generador de OpenAPI ya existe; el gap era la compuerta, no el generador

**Decisión**: reutilizar `tools/generar_openapi.py` tal cual (construido en
S1.2, `crear_app().openapi()` volcado a YAML) para regenerar
`docs/api/openapi.yaml`. El trabajo real de este sprint es agregar un paso
nuevo al job `contrato-api` de `.github/workflows/ci.yml` que genera el
esquema a un archivo temporal y falla si difiere del comiteado.

**Razón**: el hallazgo de la auditoría (`ANALISIS_RUMBO_Y_BRECHAS_2026-08.md`)
no fue "falta un generador" -- es que el generador existente nunca se volvió
a correr después del workpanel de tenants/usuarios/api-keys/licencias
(2026-08-02 en adelante), y nada en CI lo habría detectado porque Spectral
solo valida que el YAML sea sintácticamente correcto, no que coincida con
el backend real.

**Alternativas consideradas**: escribir un generador nuevo -- rechazado,
sería reconstruir algo que ya funciona; mantener el archivo a mano con
disciplina de revisión -- rechazado, es exactamente el proceso que ya
falló una vez.

## Decisión 2 — Los catálogos de aerolínea/aeronave/tipo de vuelo no existen como endpoint; hace falta agregarlos

**Decisión**: agregar `GET /vuelos/catalogo/aerolineas`,
`/aeronaves` y `/tipos-vuelo` en `services/aodb`, redeclarando
`catalogo.aerolinea`/`catalogo.aeronave`/`catalogo.modelo_aeronave`/
`catalogo.tipo_vuelo` de solo lectura en `aerohub_aodb/infrastructure/`
-- mismo patrón que `consultas_catalogo.py` de `aerohub_tenancy` sobre
`catalogo.aeropuerto` (independencia de módulos, ADR-017 §5.4: cada
módulo redeclara la tabla ajena en vez de importarla).

**Razón**: `spec.md` FR-010 exige explícitamente que ninguna vista de este
sprint obligue a pegar un id técnico a mano. El formulario de alta de vuelo
necesita `aerolinea_id`, `aeronave_id` y `tipo_vuelo_id` -- sin un
`<select>` poblado, la única alternativa sería un campo de texto libre con
el id Snowflake, que es justamente el patrón que el proyecto abandonó en
S1.10/S1.13 para tenants.

**Corrección post-verificación empírica (Principio III)**: esta decisión
asumió originalmente que `aeropuerto_origen_id`/`aeropuerto_destino_id`
podían reutilizar `GET /catalogo/aeropuertos` de `aerohub_tenancy` sin
endpoint nuevo, razonando que es "una llamada HTTP del frontend, no un
import de Python" -- arquitectónicamente correcto, pero **sin verificar el
scope real del endpoint**. Al probar en navegador real con
`role_tenant_admin`, `GET /catalogo/aeropuertos` devolvió 403 (exige
`tenants:crear`, exclusivo de `role_platform_admin` -- es el endpoint que
sirve el formulario de alta de tenant, no un catálogo operativo general),
y el interceptor HTTP lo tradujo en un logout forzado. Se agregó un cuarto
endpoint, `GET /vuelos/catalogo/aeropuertos` en `aerohub_aodb` (misma
redeclaración local de `catalogo.aeropuerto`, protegido por
`vuelos:leer`), en vez de relajar el scope del endpoint de tenancy --
tocar ese scope es una decisión de seguridad de otro módulo, fuera de
alcance de este sprint.

**Grants ya cubiertos**: `db/ddl/monetdb/91_grants_catalogo.sql` ya otorga
`SELECT` sobre las 4 tablas a `role_operations_controller` (entre otros) --
no hace falta DDL nuevo, es dato de solo lectura ya accesible por el rol.

**Alternativas consideradas**: pedir los 3 ids como texto libre y validar
solo en el backend -- rechazado explícitamente por FR-010; construir un
único endpoint "catálogos combinados" -- rechazado, mezclaría 3 entidades
sin relación jerárquica real en una sola respuesta, dificultando el cache
y la reutilización individual de cada lista.

## Decisión 3 — Alta de vuelo y cambio de estado se resuelven con modales, no con navegación a otra ruta

**Decisión**: en `vuelos/estado-tiempo-real`, un botón "Nuevo vuelo" abre
un modal (`.ah-modal-fondo`/`.ah-modal`) con el formulario de alta; cada
fila de la tabla gana una acción "Cambiar estado" que abre un segundo
modal con el `<select>` de estados válidos. Ninguno de los dos navega a
una ruta separada.

**Razón**: es el mismo patrón ya consolidado en `tenants/tenant-list`,
`usuarios/usuario-list` y las 4 vistas operativas migradas a tabla el
2026-08-04 (`PLAN_WORKPANELS_MODULOS.md` §3.0) -- una vista nueva que
navegara a otra ruta rompería la consistencia recién lograda entre las
9 vistas de `apps/web`.

**Sobre las transiciones de estado válidas**: el dominio
(`aerohub_aodb/domain/estado.py`) valida las transiciones en el backend
(`TransicionEstadoInvalida` → 409); el modal de cambio de estado no
necesita replicar esa máquina de estados en el cliente como hacen
`tenant-list`/`usuario-list` con `transicionesDisponibles()` -- a
diferencia de tenant/usuario (catálogo cerrado y pequeño, 3-4 estados),
`catalogo.estado_vuelo_catalogo` es un dominio abierto (ver comentario en
`domain/tenant.py`), así que el `<select>` ofrece los 6 códigos de estado
conocidos (mismo catálogo que ya usa `estado-tiempo-real.ts::ETIQUETAS_ESTADO`
desde S1.14) y deja que el backend rechace la transición inválida con 409,
mostrado como error de formulario -- más simple y no requiere duplicar la
máquina de estados en el cliente.

**Alternativas consideradas**: ruta separada `/vuelos/nuevo` -- rechazada
por romper la consistencia del patrón modal ya establecido; replicar la
máquina de transiciones en el cliente -- rechazada, el catálogo de estados
es abierto y el backend ya es la fuente de verdad de qué transición es
válida.

## Decisión 4 — "Reenviar verificación" vive en el shell, no en la vista pública de verificación

**Decisión**: `POST /auth/solicitar-verificacion` no recibe ningún
parámetro -- opera sobre `contexto_usuario_id()` de la sesión ya
autenticada (`aerohub_tenancy/application/verificar_correo.py`). La vista
`auth/verificar-correo` (ruta pública `/verificar-correo?token=...`) NO
tiene sesión: es la página que consume el enlace del correo, alcanzable
sin haber iniciado sesión. Por lo tanto la acción de reenvío no puede vivir
ahí -- se agrega como un banner condicional en el shell
(`perfil().email_verificado === false`), visible para cualquier persona ya
autenticada con el correo pendiente de verificar.

**Razón**: es una corrección de alcance respecto a la redacción original de
`spec.md` US3 ("vista de verificación existente"), que asumía sin verificar
que el endpoint podía invocarse sin sesión. Verificado leyendo
`verificar_correo.py::solicitar_verificacion()` antes de diseñar la UI --
exactamente el tipo de chequeo que el Principio III pide hacer antes de
construir, no después.

**Alternativas consideradas**: agregar un parámetro de correo al endpoint
para permitir el reenvío sin sesión -- rechazado, es un cambio de contrato
de backend fuera del alcance declarado del sprint (`spec.md` Assumptions:
"no se construye backend nuevo salvo lo estrictamente necesario", y este
endpoint YA es consumible tal cual está).

## Decisión 5 — El id de vuelo nunca se pega a mano para cambiar su estado

**Decisión**: la acción "Cambiar estado" de cada fila de la tabla pasa el
`vuelo_id` del registro ya cargado en memoria (signal), igual que
`tenant-list`/`usuario-list` pasan el id de la fila al abrir su modal --
nunca se le pide a la persona que lo escriba.

**Razón**: cierre explícito de FR-010, y consistencia con el patrón ya
establecido en las demás vistas administrativas.
