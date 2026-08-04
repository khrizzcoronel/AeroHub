# Quickstart: validación de S1.15

Prerrequisito: stack en Docker,
`docker compose up -d --build gateway web` (hallazgo de S1.11: el
`Dockerfile` de `web` copia en build-time, un `restart` sirve el bundle
viejo).

## Escenario 1 — Contrato de API regenerado (US2)

1. Ejecutar `uv run python tools/generar_openapi.py` dentro del
   contenedor `gateway` (o `docker cp` el resultado) y confirmar que
   `docs/api/openapi.yaml` ahora incluye las rutas del workpanel de
   usuarios/tenants/api-keys/licencias (`/usuarios/{usuario_id}`,
   `/tenants/validar`, `/licencias/mi-tenant`, etc.), ausentes antes de
   este sprint.
2. Correr `npx spectral lint docs/api/openapi.yaml --fail-severity=error`
   y confirmar que sigue en verde (la regeneración no rompe la validez
   sintáctica).
3. Agregar una ruta de prueba temporal al backend, NO regenerar el
   archivo, y confirmar que el nuevo paso de CI (diff contra el
   generado) falla explícitamente. Revertir la ruta de prueba.

## Escenario 2 — Alta, consulta y cambio de estado de vuelo (US1)

1. Iniciar sesión con un usuario `role_operations_controller`, abrir
   `vuelos/tiempo-real`.
2. Abrir el modal "Nuevo vuelo": confirmar que aerolínea, aeronave, tipo
   de vuelo y aeropuertos de origen/destino se seleccionan de una lista,
   no se escriben como id.
3. Completar y enviar el formulario -- confirmar que el vuelo queda
   visible en la tabla de inmediato.
4. Sobre ese vuelo, abrir "Cambiar estado", seleccionar un estado válido
   -- confirmar que se refleja tanto en la fila de la tabla como en el
   WebSocket de tiempo real, sin recargar la página.
5. Intentar una transición inválida (por ejemplo, sobre un vuelo ya
   `aterrizado`) -- confirmar que el rechazo (409) se muestra como error
   de formulario, no como excepción sin manejar.
6. Confirmar que los ids Snowflake (aerolínea, aeronave, vuelo) viajan
   como string en las peticiones -- inspeccionar el payload real en las
   herramientas de red del navegador.

## Escenario 3 — Endpoints huérfanos (US3)

1. En `puertas/tablero`, abrir "Ver asignaciones" de una puerta con una
   asignación activa, cancelarla, y confirmar que la puerta vuelve a
   mostrarse libre en el tablero.
2. Con una cuenta cuyo correo no esté verificado, confirmar que el shell
   muestra un banner con la acción de reenviar verificación; solicitarlo
   y confirmar que llega un correo nuevo (verificar en Mailpit/SMTP de
   desarrollo).
3. Con una cuenta ya verificada, confirmar que el banner NO aparece.

## Verificación transversal

- Consola del navegador sin errores en los tres escenarios.
- `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre
  `services/aodb` (las tablas de catálogo redeclaradas no deben violar
  la independencia de módulos).
- `pytest` de `services/aodb` en verde, incluida cobertura de las 3
  consultas de catálogo nuevas.
- Build de producción de `apps/web` en verde.
