"""Invariantes de API Key (Sprint S1.2, Plan §8.2; SDD-DATA-001 §6.8, RF-O12).

El secreto en claro NUNCA vive en este objeto -- solo su hash (columna
`hash_secreto`, ya calculado por `aerohub_kernel.hash_credencial` antes de
construir esta instancia). El `prefijo` es la parte publica/buscable de la
clave (formato fijo: 12 caracteres hexadecimales, generado por
`secrets.token_hex(6)` en application/), analogo al patron `sk_live_...` de
Stripe -- permite localizar la fila sin exponer nunca el secreto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

_PREFIJO_PATRON = re.compile(r"^[a-f0-9]{12}$")

ESTADOS_API_KEY = ("activa", "revocada", "expirada")


class ApiKeyInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ApiKey:
    id: int
    tenant_id: int
    prefijo: str
    hash_secreto: str
    creada_en: datetime
    estado: str
    rotada_en: datetime | None = None
    expira_en: datetime | None = None

    def __post_init__(self) -> None:
        if not _PREFIJO_PATRON.match(self.prefijo):
            raise ApiKeyInvalida(f"prefijo con formato invalido: {self.prefijo!r}")
        if not self.hash_secreto:
            raise ApiKeyInvalida("hash_secreto no puede ser vacio")
        if self.estado not in ESTADOS_API_KEY:
            raise ApiKeyInvalida(f"estado invalido: {self.estado!r}")

    def esta_vigente(self, ahora: datetime) -> bool:
        """PN-06: revocada o expirada -- en cualquiera de los dos casos, no
        vigente. `expira_en` es opcional (una clave sin vencimiento fijo es
        valida mientras su `estado` sea 'activa').
        """
        if self.estado != "activa":
            return False
        return self.expira_en is None or ahora < self.expira_en
