"""Helper minimo para verificar correos contra mailpit real (Sprint
S1.10, contracts/correo-puerto.md: "no se usa un mock de smtplib,
Principio III"). Sin dependencia nueva -- reusa `httpx`, ya presente
via `fastapi.testclient`.
"""

from __future__ import annotations

import os
import re

import httpx

_BASE = f"http://{os.environ.get('AEROHUB_SMTP_HOST', 'localhost')}:8025"


def limpiar_buzon() -> None:
    httpx.delete(f"{_BASE}/api/v1/messages")


def ultimo_mensaje_para(destinatario: str, *, asunto_contiene: str | None = None) -> dict:
    """Busca en orden inverso (mas reciente primero) el primer mensaje
    dirigido a `destinatario`. Lanza AssertionError con un mensaje claro
    si no aparece -- mas util en un fallo de test que un IndexError."""
    resumen = httpx.get(f"{_BASE}/api/v1/messages", params={"limit": 50}).json()
    for item in resumen.get("messages", []):
        destinatarios = {d["Address"] for d in item.get("To", [])}
        if destinatario not in destinatarios:
            continue
        if asunto_contiene and asunto_contiene not in item.get("Subject", ""):
            continue
        return httpx.get(f"{_BASE}/api/v1/message/{item['ID']}").json()
    raise AssertionError(f"ningun correo a {destinatario!r} encontrado en mailpit")


def extraer_token_del_enlace(mensaje: dict) -> str:
    """El cuerpo HTML/texto contiene `...?token=<valor>` -- extrae el
    valor, que es el token EN CLARO que las plantillas incluyen una sola
    vez (research.md Decision 8)."""
    cuerpo = mensaje.get("Text") or mensaje.get("HTML") or ""
    coincidencia = re.search(r"token=([A-Za-z0-9_\-.]+)", cuerpo)
    if not coincidencia:
        raise AssertionError(f"no se encontro un enlace con token en el correo: {cuerpo!r}")
    return coincidencia.group(1)
