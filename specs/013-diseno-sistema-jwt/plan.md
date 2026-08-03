# Implementation Plan: Sistema de diseño + deuda de JWT + vista canónica

**Branch**: `main` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/013-diseno-sistema-jwt/spec.md`

## Summary

Extiende el sistema de tokens ya creado en S1.10 (`apps/web/src/styles.scss`,
`_auth-form.scss`) con el semáforo operacional y la tipografía mono para
dato, y agrega los primitivos compartidos (`.ah-tira`, `.ah-tabla`,
`.ah-vacio`) que el resto del rediseño (S1.12-S1.14) reutilizará. Los
prueba en un único consumidor real: `vuelos/estado-tiempo-real` (M1),
que pasa de HTML crudo a la consola densa que define el patrón "tira".
En paralelo, cierra la deuda del JWT manual en las 4 vistas que todavía
lo piden — 3 de ellas (facturas, turnaround, tablero de puertas) solo
pierden el textarea, sin rediseño visual (eso es S1.12/S1.13).

## Technical Context

**Language/Version**: TypeScript/Angular 22 (frontend únicamente — sin
cambios de backend en este sprint)

**Primary Dependencies**: Angular standalone components/signals ya
establecidos desde S1.1; `HttpClient` + `authInterceptor` (S1.10); fuente
tipográfica IBM Plex Sans/Mono ya cargada desde S1.10 (ver
`apps/web/src/index.html` — verificar si Mono ya está enlazada o falta
agregar el peso faltante).

**Storage**: N/A — sin cambios de esquema ni de API en este sprint.

**Testing**: verificación manual en navegador real contra el backend real
en Docker (Principio III) — WebSocket de vuelos real, sin mocks; recorrido
de teclado; `prefers-reduced-motion`; escritorio y móvil (ver
[quickstart.md](./quickstart.md)). Sin tests automatizados de UI nuevos
(el proyecto no tiene suite de tests de frontend hasta la fecha; no se
introduce una para un sprint de estilo).

**Target Platform**: navegador (Chrome/Firefox de escritorio y viewport
móvil), servido por el contenedor `web` de `infra/docker-compose.yml`.

**Performance Goals**: la transición de color de estado (FR-006) debe
percibirse pero no demorar la lectura — 150ms fija (research.md Decisión 4),
sin animación adicional.

**Constraints**: no se toca el backend ni el contrato de `GET /auth/yo`
(ya devuelve todo lo necesario desde S1.10, incluida la lista de módulos
visibles usada por el shell). El WebSocket de vuelos (`/vuelos/ws/estado`)
no pasa por `HttpClient`, así que `authInterceptor` no le aplica — se
resuelve leyendo el token ya guardado en `AuthService.token()` en vez de
pedirlo a la persona usuaria (research.md Decisión 3).

**Scale/Scope**: 1 archivo de tokens ampliado, ~6 primitivos nuevos, 1
vista con rediseño visual completo, 3 vistas + 3 servicios + 1 componente
WS con un cambio mínimo (quitar parámetro/campo de token), sin cambios de
backend.

## Constitution Check

*GATE: Debe cumplirse antes de Fase 0. Re-evaluado después de Fase 1.*

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: no aplica —
  sprint puramente de frontend, sin tocar consultas ni esquema. El
  aislamiento de datos ya lo garantiza el backend (S0.2-S1.10); este
  sprint no introduce ninguna llamada nueva a la API.
- **Principio II (Arquitectura Modular por Capas)**: no aplica a
  `services/`; dentro de `apps/web`, se seguiye el patrón ya establecido
  (componente standalone, estado en `signal()`, `inject()` para DI,
  `mensajeDeError` uniforme) sin introducir una capa nueva.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE — la
  vista canónica se verifica contra el WebSocket real del gateway en
  Docker generando cambios de estado reales, no contra datos simulados
  en el navegador ([quickstart.md](./quickstart.md)).
- **Principio IV (Calidad Continua en Verde)**: aplica en lo que exista
  (lint/build de Angular); no hay suite de tests de frontend que cerrar
  en verde porque no existe todavía en el proyecto (no se introduce en
  este sprint, sería alcance no pedido).
- **Principio V (Aprobación Explícita Antes de Acciones Irreversibles)**:
  aplica igual — presentar diff antes de commitear, sin commit hasta
  pedido explícito. Ninguna acción de este sprint es destructiva
  (elimina un `<textarea>` y un parámetro de función, no datos).
- **Requisitos Tecnológicos y de Infraestructura**: CUMPLE — la
  verificación corre contra el contenedor `web`/`gateway` en Docker
  (`infra/docker-compose.yml`), nunca con `npx nx serve` suelto en el
  host. Skill `frontend-design` ya se usó para producir
  `docs/diseno/DIRECCION_VISUAL.md`; este sprint sigue esa dirección ya
  aprobada, no vuelve a invocar el skill para redecidir estética.

Sin violaciones que justificar — no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-diseno-sistema-jwt/
├── plan.md
├── research.md
└── quickstart.md
```

Sin `data-model.md` ni `contracts/`: este sprint no introduce entidades
de datos ni contratos de API nuevos (FR-001..FR-012 son todos de
presentación/frontend).

### Source Code (repository root)

```text
apps/web/src/
├── styles.scss                          # + semaforo, + regla de mono para dato
├── app/
│   ├── _primitivos.scss                 # NUEVO -- .ah-tira/.ah-tabla/.ah-campo/.ah-btn/.ah-alerta/.ah-vacio
│   ├── auth/
│   │   └── _auth-form.scss              # migra sus reglas a los primitivos nuevos (sin duplicar .card/.field/.btn)
│   ├── vuelos/estado-tiempo-real/
│   │   ├── estado-tiempo-real.ts        # quita signal tokenJwt; usa auth.token() para el WS
│   │   ├── estado-tiempo-real.html      # rediseno completo con .ah-tira
│   │   └── estado-tiempo-real.scss      # NUEVO
│   ├── billing/
│   │   ├── billing.service.ts           # quita parametro tokenJwt de los 5 metodos
│   │   └── panel-facturas/*.ts          # deja de pasar tokenJwt al servicio (sin rediseno visual)
│   ├── rampa/
│   │   ├── rampa.service.ts             # idem
│   │   └── panel-turnaround/*.ts        # idem
│   └── puertas/
│       ├── puertas.service.ts           # idem
│       └── tablero-puertas/*.ts         # idem

docs/PLAN_IMPLEMENTACION_v2.0.md          # + Sec 8.11 (S1.11)
CLAUDE.md                                 # + fila de sprint, + estado del rediseño
```

**Structure Decision**: los primitivos compartidos van a un archivo nuevo
`apps/web/src/app/_primitivos.scss` importado desde `styles.scss` (global,
no por componente) porque S1.12-S1.14 los consumen desde vistas en
carpetas distintas — declararlos dentro de `auth/` o de `vuelos/` los
ataría a un módulo que no es su dueño conceptual. `_auth-form.scss` se
mantiene como archivo (las 6 vistas de auth lo importan) pero sus reglas
de `.card`/`.field`/`.btn` pasan a apoyarse en los primitivos nuevos en
vez de duplicar las mismas propiedades.
