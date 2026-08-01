# Implementation Plan: Capa de repositorio -- guardián de tenant, roles y DDL fundacional

**Branch**: `main` | **Date**: 2026-07-30 (retroactivo) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-capa-repositorio-guardian-tenant/spec.md`

## Summary

Deja operativa la capa de repositorio (`packages/repository`) con el guardián
de tenant fail-closed (G1 registro de alcance + G2 verificación en
`before_execute`), el journal transaccional de continuidad, la auditoría
append-only, y el DDL fundacional completo (catálogos, `tenants`,
`compliance`, `continuidad`, roles y grants) -- todo antes de la primera
tabla de negocio de Fase 1.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: SQLAlchemy Core, `pymonetdb`

**Storage**: MonetDB -- DDL aplicado vía `db/migrations/apply.py`
(`pymonetdb` directo, no herramienta de migraciones tipo Alembic: MonetDB no
tiene un dialecto de migraciones maduro)

**Testing**: `pytest` contra MonetDB real (Docker), no mocks -- 134 tests

**Target Platform**: MonetDB en Docker (`infra/docker-compose.yml`, servicio
`monetdb`)

**Performance Goals**: N/A explícito en este sprint (el guardián se mide por
corrección, no por latencia)

**Constraints**: el guardián debe recorrer el ÁRBOL de la sentencia
SQLAlchemy Core, nunca el texto SQL compilado (para que un alias o una
concatenación no lo engañen); nunca debe asumir un alcance por defecto
permisivo ante una tabla no declarada.

**Scale/Scope**: 11 archivos DDL, 16 roles RBAC, `packages/repository`
completo (`guard.py`, `base.py`, `journal.py`, `audit.py`, `contexto.py`,
`alcances.py`)

## Constitution Check

- **Principio I (Aislamiento Multi-Tenant Fail-Closed)**: CUMPLE -- este
  sprint es el que construye el mecanismo (G1/G2) que el Principio I
  formaliza después.
- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE -- 134/134
  tests contra MonetDB real, no mocks; los 3 hallazgos empíricos
  (`GENERATED ALWAYS AS IDENTITY`, `MDB_CREATE_DBS`, FK de auditoría) se
  descubrieron y corrigieron por verificación real, no por lectura de
  documentación del motor.
- **Principio IV (Calidad Continua en Verde)**: CUMPLE -- ruff, mypy, bandit,
  import-linter y nomenclatura DDL limpios al cierre.

## Project Structure

### Documentation (this feature)

```text
specs/002-capa-repositorio-guardian-tenant/
├── plan.md
└── spec.md
```

Diseño detallado de las tablas vive en `docs/sdd/AEROHUB-SDD-DATA-001-MonetDB-v1.0.md`
§4-§5; hallazgos empíricos de motor en `docs/runbooks/monetdb.md`.

### Source Code (repository root)

```text
db/
├── ddl/monetdb/
│   ├── 00_schemas.sql .. 04_continuidad.sql   # catalogo, tenants, compliance, continuidad
│   └── 90_roles.sql .. 95_usuario_aplicacion.sql  # roles RBAC + grants + usuario tecnico
├── migrations/apply.py     # aplica *.sql en orden lexicografico via pymonetdb
└── seeds/generate.py       # datos sinteticos + filas canario (MEC/UIO)

packages/
├── kernel/aerohub_kernel/
│   ├── identificador.py    # generar_id() estilo Snowflake (motor no puede)
│   └── credenciales.py     # hash de credenciales
└── repository/aerohub_repository/
    ├── guard.py             # G1 (registrar_alcance) + G2 (verificar_sentencia)
    ├── base.py              # sesion() -- SET ROLE real por sesion
    ├── contexto.py           # ContextVar de tenant/rol/usuario, alcance_global()
    ├── journal.py            # escribir_journal (ADR-018 C1)
    ├── audit.py               # registrar_auditoria (P8)
    └── alcances.py            # registro G1 de tablas transversales (catalogo/tenants/compliance/continuidad)

tests/
├── negative/    # PN-03, PN-04, PN-08, PN-15 (58 casos)
└── cross_tenant/  # suite G4 por introspeccion
```

**Structure Decision**: la capa de repositorio es un paquete transversal
(`packages/repository`), no un módulo de negocio -- cualquier módulo de
negocio futuro importa de aquí, nunca al revés.

## Complexity Tracking

Sin violaciones que justificar.
