"""Invariantes de reporte regulatorio DGAC (Sprint S1.7, SDD-DATA-001
Sec10.5). Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos
(ADR-017 Sec5.4, regla 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class ReporteDgacInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ReporteDgac:
    id: int
    tenant_id: int
    tipo_reporte_id: int
    periodo_inicio: date
    periodo_fin: date
    contenido_ref: str
    hash_contenido: str
    emitido_por_usuario_id: int

    def __post_init__(self) -> None:
        if self.periodo_fin < self.periodo_inicio:
            raise ReporteDgacInvalido(
                f"periodo_fin ({self.periodo_fin}) no puede ser anterior a "
                f"periodo_inicio ({self.periodo_inicio})"
            )
        if len(self.hash_contenido) != 64:
            raise ReporteDgacInvalido("hash_contenido debe ser SHA-256 (64 caracteres hex)")
        if not self.contenido_ref.strip():
            raise ReporteDgacInvalido("contenido_ref no puede ser vacio")
