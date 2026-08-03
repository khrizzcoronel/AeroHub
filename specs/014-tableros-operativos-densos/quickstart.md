# Quickstart: validación de S1.12

Prerrequisito: stack en Docker (`monetdb`, `gateway`, `web`), sesión
iniciada con un usuario que tenga M3/M4 visibles (p. ej.
`canario@mec.aerohub.test`, `role_tenant_admin`).

Recordar el hallazgo de S1.11: `apps/web/Dockerfile` copia el código en
build-time — usar `docker compose up -d --build web`, un `restart` sirve
el bundle viejo.

## Escenario 1 — Tablero de puertas (US1)

1. Abrir `puertas/tablero`, cargar el tablero real.
2. Verificar que cada puerta aparece como una tira (barra de color +
   datos en mono), no como una sección con tabla cruda.
3. Asignar dos vuelos a la misma puerta con ventanas de tiempo
   superpuestas (vía el propio formulario de asignación manual, o
   verificando datos ya sembrados que se solapen) y confirmar que esa
   puerta pasa a color crítico.
4. Confirmar que una puerta sin asignaciones se ve en color neutro, y una
   con una única asignación vigente en color satisfactorio.
5. Confirmar que el resultado de la asignación automática y cualquier
   error usan el mismo tratamiento de aviso que el resto de la app.
6. Redimensionar a ancho móvil y confirmar que no hay scroll horizontal.
7. Navegar solo con teclado y confirmar foco visible en todos los
   controles.
8. Consola del navegador sin errores.

## Escenario 2 — Panel de turnaround (US2)

1. Abrir `rampa/turnaround`, cargar los turnarounds reales.
2. Verificar que cada turnaround aparece como una tira con color según
   su estado (interrumpido → crítico, completado/en_curso → ok,
   planificado → neutro; en_curso vencido → atención).
3. Seleccionar un turnaround con tareas reales y confirmar que se listan
   en una tabla densa con su estado resaltado.
4. Seleccionar uno sin tareas propias (o ninguna existente) y confirmar
   que el mensaje real de mínimo privilegio se conserva, con tratamiento
   de estado vacío.
5. Cargar incidencias reales y confirmar que la severidad se distingue
   por color, no solo por texto (`alta`/`critica` en rojo, `media` en
   ámbar, `baja` en neutro).
6. Redimensionar a ancho móvil, confirmar sin scroll horizontal.
7. Navegar solo con teclado (cargar, seleccionar turnaround, iniciar
   tarea, finalizar tarea) con foco siempre visible.
8. Consola del navegador sin errores.

## Escenario 3 — Coherencia con la vista canónica (SC-005)

1. Con las tres vistas abiertas en pestañas distintas (`vuelos/tiempo-
   real`, `puertas/tablero`, `rampa/turnaround`), confirmar visualmente
   que las tiras de las tres comparten el mismo componente (barra de
   4px, mono para dato, mismo alto de fila) y la misma paleta de
   semáforo.
