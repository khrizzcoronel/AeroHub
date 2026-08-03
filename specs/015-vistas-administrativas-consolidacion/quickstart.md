# Quickstart: validación de S1.13

Prerrequisito: stack en Docker, `docker compose up -d --build web`
(hallazgo de S1.11).

## Escenario 1 — Panel de facturas (US1)

1. Iniciar sesión, abrir `billing/facturas`, cargar facturas reales.
2. Verificar que cada factura aparece como `.ah-tira` con color según
   estado (pagada=verde, emitida=ámbar, vencida/disputada=rojo,
   borrador=neutro).
3. Ver el detalle de una factura y confirmar que las líneas de cargo
   usan `.ah-tabla`, con montos alineados en mono.
4. Emitir o disputar una factura (según su estado) y confirmar que la
   acción usa `.ah-campo`/`.ah-btn`.
5. Redimensionar a móvil, confirmar sin scroll horizontal.
6. Consola sin errores.

## Escenario 2 — Formulario de tenant (US2)

1. Con sesión de `role_platform_admin`, abrir el formulario de
   aprovisionamiento.
2. Confirmar que los campos usan `.ah-campo`, el botón `.ah-btn`.
3. Crear un tenant real y confirmar que el resultado (ids + contraseña
   temporal) se presenta con claridad dentro de un aviso.
4. Provocar un error (dato inválido) y confirmar `.ah-alerta`.
5. Redimensionar a móvil, confirmar sin scroll horizontal.

## Escenario 3 — Auditoría de las 8 vistas de S1.10 (US3)

1. Recorrer login, cambiar-password, recuperar, restablecer,
   verificar-correo, aceptar-invitacion, invitar y el shell.
2. Confirmar visualmente que cada una sigue coherente con los tokens y
   primitivos vigentes (color, tipografía, espaciado).
3. Corregir en el momento cualquier inconsistencia menor encontrada;
   documentar como hallazgo cualquier inconsistencia mayor sin
   resolverla en este sprint.
