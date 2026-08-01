"""Registro G1 (ADR-019) de las tablas de FIDS -- Sprint S1.3.

`ops.plantilla_fids` y `ops.pantalla_fids` viven en el esquema `ops`
(SDD-DATA-001 §7.7-7.8) pero las gestiona services/fids, no
services/aodb -- cada modulo registra el alcance de SUS PROPIAS tablas
aqui, aunque compartan esquema de base de datos con otro modulo (el
registro G1 es un diccionario plano (esquema, tabla) -> alcance, no esta
particionado por modulo Python que lo puebla).
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

_TABLAS_FIDS = ("plantilla_fids", "pantalla_fids")
for _tabla in _TABLAS_FIDS:
    registrar_alcance("ops", _tabla, "tenant")
