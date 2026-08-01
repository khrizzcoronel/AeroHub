# Implementation Plan: M3 Terminal & Gate Manager -- asignación de puertas sin solapamiento

**Branch**: `main` | **Date**: 2026-08-01 (retroactivo) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-gate-manager-asignacion-puertas/spec.md`

## Summary

Módulo `services/gates` completo: dominio con el algoritmo puro de
intersección de intervalos semiabiertos, infraestructura con el mecanismo de
"bloqueo de fila" simulado (MonetDB no tiene `SELECT ... FOR UPDATE`),
asignación manual verificada bajo concurrencia real, asignación automática
por programación lineal (PuLP), y un tablero Angular con notificación de
conflicto.

## Technical Context

**Language/Version**: Python 3.12, TypeScript/Angular 22

**Primary Dependencies**: FastAPI, PuLP (nueva dependencia, resuelve el
modelo de programación lineal con el solver CBC bundleado)

**Storage**: MonetDB -- `ops.asignacion_puerta` (`db/ddl/monetdb/10_ops.sql`, ampliado)

**Testing**: `pytest` unit (algoritmo de intervalos) + integration
(secuencial vía `TestClient`, concurrente vía servidor real + `ThreadPoolExecutor`)

**Target Platform**: backend suelto en el host

**Performance Goals**: sin objetivo de latencia explícito -- el requisito es
de CORRECCIÓN bajo concurrencia, no de velocidad

**Constraints**: MonetDB carece de `EXCLUDE USING gist` y de
`SELECT ... FOR UPDATE`; la garantía de no solapamiento se construye con
herramientas que el motor SÍ tiene (UPDATE de una fila + concurrencia
optimista + reintento)

**Scale/Scope**: 1 módulo de negocio nuevo, ampliación de
`aerohub_repository.reintentar_en_conflicto` (segundo SQLSTATE reconocido)

## Constitution Check

- **Principio III (Verificación Empírica Obligatoria)**: CUMPLE de forma
  particularmente estricta -- el mecanismo central del sprint (bloqueo de
  fila simulado) se diseñó, se probó bajo concurrencia real, FALLÓ la
  primera vez (500 en vez de 409 limpio), se diagnosticó el SQLSTATE 42000
  nuevo, se corrigió el decorador de reintentos compartido, y se volvió a
  probar hasta confirmar el resultado correcto (201+409, nunca 500) en 3
  corridas consecutivas.
- **Principio II (Arquitectura Modular por Capas)**: CUMPLE -- `gates`
  redeclara localmente `ops.terminal`/`ops.puerta`/`ops.vuelo` en su propio
  `infrastructure/tablas.py` en vez de importar las de `aodb`.

## Project Structure

### Documentation (this feature)

```text
specs/006-gate-manager-asignacion-puertas/
├── plan.md
└── spec.md
```

### Source Code (repository root)

```text
services/gates/aerohub_gates/
├── domain/asignacion_puerta.py   # intervalos_se_solapan(), verificar_no_solapamiento(),
│                                   verificar_compatibilidad_envergadura()
├── infrastructure/
│   ├── comandos.py                # bloquear_puerta_para_asignacion() -- UPDATE sin efecto
│   └── tablas.py, consultas.py, alcances.py
├── application/
│   ├── asignar_puerta.py, cancelar_asignacion.py, consultar_asignaciones.py
│   └── asignacion_automatica.py    # modelo PuLP (LpProblem, LpMaximize)
└── api/router.py

packages/repository/aerohub_repository/reintentos.py   # ampliado: reconoce SQLSTATE 42000 ademas de 40001

apps/web/src/app/puertas/tablero-puertas/    # tablero Angular con notificacion de conflicto
```

**Structure Decision**: la asignación automática por PuLP se implementa como
un caso de uso más de `application/`, NO como un servicio aparte -- reutiliza
las mismas funciones de dominio (`intervalos_se_solapan`,
`verificar_compatibilidad_envergadura`) que la asignación manual, evitando
dos implementaciones divergentes de la misma regla de negocio.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Modificar `packages/repository/aerohub_repository/reintentos.py` (paquete transversal) desde un sprint de módulo de negocio | El segundo SQLSTATE de conflicto (42000) es un hallazgo genuino del MOTOR, no específico de `gates` -- cualquier módulo futuro con el mismo patrón de "bloqueo de fila simulado" lo necesitaría | Duplicar la lógica de reintento dentro de `aerohub_gates` habría fragmentado el mecanismo compartido sin necesidad real |
