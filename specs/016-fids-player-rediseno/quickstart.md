# Quickstart: validación de S1.14

Prerrequisito: stack en Docker, `docker compose up -d --build gateway fids-player`
(hallazgo de S1.11: `fids-player/Dockerfile` copia en build-time, sin
volumen — un `restart` sirve el bundle viejo, hace falta `--build`).

Necesita un código de pantalla real y un token JWT con scopes
`fids:leer`, `fids:heartbeat` (emitido para un usuario de un tenant con
M2 licenciado) y al menos una plantilla activa asignada a esa pantalla
(ver `specs/005-fids-plantillas-pantallas/` para cómo sembrar una).

## Escenario 1 — Legibilidad del contenido en modo reproducción (US1)

1. Abrir `fids-player`, completar el formulario de configuración con el
   código y token reales, conectar.
2. Confirmar que la transición a modo `reproduccion` es completa (el
   formulario de configuración deja de ser visible por completo).
3. Confirmar que el contenido de la plantilla activa se lee sin
   acercarse a la pantalla (alejarse físicamente 3+ metros del monitor,
   o reducir el zoom del navegador a un tamaño equivalente).
4. Confirmar que no aparece ningún botón, campo de formulario, ni tabla
   administrativa en este modo.
5. Publicar una actualización de plantilla (vía el flujo de S1.3,
   `services/fids`) y confirmar que el contenido se actualiza sin
   parpadeo ni recarga de página.
6. Asignar una plantilla con `definicion_json` que NO siga la
   convención `filas: [{texto}]` (por ejemplo `{"otra_forma": true}`) y
   confirmar que se muestra un respaldo legible, no la estructura JSON
   cruda.

## Escenario 2 — Modo de configuración distinto del de reproducción (US2)

1. Recargar `fids-player` sin conectar aún — confirmar que el modo
   `configuracion` se ve claramente distinto del modo `reproduccion`
   (otra composición, no un formulario flotando sobre contenido).
2. Intentar conectar con un código o token inválido — confirmar que el
   error se muestra dentro del mismo modo `configuracion`, sin
   transicionar a `reproduccion`.
3. Conectar con datos válidos — confirmar la transición completa a
   `reproduccion`.

## Escenario 3 — Detección y recuperación de "sin señal" (US3)

1. Con la pantalla en modo `reproduccion`, cerrar la conexión de red del
   contenedor `fids-player` hacia `gateway` (o detener el contenedor
   `gateway` brevemente) para forzar el cierre anómalo del WebSocket.
2. Confirmar que, dentro de ≤ 30s, la pantalla transiciona a un modo
   `sin_senal` visualmente propio (no el modo `configuracion`, no un
   texto de error sobre el contenido anterior).
3. Restablecer la conexión (reiniciar `gateway`) y confirmar que la
   pantalla vuelve automáticamente a `reproduccion` sin ninguna acción
   manual, en cuanto llega el siguiente heartbeat exitoso o una
   plantilla nueva.
4. Repetir un corte de red de duración menor a 15s (un solo ciclo de
   heartbeat) y confirmar que el modo `sin_senal` NO llega a mostrarse
   de forma perceptible.

## Verificación transversal

- Consola del navegador sin errores en los tres modos.
- Build de producción de `fids-player` en verde
  (`nx build fids-player --configuration=production`).
- Con este sprint cerrado, no queda ninguna vista sin estilo en
  `apps/web` ni en `apps/fids-player` (cierre del rediseño S1.11-S1.14).
