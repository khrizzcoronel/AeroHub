# Implementation Plan: Rediseño de fids-player/pantalla-player

**Branch**: `main` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-fids-player-rediseno/spec.md`

## Summary

Cierra el cuarto y último sprint del rediseño de interfaz (S1.11-S1.14).
Rediseña la única vista de `apps/fids-player` (`pantalla-player`) en tres
modos visualmente distintos y mutuamente excluyentes: `configuracion`
(formulario de código+token, sin login real, ver research.md Decisión 6),
`reproduccion` (contenido de plantilla en tipografía enorme, cero
elementos de consola) y `sin_senal` (nuevo, inferido en el cliente sin
backend nuevo — research.md Decisión 2). Copia los tokens de color/fuente
de `apps/web/src/styles.scss` sin el paquete de primitivos de consola
(research.md Decisión 4), con una escala tipográfica propia para
legibilidad a 3+ metros (research.md Decisión 5). Sin cambios de backend,
de contrato HTTP/WS, ni de esquema.

## Technical Context

**Language/Version**: TypeScript/Angular 22 (frontend únicamente).

**Primary Dependencies**: ninguna nueva — se copian (no se importan)
variables `:root` de `apps/web/src/styles.scss` y los `<link>` de Google
Fonts (IBM Plex Sans/Mono) de `apps/web/src/index.html`, ver research.md
Decisión 4.

**Storage**: N/A.

**Testing**: verificación manual en navegador real contra el gateway en
Docker (Principio III) — conectar una pantalla real, forzar corte de
WebSocket, confirmar recuperación automática. Ver
[quickstart.md](./quickstart.md).

**Target Platform**: navegador en pantalla física (kiosk), contenedor
`fids-player`.

**Performance Goals**: transición de estado de la barra/color en
≤ 150ms (mismo criterio ya fijado en DIRECCION_VISUAL.md §2.5 para toda
actualización de estado en vivo); detección de "sin señal" en ≤ 30s
(research.md Decisión 2, spec.md SC-003).

**Constraints**: cero elementos de interfaz de consola visibles en modo
`reproduccion` (spec.md FR-002); cero cambios en `pantalla.service.ts`
(mismos 2 métodos HTTP, mismo mecanismo de token — spec.md FR-004,
FR-009); cero cambios de backend.

**Scale/Scope**: 1 vista (`pantalla-player`), 3 modos visuales nuevos,
1 archivo de tokens nuevo (`apps/fids-player/src/styles.scss`), 1
`<link>` de fuentes nuevo (`apps/fids-player/src/index.html`).

## Constitution Check

- **Principios I/II**: no aplican — sin cambios de acceso a datos ni de
  módulos de backend.
- **Principio III**: CUMPLE — verificación con datos reales (plantilla
  real, corte de WebSocket real) en Docker, ver quickstart.md.
- **Principio IV**: build de Angular de `fids-player` en verde.
- **Principio V**: commit solo si se pide, diff presentado antes.
- **Infraestructura**: verificación en contenedor `fids-player`
  (`docker compose up -d --build fids-player`, mismo hallazgo de S1.11
  sobre `apps/web/Dockerfile` — build-time copy, sin volumen).

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/016-fids-player-rediseno/
├── plan.md
├── research.md
└── quickstart.md
```

Sin `data-model.md` ni `contracts/` — mismo criterio que S1.11-S1.13
(sprint de presentación puro, sin entidades nuevas ni contrato HTTP/WS
nuevo que documentar; las entidades ya existentes se listan en spec.md
§Key Entities).

### Source Code (repository root)

```text
apps/fids-player/src/
├── styles.scss                              # NUEVO contenido: tokens copiados (research.md D4/D5)
├── index.html                                # + <link> de Google Fonts (IBM Plex Sans/Mono)
└── app/pantallas/pantalla-player/
    ├── pantalla-player.html                  # rediseno: 3 modos (@if configuracion/reproduccion/sin_senal)
    ├── pantalla-player.ts                    # + modoActual computed, deteccion de sin_senal (D2), filasDeTexto respaldo (D7)
    └── pantalla-player.scss                  # NUEVO
```

**Structure Decision**: mismo patrón por componente que S1.11-S1.13
(HTML + TS + SCSS propio del componente), aplicado a la única vista de
esta segunda aplicación Angular.

## Complexity Tracking

Sin violaciones que justificar.
