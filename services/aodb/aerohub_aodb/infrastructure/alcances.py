"""Registro G1 (ADR-019) de las tablas de ops -- Sprint S1.1.

Primer modulo que sigue el patron que packages/repository/alcances.py
anuncia en su propio docstring: a partir de que un modulo tiene su propio
`infrastructure/`, registra el alcance de SUS tablas aqui, no en el
registro centralizado (que queda limitado a lo verdaderamente
transversal: catalogo, tenants, compliance, continuidad).

Las 5 tablas de ops tienen tenant_id NOT NULL -- todas son alcance
'tenant' (a diferencia de tenants.*, donde varias tablas no lo tienen).
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

_TABLAS_OPS = (
    "terminal",
    "puerta",
    "vuelo",
    "vuelo_estado",
    "vuelo_demora",
    "v_vuelo_estado_actual",  # vista, no tabla, pero G1 no distingue (ver tablas.py)
)
for _tabla in _TABLAS_OPS:
    registrar_alcance("ops", _tabla, "tenant")
