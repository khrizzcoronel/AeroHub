# Implementation Plan: Tableros operativos densos (puertas + rampa)

**Branch**: `main` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/014-tableros-operativos-densos/spec.md`

## Summary

Aplica el sistema de diseño construido en S1.11 (`.ah-tira`, `.ah-tabla`,
`.ah-campo`, `.ah-btn`, `.ah-alerta`, `.ah-vacio`) a las dos vistas de
tableros operativos densos que quedaron con HTML crudo: `puertas/tablero-
puertas` (una tira por puerta, color = ocupación/conflicto calculado por
solapamiento de intervalos) y `rampa/panel-turnaround` (una tira por
turnaround, color = desviación aproximada por `estado`; tareas e
incidencias en `.ah-tabla` con semáforo en sus columnas de estado/
severidad). Sin cambios de backend ni de contrato HTTP — sprint
exclusivamente de presentación.

## Technical Context

**Language/Version**: TypeScript/Angular 22 (frontend únicamente).

**Primary Dependencies**: los mismos primitivos SCSS de S1.11
(`apps/web/src/app/_primitivos.scss`) — ninguna dependencia nueva.

**Storage**: N/A — sin cambios de esquema ni de API.

**Testing**: verificación manual en navegador real contra el backend real
en Docker (Principio III), igual que S1.11 — ver
[quickstart.md](./quickstart.md). Sin suite de tests de frontend (no
existe en el proyecto, no se introduce para un sprint de estilo).

**Target Platform**: navegador, servido por el contenedor `web`.

**Performance Goals**: el cálculo de conflicto/desviación es una función
pura de presentación (recorrido lineal/cuadrático sobre listas de
decenas de elementos como máximo) — sin impacto perceptible.

**Constraints**: cero cambios en `puertas.service.ts`/`rampa.service.ts`
ni en los `.ts` de componente más allá de las funciones puras de mapeo a
semáforo (mismo patrón que `claseDeEstado` en `estado-tiempo-real.ts`,
S1.11) — el HTML es lo que cambia de verdad.

**Scale/Scope**: 2 vistas (`.html` + `.ts` con función de mapeo pura +
`.scss` nuevo cada una), sin tocar servicios ni backend.

## Constitution Check

- **Principio I**: no aplica — sin cambios de acceso a datos.
- **Principio II**: no aplica a `services/`; en `apps/web` se sigue el
  mismo patrón de componente ya establecido (signals, `inject()`,
  funciones puras de mapeo separadas del template).
- **Principio III**: CUMPLE — verificación contra el backend real en
  Docker con datos reales (asignaciones/turnarounds/tareas/incidencias
  reales), no con datos simulados.
- **Principio IV**: aplica en lo que exista (build de Angular en verde).
- **Principio V**: sin acciones irreversibles; commit solo si se pide.
- **Requisitos de infraestructura**: verificación en el contenedor `web`
  de Docker, recordando el hallazgo de S1.11 (`COPY apps apps` en build-
  time — hace falta `--build`, no alcanza con `restart`).

Sin violaciones — no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-tableros-operativos-densos/
├── plan.md
├── research.md
└── quickstart.md
```

Sin `data-model.md` ni `contracts/` — mismo motivo que S1.11 (sprint sin
entidades ni contratos de API nuevos).

### Source Code (repository root)

```text
apps/web/src/app/
├── puertas/tablero-puertas/
│   ├── tablero-puertas.html   # rediseno con .ah-tira/.ah-tabla/.ah-campo/.ah-btn/.ah-alerta/.ah-vacio
│   ├── tablero-puertas.ts     # + funcion pura de calculo de conflicto/ocupacion
│   └── tablero-puertas.scss   # NUEVO
└── rampa/panel-turnaround/
    ├── panel-turnaround.html  # idem
    ├── panel-turnaround.ts    # + funciones puras de mapeo (turnaround, severidad)
    └── panel-turnaround.scss  # NUEVO
```

**Structure Decision**: mismo patrón de archivo por componente que
`estado-tiempo-real` en S1.11 — sin nuevos primitivos SCSS globales (los
de S1.11 ya cubren lo que estas 2 vistas necesitan).

## Complexity Tracking

Sin violaciones que justificar.
