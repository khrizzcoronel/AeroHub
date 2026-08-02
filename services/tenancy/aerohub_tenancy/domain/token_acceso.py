"""Vigencia y un-solo-uso de tokens de acceso (Sprint S1.10, data-model.md).
Puro -- el hash/verificacion Argon2id vive en aerohub_kernel, no aqui.
"""

from __future__ import annotations

from datetime import datetime

TIPOS_VALIDOS = ("verificacion", "invitacion", "recuperacion")


def token_canjeable(*, consumido_en: datetime | None, expira_en: datetime, ahora: datetime) -> bool:
    return consumido_en is None and ahora < expira_en
