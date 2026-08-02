"""Calculo y verificacion de checksum de artefactos de continuidad (Sprint
S1.9, ADR-018 C2). Puro: sin I/O de red, opera sobre bytes ya leidos --
quien lee el archivo (local o desde MinIO) vive en operaciones/snapshot.py.
"""

from __future__ import annotations

import hashlib


def calcular_checksum_sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def checksums_coinciden(calculado: str, esperado: str) -> bool:
    return calculado.lower() == esperado.lower()
