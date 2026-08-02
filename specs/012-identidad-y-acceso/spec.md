# Feature Specification: Identidad y acceso

**Feature Branch**: `main`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Sprint S1.10 -- Identidad y acceso (login, registro por invitacion, verificacion de correo, menu por rol). Cerrar el hueco de autenticacion que el proyecto arrastra desde S1.1: hoy no existe login real (el JWT se pega a mano en un textarea), y un tenant no puede tener mas de un usuario en toda su vida. Alcance decidido con el usuario: email globalmente unico; un rol vigente por usuario; login + menu por rol + cambio de contrasena + invitaciones + verificacion de correo + recuperacion en un solo sprint. Correo por Gmail (SMTP) con puerto/adaptador. Toda la documentacion general debe quedar actualizada."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar sesión con credenciales propias (Priority: P1)

Una persona que ya tiene cuenta en la plataforma entra al portal, escribe su correo y su contraseña, y queda dentro de la aplicación trabajando con los datos de su organización — sin que nadie le tenga que entregar una credencial técnica por un canal ajeno al producto.

**Why this priority**: Es la puerta de entrada al sistema completo. Hoy el acceso depende de pegar a mano una credencial técnica generada fuera del producto, lo que hace imposible entregarlo a un usuario real. Ninguna otra historia de este sprint tiene sentido sin esta.

**Independent Test**: Puede probarse íntegramente creando una organización con su persona administradora, iniciando sesión con ese correo y contraseña, y verificando que a continuación se puede consultar un dato de negocio real de esa organización.

**Acceptance Scenarios**:

1. **Given** una persona con cuenta activa y contraseña válida, **When** inicia sesión con sus credenciales correctas, **Then** obtiene acceso a la aplicación y puede consultar datos de su propia organización.
2. **Given** una persona que escribe una contraseña incorrecta, **When** intenta iniciar sesión, **Then** el sistema rechaza el intento con un mensaje que **no** revela si el error fue el correo o la contraseña.
3. **Given** un correo que no existe en el sistema, **When** alguien intenta iniciar sesión con él, **Then** recibe exactamente el mismo mensaje de rechazo que ante una contraseña incorrecta.
4. **Given** varios intentos fallidos consecutivos sobre la misma cuenta, **When** se supera el límite establecido, **Then** la cuenta queda temporalmente bloqueada y los intentos posteriores se rechazan aunque la contraseña sea correcta.
5. **Given** un inicio de sesión exitoso, **When** se completa, **Then** queda registrada la marca de tiempo del último acceso de esa persona y el evento queda auditado.
6. **Given** una persona con cuenta suspendida, **When** intenta iniciar sesión con credenciales correctas, **Then** el acceso se rechaza.

---

### User Story 2 - Ver únicamente los módulos que me corresponden (Priority: P1)

Al entrar, cada persona ve en su menú solo los módulos que su rol le permite operar **y** que su organización tiene contratados — no una lista completa donde la mitad de las opciones fallan al hacer clic.

**Why this priority**: Es la otra mitad del MVP: sin esto, el inicio de sesión deja a la persona frente a una aplicación que no sabe quién es. Además cierra un hueco real: hoy no existe en ninguna parte del sistema una definición de qué módulos corresponden a cada rol.

**Independent Test**: Puede probarse iniciando sesión con dos personas de roles distintos en la misma organización y verificando que cada una ve un conjunto de módulos diferente; y con una organización a la que le falta la contratación de un módulo, verificando que ese módulo no aparece aunque el rol lo permitiera.

**Acceptance Scenarios**:

1. **Given** una persona autenticada con un rol determinado, **When** entra a la aplicación, **Then** su menú muestra exactamente los módulos que su rol puede operar y que su organización tiene contratados vigentes.
2. **Given** un módulo que el rol de la persona sí permitiría operar, **When** su organización no tiene ese módulo contratado, **Then** el módulo no aparece en su menú.
3. **Given** un módulo contratado por la organización, **When** el rol de la persona no lo contempla, **Then** el módulo no aparece en su menú.
4. **Given** dos personas de la misma organización con roles distintos, **When** ambas inician sesión, **Then** cada una ve el conjunto de módulos correspondiente a su propio rol.
5. **Given** una persona autenticada, **When** consulta su propio perfil de acceso, **Then** obtiene su identidad, su organización, su rol vigente y la lista de módulos visibles ya resuelta, sin tener que deducirla.

---

### User Story 3 - Cambiar la contraseña temporal en el primer acceso (Priority: P2)

Una persona a la que se le entregó una contraseña temporal al crear su organización debe establecer una contraseña propia antes de poder usar el sistema — la temporal no queda vigente para siempre.

**Why this priority**: Cierra un riesgo de seguridad concreto que el sistema ya tiene hoy: la contraseña temporal que se genera al dar de alta una organización nunca se cambia. Depende de que exista inicio de sesión (US1).

**Independent Test**: Puede probarse creando una organización, iniciando sesión con la contraseña temporal, verificando que cualquier otra acción está bloqueada hasta cambiarla, y confirmando que tras el cambio el sistema queda plenamente disponible.

**Acceptance Scenarios**:

1. **Given** una persona que inicia sesión por primera vez con una contraseña temporal, **When** intenta cualquier operación distinta de cambiar su contraseña, **Then** el sistema se lo impide e indica que debe cambiarla primero.
2. **Given** esa misma persona, **When** establece una contraseña nueva que cumple la política mínima, **Then** queda con acceso pleno y la obligación de cambio desaparece.
3. **Given** una persona que intenta fijar una contraseña que no cumple la política mínima, **When** la envía, **Then** el sistema la rechaza explicando qué requisito falta.
4. **Given** una persona que cambia su contraseña, **When** el cambio se completa, **Then** el evento queda auditado sin registrar en ningún momento la contraseña en claro.

---

### User Story 4 - Invitar personas a mi organización (Priority: P2)

Una persona administradora de una organización invita por correo a un colega indicando qué rol tendrá; el colega recibe un mensaje, establece su propia contraseña y queda operando dentro de esa organización.

**Why this priority**: Desbloquea una limitación estructural: hoy una organización queda con una única persona usuaria para siempre, porque no existe forma alguna de crear una segunda. Sin esto el producto no es utilizable por un equipo.

**Independent Test**: Puede probarse invitando a un correo desde una organización, siguiendo el enlace recibido, estableciendo una contraseña, e iniciando sesión con esa cuenta nueva para comprobar que ve los datos de esa organización y los módulos de su rol.

**Acceptance Scenarios**:

1. **Given** una persona administradora de una organización, **When** invita a un correo indicando un rol, **Then** se envía un mensaje a ese correo con un enlace de aceptación de un solo uso.
2. **Given** una persona que recibió una invitación, **When** sigue el enlace y establece su contraseña, **Then** queda con cuenta activa dentro de esa organización con el rol indicado.
3. **Given** una invitación ya aceptada, **When** se intenta usar el mismo enlace por segunda vez, **Then** el sistema lo rechaza.
4. **Given** una invitación cuyo plazo venció, **When** se intenta aceptar, **Then** el sistema la rechaza indicando que caducó.
5. **Given** una persona que no administra la organización, **When** intenta invitar a alguien, **Then** el sistema se lo impide.
6. **Given** un correo que ya pertenece a una cuenta existente en la plataforma, **When** se intenta invitarlo, **Then** el sistema rechaza la invitación indicando que ese correo ya está en uso.

---

### User Story 5 - Verificar que el correo es real (Priority: P3)

Una persona confirma que el correo con el que accede le pertenece, siguiendo un enlace de un solo uso que recibe en su bandeja.

**Why this priority**: Da confianza en que los correos operativos (recuperación de contraseña, avisos) llegan a una dirección real. Es deseable pero no bloquea la operación diaria.

**Independent Test**: Puede probarse solicitando la verificación de una cuenta, siguiendo el enlace recibido y comprobando que la cuenta queda marcada como verificada; y verificando que el mismo enlace no sirve una segunda vez.

**Acceptance Scenarios**:

1. **Given** una persona con correo sin verificar, **When** solicita la verificación, **Then** recibe un mensaje con un enlace de un solo uso.
2. **Given** ese enlace, **When** lo sigue dentro del plazo, **Then** su cuenta queda marcada como verificada con la fecha correspondiente.
3. **Given** un enlace ya usado o vencido, **When** se intenta usar, **Then** el sistema lo rechaza.

---

### User Story 6 - Recuperar el acceso si olvidé mi contraseña (Priority: P3)

Una persona que no recuerda su contraseña solicita recuperarla, recibe un enlace de un solo uso y establece una nueva sin depender de que alguien se la restablezca a mano.

**Why this priority**: Evita que cada olvido de contraseña se convierta en una intervención manual de soporte. Depende del envío de correo (compartido con US4/US5).

**Independent Test**: Puede probarse solicitando la recuperación de una cuenta, siguiendo el enlace, estableciendo una contraseña nueva e iniciando sesión con ella.

**Acceptance Scenarios**:

1. **Given** una persona con cuenta activa, **When** solicita recuperar su contraseña, **Then** recibe un mensaje con un enlace de un solo uso.
2. **Given** un correo que no corresponde a ninguna cuenta, **When** se solicita la recuperación, **Then** la respuesta es idéntica a la de un correo existente, sin revelar si la cuenta existe.
3. **Given** una persona que sigue el enlace y establece una contraseña nueva, **When** el cambio se completa, **Then** puede iniciar sesión con la nueva y **no** con la anterior.
4. **Given** una recuperación completada, **When** existían sesiones abiertas de esa persona, **Then** todas quedan invalidadas.
5. **Given** un enlace de recuperación ya usado o vencido, **When** se intenta usar, **Then** el sistema lo rechaza.

---

### User Story 7 - Cerrar sesión de verdad (Priority: P3)

Una persona cierra su sesión y a partir de ese momento su credencial de acceso deja de funcionar, sin tener que esperar a que caduque sola.

**Why this priority**: Completa el ciclo de vida de la sesión. Sin esto, "cerrar sesión" solo borraría la credencial del navegador mientras sigue siendo válida en el servidor.

**Independent Test**: Puede probarse iniciando sesión, cerrando sesión y comprobando que la credencial obtenida antes ya no permite consultar datos.

**Acceptance Scenarios**:

1. **Given** una persona con sesión abierta, **When** cierra sesión, **Then** su credencial deja de ser aceptada de inmediato.
2. **Given** una sesión ya cerrada, **When** se reintenta usar esa credencial, **Then** el sistema la rechaza.

---

### Edge Cases

- ¿Qué pasa si el servicio de correo no está disponible al invitar o al recuperar contraseña? La operación debe informar el fallo con claridad y no dejar registrada una invitación cuyo mensaje nunca llegará.
- ¿Qué pasa si una persona solicita recuperar su contraseña varias veces seguidas? Los enlaces anteriores dejan de ser válidos; solo el más reciente sirve.
- ¿Qué pasa si el plazo de una invitación vence sin aceptarse? La invitación queda caducada y la persona administradora puede emitir una nueva.
- ¿Qué pasa si una persona tiene más de un rol vigente asignado? Se trata como una inconsistencia de datos que debe reportarse explícitamente, nunca resolverse eligiendo uno en silencio.
- ¿Qué pasa si una persona no tiene ningún rol vigente (o todos vencieron)? No puede iniciar sesión y recibe un mensaje que lo indica sin exponer detalles internos.
- ¿Qué pasa con la cuenta bloqueada por intentos fallidos cuando la persona recuerda su contraseña? El bloqueo se levanta solo al cumplirse el plazo; no hay forma de saltárselo acertando la contraseña.
- ¿Qué pasa si la organización de una persona pierde la contratación de un módulo mientras tiene la sesión abierta? Su menú refleja el cambio al recargar su perfil de acceso o en el siguiente inicio de sesión; el acceso al módulo se rechaza aunque el menú aún lo muestre.
- ¿Qué pasa si dos personas distintas intentan usar el mismo correo? Solo una puede: el correo identifica de forma única a una persona en toda la plataforma.
- ¿Qué pasa con las cuentas ya existentes cuyo correo se repite entre organizaciones al aplicar la unicidad global? La migración debe detectar y reportar cualquier colisión antes de aplicarse, no fallar a mitad de camino.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir iniciar sesión presentando correo y contraseña, sin requerir ningún identificador adicional de la organización.
- **FR-002**: El sistema MUST identificar a cada persona por un correo único en toda la plataforma; un mismo correo no puede pertenecer a dos organizaciones distintas.
- **FR-003**: El sistema MUST rechazar credenciales inválidas con un mensaje idéntico tanto si el correo no existe como si la contraseña es incorrecta.
- **FR-004**: El sistema MUST bloquear temporalmente una cuenta tras un número definido de intentos fallidos consecutivos, y rechazar los accesos durante ese bloqueo aunque las credenciales sean correctas.
- **FR-005**: El sistema MUST limitar la frecuencia de intentos de inicio de sesión para dificultar ataques automatizados.
- **FR-006**: El sistema MUST registrar la marca de tiempo del último acceso exitoso de cada persona.
- **FR-007**: El sistema MUST determinar el rol vigente de la persona al iniciar sesión, respetando la fecha de expiración de la asignación de rol; si hay más de un rol vigente, MUST reportarlo como inconsistencia en vez de elegir uno.
- **FR-008**: El sistema MUST impedir el acceso a personas cuya cuenta no esté activa.
- **FR-009**: El sistema MUST exponer, para la persona autenticada, su identidad, su organización, su rol vigente y la lista de módulos visibles ya resuelta.
- **FR-010**: El sistema MUST calcular los módulos visibles como la intersección entre los módulos que el rol puede operar y los módulos con contratación vigente de la organización.
- **FR-011**: El sistema MUST mantener una definición explícita y versionada de qué módulos y permisos corresponden a cada rol.
- **FR-012**: El sistema MUST obligar a establecer una contraseña propia antes de permitir cualquier otra operación, cuando la persona todavía usa una contraseña temporal.
- **FR-013**: El sistema MUST rechazar contraseñas que no cumplan una política mínima definida, indicando qué requisito falta.
- **FR-014**: El sistema MUST asignar un rol a la persona administradora en el mismo acto de dar de alta una organización, de modo que pueda iniciar sesión desde el primer momento.
- **FR-015**: El sistema MUST permitir a una persona administradora de una organización invitar a otra por correo, indicando el rol que tendrá.
- **FR-016**: El sistema MUST impedir invitar a un correo que ya corresponda a una cuenta existente.
- **FR-017**: El sistema MUST enviar por correo electrónico los enlaces de invitación, verificación y recuperación.
- **FR-018**: El sistema MUST hacer que todo enlace de invitación, verificación o recuperación sea de un solo uso y tenga un plazo de vencimiento.
- **FR-019**: El sistema MUST permitir a la persona invitada establecer su contraseña y quedar activa en la organización con el rol indicado.
- **FR-020**: El sistema MUST permitir verificar la titularidad del correo y registrar la fecha de verificación.
- **FR-021**: El sistema MUST permitir solicitar la recuperación de contraseña, respondiendo de forma idéntica exista o no una cuenta con ese correo.
- **FR-022**: El sistema MUST invalidar todas las sesiones abiertas de una persona cuando su contraseña se restablece.
- **FR-023**: El sistema MUST permitir cerrar sesión, dejando la credencial inutilizable de inmediato y no solo al vencer su plazo.
- **FR-024**: El sistema MUST auditar todo evento de identidad —acceso exitoso, acceso fallido, cambio de contraseña, invitación emitida y aceptada, verificación, recuperación y cierre de sesión— sin registrar nunca contraseñas ni enlaces en claro.
- **FR-025**: El sistema MUST almacenar contraseñas y enlaces de un solo uso de forma irreversible, nunca en texto plano.
- **FR-026**: El sistema MUST permitir el acceso a las operaciones de inicio de sesión, recuperación, verificación y aceptación de invitación sin exigir una credencial previa.
- **FR-027**: La aplicación web MUST impedir el acceso a las vistas de negocio a quien no tenga sesión iniciada, redirigiéndolo a la pantalla de acceso.
- **FR-028**: La aplicación web MUST construir su menú a partir de los módulos visibles que le informa el sistema, sin duplicar la decisión de permisos.
- **FR-029**: La aplicación web MUST dejar de requerir que la persona usuaria introduzca manualmente una credencial técnica.

### Key Entities *(include if data involved)*

- **Persona usuaria (existente)**: identidad de acceso; correo único en la plataforma, credencial irreversible, estado, organización a la que pertenece, marca de verificación de correo, obligación de cambio de contraseña pendiente, bloqueo temporal vigente y último acceso.
- **Asignación de rol (existente)**: relación entre una persona y su rol, con vigencia y trazabilidad de quién la otorgó.
- **Sesión**: acceso vigente de una persona; permite invalidarlo antes de su vencimiento natural.
- **Enlace de un solo uso**: credencial temporal enviada por correo para invitación, verificación o recuperación; con tipo, vencimiento y marca de consumo, almacenada de forma irreversible.
- **Invitación**: propuesta de incorporación de una persona a una organización con un rol determinado; quién la emitió, a qué correo, su estado y vencimiento.
- **Intento de acceso**: registro de cada intento de inicio de sesión, base del bloqueo por intentos fallidos y evidencia de auditoría.
- **Correspondencia rol → módulos (nuevo, sin datos propios)**: definición explícita de qué módulos y permisos habilita cada rol.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona con cuenta puede entrar a la aplicación y operar sin recibir ninguna credencial técnica por un canal ajeno al producto.
- **SC-002**: El 100 % de los intentos con credenciales inválidas se rechaza con un mensaje indistinguible entre correo inexistente y contraseña incorrecta.
- **SC-003**: Tras el número definido de intentos fallidos consecutivos, el 100 % de los accesos posteriores a esa cuenta se rechaza durante el período de bloqueo.
- **SC-004**: El menú que ve cada persona coincide exactamente con la intersección entre lo que su rol permite y lo que su organización tiene contratado, verificado con al menos dos roles distintos y una organización sin contratación de un módulo.
- **SC-005**: Una organización puede pasar de una a varias personas usuarias sin intervención del equipo de plataforma.
- **SC-006**: Una persona invitada completa su incorporación —desde recibir el correo hasta operar en el sistema— en menos de 5 minutos.
- **SC-007**: El 100 % de los enlaces de un solo uso deja de funcionar tras su primer uso o al vencer su plazo.
- **SC-008**: Una persona que olvidó su contraseña recupera el acceso por sí misma, sin intervención manual de soporte.
- **SC-009**: Tras cerrar sesión o restablecer la contraseña, el 100 % de las credenciales previamente emitidas deja de ser aceptado.
- **SC-010**: El 100 % de los eventos de identidad queda auditado, y ninguna contraseña ni enlace aparece en claro en ningún registro.
- **SC-011**: Una persona autenticada nunca accede a datos de una organización distinta de la suya.

## Assumptions

- El alta de una organización nueva sigue siendo una operación del equipo de plataforma; **no** se habilita el registro público autoservicio de organizaciones en este alcance.
- Cada persona pertenece a una única organización. El correo la identifica de forma única en toda la plataforma, lo que exige migrar la restricción de unicidad hoy vigente (única por organización) a unicidad global — decisión tomada explícitamente con el usuario.
- Cada persona opera con un único rol vigente. La estructura de datos admite varios, pero este alcance trata más de uno como inconsistencia a reportar — decisión tomada explícitamente con el usuario.
- El envío de correo se realiza a través de una cuenta de Gmail mediante su servicio de correo saliente, elegido por el usuario. Se asume que ese canal es suficiente para el volumen de desarrollo y piloto; sus límites conocidos (cupo diario, credencial de aplicación específica y segundo factor obligatorio en la cuenta emisora) se documentan como restricción operativa, y el diseño mantiene el envío detrás de una frontera que permita sustituir el proveedor sin rehacer la funcionalidad.
- Las credenciales del servicio de correo se administran como secretos de entorno y nunca se incorporan al repositorio.
- La verificación de contratación de módulos por organización ya existe en el sistema y se reutiliza tal cual; este alcance no la redefine.
- La autenticación por segundo factor, el inicio de sesión federado con proveedores externos, la renovación de credenciales sin volver a autenticarse y el registro público autoservicio quedan **fuera de alcance**, cada uno como trabajo posterior independiente.
- El alcance incluye dejar registrada toda la funcionalidad nueva en la documentación normativa del proyecto (requisitos, decisión de arquitectura, modelo de datos, plan de implementación, guía operativa del correo y contrato de la interfaz), por pedido explícito del usuario.
