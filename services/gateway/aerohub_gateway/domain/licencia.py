"""Mapeo de prefijo de ruta HTTP a codigo de modulo licenciable (Sprint
S1.7, RF-O18, CU-O20; research.md Decision 2).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 Sec5.4,
regla 1). No existe metadata de "modulo" en cada APIRouter existente --
el prefijo de ruta es la unica senal disponible sin tocar los 6 routers
de negocio ya existentes.

Los codigos 'M1'..'M9' NO son una invencion de este sprint: YA estan
sembrados en catalogo.modulo desde el DDL fundacional
(db/ddl/monetdb/01_catalogo.sql, INSERT de S0.1) -- 'M1'=AODB,
'M2'=FIDS Management, 'M3'=Terminal & Gate Manager, 'M4'=Ground
Operations, 'M5'=Revenue & Billing, 'M6'=Passenger Experience. M7-M9 (ETL
& Analytics, Observability, Compliance Hub) no tienen ruta HTTP propia
licenciable en este sprint -- no aparecen en este mapeo.
"""

from __future__ import annotations

# Rutas de aprovisionamiento (/tenants/*) y de plataforma (/metrics) NO
# estan aqui -- exentas por diseno, no un descuido (no se puede exigir
# licencia para el propio flujo que la otorga).
PREFIJO_A_CODIGO_MODULO: dict[str, str] = {
    "/vuelos": "M1",
    "/fids": "M2",
    "/puertas": "M3",
    "/rampa": "M4",
    "/billing": "M5",
    "/passenger": "M6",
}


def resolver_modulo_de_ruta(path: str) -> str | None:
    """None si la ruta no requiere licencia (fuera del diccionario)."""
    primer_segmento = "/" + path.strip("/").split("/", 1)[0] if path.strip("/") else ""
    return PREFIJO_A_CODIGO_MODULO.get(primer_segmento)
