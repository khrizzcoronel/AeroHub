"""Composicion de los mensajes de correo (Sprint S1.10,
contracts/correo-puerto.md). Vive en `application/`, no en
`infrastructure/`: es contenido de negocio (que dice cada correo), no
transporte -- el adaptador SMTP (`infrastructure/correo_smtp.py`) no
sabe nada de plantillas.

Solo 3 de las 4 plantillas documentadas en el contrato tienen un disparador
en este sprint (invitacion, verificacion, recuperacion) -- "aviso de
acceso desde origen nuevo" queda documentada en el contrato para una
integracion futura, pero ningun FR/CU de spec.md la dispara todavia;
construirla sin un llamador seria codigo muerto (no se implementa aqui).
"""

from __future__ import annotations

import os

from aerohub_contracts import Mensaje


def _url_base() -> str:
    return os.environ.get("AEROHUB_URL_BASE_APP", "http://localhost:4200")


def mensaje_invitacion(
    *, destinatario: str, token_en_claro: str, invitado_por_nombre: str, tenant_razon_social: str
) -> Mensaje:
    enlace = f"{_url_base()}/aceptar-invitacion?token={token_en_claro}"
    return Mensaje(
        destinatario=destinatario,
        asunto=f"Invitacion a {tenant_razon_social} en AeroHub",
        cuerpo_texto=(
            f"{invitado_por_nombre} te invito a unirte a {tenant_razon_social} en AeroHub.\n\n"
            f"Aceptar la invitacion: {enlace}\n\n"
            "Este enlace vence en 7 dias y solo puede usarse una vez."
        ),
        cuerpo_html=(
            f"<p>{invitado_por_nombre} te invito a unirte a "
            f"<strong>{tenant_razon_social}</strong> en AeroHub.</p>"
            f'<p><a href="{enlace}">Aceptar la invitacion</a></p>'
            "<p>Este enlace vence en 7 dias y solo puede usarse una vez.</p>"
        ),
    )


def mensaje_verificacion(*, destinatario: str, token_en_claro: str) -> Mensaje:
    enlace = f"{_url_base()}/verificar-correo?token={token_en_claro}"
    return Mensaje(
        destinatario=destinatario,
        asunto="Verifica tu correo en AeroHub",
        cuerpo_texto=(
            f"Confirma que este correo es tuyo: {enlace}\n\nEste enlace vence en 24 horas."
        ),
        cuerpo_html=(
            f'<p>Confirma que este correo es tuyo: <a href="{enlace}">Verificar correo</a></p>'
            "<p>Este enlace vence en 24 horas.</p>"
        ),
    )


def mensaje_recuperacion(*, destinatario: str, token_en_claro: str) -> Mensaje:
    enlace = f"{_url_base()}/restablecer?token={token_en_claro}"
    return Mensaje(
        destinatario=destinatario,
        asunto="Recuperar tu contrasena de AeroHub",
        cuerpo_texto=(
            f"Elegi una contrasena nueva aqui: {enlace}\n\n"
            "Este enlace vence en 1 hora. Si no fuiste vos, ignora este mensaje."
        ),
        cuerpo_html=(
            f'<p>Elegi una contrasena nueva aqui: <a href="{enlace}">Restablecer contrasena</a></p>'
            "<p>Este enlace vence en 1 hora. Si no fuiste vos, ignora este mensaje.</p>"
        ),
    )
