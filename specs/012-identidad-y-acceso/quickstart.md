# Quickstart: validación de S1.10

Prerrequisito: stack en Docker, incluido el servidor SMTP de prueba nuevo:

```bash
docker compose -f infra/docker-compose.yml up -d monetdb mailpit gateway web
```

DDL aplicado, incluidos `16_identidad.sql` y la migración
`17_migracion_email_unico.sql`. Seeds ejecutados (los usuarios canario
ahora reciben rol, ver US1).

Bandeja de correo de prueba: interfaz web de `mailpit` en `:8025`.

## Escenario 1 — Iniciar sesión y operar (US1)

1. Crear un tenant (`POST /tenants` con un token de `role_platform_admin`)
   y anotar el `password_temporal` que devuelve.
2. `POST /auth/login` con el correo del admin y esa contraseña temporal →
   `200` con token y `debe_cambiar_password: true`.
3. Repetir el login con una contraseña incorrecta → `401`. Repetirlo con
   un correo inexistente → **`401` con el mismo cuerpo exacto**.
4. Fallar el login N veces seguidas → la cuenta queda bloqueada; el
   siguiente intento **con la contraseña correcta** también falla.
5. Verificar en `tenants.intento_acceso` que quedaron registrados los
   intentos con su `resultado` real (distinto por caso, a diferencia de la
   respuesta HTTP).

## Escenario 2 — Menú por rol × licencia (US2)

1. `GET /auth/yo` con el token del paso anterior → devuelve rol, scopes y
   `modulos_visibles`.
2. Retirar la licencia de un módulo del tenant (p. ej. M5) y repetir →
   ese módulo **desaparece** de `modulos_visibles` aunque el rol lo
   permita.
3. Invitar a un usuario con un rol más restringido (ver Escenario 4),
   iniciar sesión con él y comparar: su `modulos_visibles` es un
   subconjunto distinto.
4. Abrir `web` en el navegador: el menú lateral muestra exactamente esos
   módulos, ni uno más.

## Escenario 3 — Cambio obligatorio de contraseña (US3)

1. Con la sesión del admin recién creado (`debe_cambiar_password: true`),
   llamar a cualquier endpoint de negocio → `403` indicando que debe
   cambiar la contraseña.
2. `POST /auth/cambiar-password` con una contraseña que no cumple la
   política → `422` indicando el requisito que falta.
3. Repetir con una válida → `200`; ahora los endpoints de negocio
   responden normalmente y `GET /auth/yo` reporta
   `debe_cambiar_password: false`.

## Escenario 4 — Invitar a un colega (US4)

1. `POST /usuarios/invitaciones` con un correo nuevo y un `rol_codigo`
   → `201`.
2. Abrir `mailpit` (`:8025`) y comprobar que llegó el correo de
   invitación con su enlace.
3. `POST /usuarios/aceptar-invitacion` con el token del enlace, un nombre
   y una contraseña → `201`.
4. Iniciar sesión con esa cuenta nueva → funciona, y `GET /auth/yo`
   muestra el tenant correcto y el rol invitado.
5. Reintentar la aceptación con el **mismo** token → `410`.
6. Invitar a un correo que ya existe → `409`.
7. Intentar invitar desde un usuario que no es `role_tenant_admin` →
   `403`.

## Escenario 5 — Verificar correo (US5)

1. `POST /auth/solicitar-verificacion` autenticado → `202`; el correo
   aparece en `mailpit`.
2. `POST /auth/verificar-correo` con el token → `200`; `GET /auth/yo`
   reporta `email_verificado: true`.
3. Reusar el token → `410`.

## Escenario 6 — Recuperar contraseña (US6)

1. `POST /auth/recuperar` con un correo existente → `202`, correo en
   `mailpit`.
2. `POST /auth/recuperar` con un correo **inexistente** → `202` idéntico,
   sin correo enviado.
3. `POST /auth/restablecer` con el token y una contraseña nueva → `200`.
4. Iniciar sesión con la contraseña nueva → funciona; con la anterior →
   `401`.
5. Comprobar que un token de sesión obtenido **antes** del
   restablecimiento ya no es aceptado (FR-022).

## Escenario 7 — Cerrar sesión de verdad (US7)

1. Iniciar sesión y guardar el token.
2. `POST /auth/logout` → `200`.
3. Reutilizar ese mismo token contra un endpoint de negocio → rechazado,
   sin esperar a que venza.

## Escenario 8 — Aislamiento con sesión real (regresión PN-01)

1. Iniciar sesión con el usuario canario de MEC y con el de UIO.
2. Con la sesión de UIO, pedir un recurso creado por MEC → `404`, nunca
   `403` ni el dato.

Es la primera vez que PN-01 se prueba con una sesión obtenida por **login
real** y no con un token fabricado en el propio test.
