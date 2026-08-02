"""Registro G1 (ADR-019) de las tablas verdaderamente transversales:
catalogo (referenciado por todos los modulos via FK), compliance y
continuidad (infraestructura de auditoria/continuidad, no propiedad de
ningun modulo de negocio).

Cualquier tabla propiedad de un modulo especifico se registra junto a su
propio codigo, en `services/<modulo>/infrastructure/alcances.py` -- ese
codigo debe importarse (arranque de la app FastAPI del modulo) antes de
que llegue una peticion, igual que este archivo se importa desde
aerohub_repository/__init__.py. Historial: `ops.*` vive en
services/aodb/ y `tenants.*` en services/tenancy/ desde S1.1 (ambos
registrados centralmente aqui hasta entonces).
"""

from __future__ import annotations

from .guard import registrar_alcance

_CATALOGO = (
    "pais",
    "aeropuerto",
    "aerolinea",
    "modelo_aeronave",
    "aeronave",
    "tipo_vuelo",
    "motivo_demora",
    "estado_vuelo_catalogo",
    "departamento",
    "modulo",
)
for _tabla in _CATALOGO:
    registrar_alcance("catalogo", _tabla, "global")

# tenant_id es nullable en ambas (eventos de alcance de plataforma sin
# tenant asociado son legitimos, SDD-DATA-001 §10.1 / ADR-018 C1) -- el
# guardian no puede exigir un filtro que la propia tabla no siempre porta.
registrar_alcance("compliance", "log_auditoria", "interno")
registrar_alcance("continuidad", "journal_mutacion", "interno")

# Ampliacion de continuidad (Sprint S1.9, ADR-018 C2/C3/C4) -- catalogo de
# snapshots, checkpoint del shipper y evidencia de la prueba de
# restauracion: infraestructura de plataforma sin tenant_id, mismo
# tratamiento que journal_mutacion.
registrar_alcance("continuidad", "snapshot_base", "interno")
registrar_alcance("continuidad", "shipper_checkpoint", "interno")
registrar_alcance("continuidad", "prueba_restauracion", "interno")
