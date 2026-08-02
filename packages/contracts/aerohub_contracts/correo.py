"""Puerto de envio de correo (Sprint S1.10, research.md Decision 6).

`application/` de `aerohub_tenancy` depende de este puerto, nunca del
adaptador SMTP concreto (que vive en
`aerohub_tenancy/infrastructure/correo_smtp.py`) -- el adaptador se
inyecta desde el borde (`services/gateway/main.py`), igual que cualquier
otra dependencia de infraestructura. El puerto no conoce plantillas, SMTP,
credenciales ni reintentos -- solo el contrato de "enviar un mensaje ya
compuesto".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Mensaje:
    destinatario: str
    asunto: str
    cuerpo_texto: str
    cuerpo_html: str


class EnviarCorreo(Protocol):
    def __call__(self, mensaje: Mensaje) -> None: ...


class EnvioDeCorreoFallo(Exception):
    """El adaptador no pudo entregar el mensaje al servidor SMTP."""
