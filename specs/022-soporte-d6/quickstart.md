# Quickstart: Soporte D6

Validación manual de los 3 escenarios de `spec.md`, sin backend nuevo
que levantar (los 11 endpoints ya corren desde S1.8).

## Prerrequisitos

```bash
docker compose -f infra/docker-compose.yml up -d monetdb gateway web
uv run python -m db.seeds.generate   # dentro de un contenedor con uv, si no hay datos canario
```

Tenants canario: `MEC`/`UIO`. Rol para probar el flujo completo:
`role_support` (ve todos los tenants, puede marcar mensajes internos).

## Escenario 1 — Bandeja de tickets con SLA y conversación (US1)

1. Iniciar sesión con un usuario `role_support`.
2. Abrir el enlace "Soporte" del menú lateral (`/soporte/panel`).
3. Crear un ticket (severidad `alta`) si no hay ninguno abierto.
4. Confirmar que la bandeja muestra severidad, estado `abierto` y el
   indicador de SLA (tiempo restante, calculado desde `creado_en` +
   `sla_objetivo_min`).
5. Abrir el ticket, responder con un mensaje visible y luego con un
   mensaje marcado "interno" -- confirmar que se distinguen
   visualmente.
6. Intentar cambiar el estado directo a `resuelto` -- confirmar que la
   interfaz solo ofrece `en_progreso` como siguiente estado válido.
7. Cambiar a `en_progreso`, luego a `resuelto`, luego a `cerrado` --
   confirmar que la bandeja refleja cada cambio.

**Resultado esperado**: el ticket queda `cerrado`, el hilo muestra 2
mensajes (uno interno, distinguible), y en ningún momento se pegó un
JWT ni una petición HTTP a mano.

## Escenario 2 — Base de conocimientos compartida (US2)

1. En el mismo panel, ir a la sección "Base de conocimientos".
2. Confirmar que hay un aviso visible de que el contenido es
   compartido entre tenants.
3. Publicar un artículo con título, cuerpo y al menos una etiqueta.
4. Buscarlo por una palabra del título -- debe aparecer.
5. Buscarlo por la etiqueta -- debe aparecer.
6. Iniciar sesión con un usuario de otro tenant (`role_tenant_admin`
   de `UIO`) y confirmar que el mismo artículo es visible (prueba
   directa de que no está aislado por tenant).

**Resultado esperado**: el artículo es visible para ambos tenants sin
ninguna configuración adicional.

## Escenario 3 — Changelog publicable (US3)

1. En el panel, ir a la sección "Changelog".
2. Publicar una entrada con versión de producto, resumen y un ítem
   (módulo M1, tipo `mejora`).
3. Confirmar que aparece en el listado, más reciente primero, con su
   ítem visible.
4. Iniciar sesión con cualquier rol que tenga `support:leer` (p. ej.
   `role_tenant_admin`) y confirmar que ve el mismo listado sin poder
   publicar una entrada nueva (control de escritura oculto).

**Resultado esperado**: el changelog es de lectura universal (dentro
de quienes tienen `support:leer`) y de escritura restringida.

## Notas

- No se verifica en navegador real de forma automática -- regla
  vigente desde S1.16. Estos pasos son para cuando el usuario pida la
  verificación explícitamente.
- La verificación empírica obligatoria de este sprint (Principio III)
  se cubre con `tests/integration/test_soporte_hub.py` contra MonetDB
  real, no con este quickstart.
