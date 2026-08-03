# Quickstart: validación de S1.11

Prerrequisito: stack en Docker.

```bash
docker compose -f infra/docker-compose.yml up -d monetdb gateway web
```

Iniciar sesión con un usuario canario (`canario@mec.aerohub.test` /
`canario-dev-password`, S1.10) antes de cada escenario.

## Escenario 1 — Vista canónica en tiempo real (US1)

1. Abrir `vuelos/estado-tiempo-real` con sesión iniciada.
2. Confirmar que la conexión se establece SIN ningún campo de token
   visible en la pantalla.
3. Provocar un cambio de estado del vuelo canario contra el backend real
   (p. ej. `PATCH` del estado vía la API de AODB con el token de la
   propia sesión) y confirmar que aparece una tira nueva arriba de las
   anteriores, con código de vuelo/ruta/puerta/hora/estado en columnas
   alineadas (mono) y la barra de color correspondiente al tipo de
   estado.
4. Repetir con 2-3 cambios de estado distintos y confirmar el orden
   (más reciente arriba) y que el color de la barra corresponde al
   semáforo correcto para cada estado.
5. Redimensionar la ventana a un ancho móvil típico y confirmar que el
   contenido sigue siendo legible sin scroll horizontal.
6. Navegar solo con teclado (Tab) por los controles de conectar/
   desconectar y confirmar que el foco es visible en todo momento.
7. Activar `prefers-reduced-motion` en el sistema operativo/navegador y
   confirmar que el cambio de color de la barra ya no transiciona (salto
   instantáneo).
8. Abrir la consola del navegador y confirmar ausencia de errores.

## Escenario 2 — Sin token manual en las 4 vistas (US2)

1. Abrir `vuelos/estado-tiempo-real`, `billing/panel-facturas`,
   `rampa/panel-turnaround` y `puertas/tablero-puertas` con sesión
   iniciada — ninguna de las 4 muestra un campo para pegar un token.
2. Ejercitar una acción de cada una que llame al backend (listar
   facturas, listar turnarounds, obtener el tablero de puertas, conectar
   el WS de vuelos) y confirmar que todas funcionan sin pedir nada de
   autenticación adicional.
3. Cerrar sesión (`AuthService.logout()` desde el shell) y volver a abrir
   cualquiera de las 4 vistas — se redirige a `/login`, igual que el
   resto de la aplicación desde S1.10.
4. Grep de control: `tokenJwt` no aparece como parámetro/signal en
   `estado-tiempo-real.ts`, `billing.service.ts`, `rampa.service.ts`,
   `puertas.service.ts`, ni en los componentes que antes lo pasaban.
