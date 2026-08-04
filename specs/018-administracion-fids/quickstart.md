# Quickstart: validación de S1.16

Prerrequisito: stack en Docker,
`docker compose up -d --build gateway web fids-player` (hallazgo de
S1.11: los `Dockerfile` copian en build-time, `--build` es obligatorio).

Necesita iniciar sesión con `role_tenant_admin` (research.md Decisión 1:
sin el fix de scopes, cualquier intento en esta vista devuelve 403).

## Escenario 1 — Publicar plantilla y registrar pantalla (US1 + US2)

1. Abrir `FIDS Management` desde el menú (entrada nueva — antes M2 no
   aparecía en ningún lado).
2. En la sección de plantillas, publicar una plantilla nueva con un
   `definicion_json` válido (ej. `{"filas": [{"texto": "Prueba S1.16"}]}`).
3. Confirmar que aparece en la tabla y en el `<select>` de plantilla de
   la sección de pantallas.
4. Registrar una pantalla nueva, seleccionando terminal (si el catálogo
   está vacío, ver Escenario 3) y la plantilla recién creada.
5. Confirmar que el código generado se muestra en un aviso copiable.

## Escenario 2 — Conectar el reproductor y reasignar plantilla (US1 + US3)

1. Copiar el código de la pantalla del Escenario 1.
2. Abrir `apps/fids-player`, completar el formulario de configuración
   con ese código y un token JWT válido (scopes `fids:leer`,
   `fids:heartbeat`).
3. Confirmar que el reproductor conecta y muestra el contenido de la
   plantilla asignada.
4. Volver a la vista administrativa, publicar una plantilla nueva, y
   reasignarla a la misma pantalla.
5. Confirmar que el reproductor, sin recargar ni reconectar, actualiza
   su contenido al de la plantilla nueva (WebSocket ya construido en
   S1.3, RNF-P02).

## Escenario 3 — Telemetría y catálogo de terminales incompleto (US1)

1. Confirmar que la tabla de pantallas muestra el estado real (`en
   línea` tras el primer heartbeat del reproductor conectado en el
   Escenario 2) y la fecha de última señal.
2. Si el `<select>` de terminal aparece vacío al registrar una pantalla,
   confirmar que la vista lo indica con un estado vacío explícito, no
   con un select silenciosamente sin opciones (research.md Decisión 4 —
   riesgo de datos conocido, no un defecto de este sprint).

## Verificación transversal

- Consola del navegador sin errores.
- `ruff`/`mypy`/`bandit`/`import-linter` en verde sobre `services/fids`.
- `pytest` de integración nuevo en verde contra MonetDB real.
- Build de producción de `apps/web` en verde.
- `role_tenant_admin` ve "FIDS Management" en el menú; un rol sin
  `fids:*` (ej. `role_billing_officer`) no lo ve y recibe 403 si accede
  la ruta directamente.
