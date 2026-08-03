# Implementation Plan: Vistas administrativas + consolidación

**Branch**: `main` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/015-vistas-administrativas-consolidacion/spec.md`

## Summary

Cierra el rediseño de las áreas de negocio: `billing/panel-facturas`
(tira por factura con semáforo de estado, tabla de líneas de cargo) y
`tenants/tenant-creation` (formulario simple con los primitivos ya
existentes). Audita las 8 vistas de identidad de S1.10 contra el sistema
formalizado en S1.11, corrigiendo inconsistencias menores. Sin cambios
de backend.

## Technical Context

**Language/Version**: TypeScript/Angular 22 (frontend únicamente).

**Primary Dependencies**: primitivos SCSS existentes (`.ah-tira`,
`.ah-tabla`, `.ah-punto`, `.ah-campo`, `.ah-btn`, `.ah-alerta`,
`.ah-vacio`) — ninguno nuevo.

**Storage**: N/A.

**Testing**: verificación manual en navegador real contra el backend en
Docker (Principio III), igual que S1.11/S1.12 — ver
[quickstart.md](./quickstart.md).

**Target Platform**: navegador, contenedor `web`.

**Performance Goals**: N/A — sin lógica nueva más allá de un mapeo de
presentación puro (`claseEstadoFactura`).

**Constraints**: cero cambios en `billing.service.ts`/`tenant.service.ts`.

**Scale/Scope**: 2 vistas rediseñadas + auditoría de 8 vistas existentes
(solo correcciones puntuales si aparecen).

## Constitution Check

- **Principios I/II**: no aplican — sin cambios de acceso a datos.
- **Principio III**: CUMPLE — verificación con datos reales en Docker.
- **Principio IV**: build de Angular en verde.
- **Principio V**: commit solo si se pide, diff presentado antes.
- **Infraestructura**: verificación en contenedor `web`
  (`docker compose up -d --build web`, hallazgo de S1.11).

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/015-vistas-administrativas-consolidacion/
├── plan.md
├── research.md
└── quickstart.md
```

### Source Code (repository root)

```text
apps/web/src/app/
├── billing/panel-facturas/
│   ├── panel-facturas.html   # rediseno con .ah-tira/.ah-tabla/.ah-punto/.ah-campo/.ah-btn
│   ├── panel-facturas.ts     # + funcion pura claseEstadoFactura
│   └── panel-facturas.scss   # NUEVO (reemplaza el bloque `styles:` inline)
└── tenants/tenant-creation/
    ├── tenant-creation.html  # rediseno con .ah-campo/.ah-btn/.ah-alerta
    └── tenant-creation.scss  # NUEVO

apps/web/src/app/auth/**/*.{html,scss}   # auditoria -- solo si aparece algo que corregir
apps/web/src/app/shell/*.{html,scss}     # idem
```

**Structure Decision**: mismo patrón por componente que S1.11/S1.12.

## Complexity Tracking

Sin violaciones que justificar.
