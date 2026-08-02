"""Adaptador SMTP del puerto `EnviarCorreo` (Sprint S1.10, research.md
Decision 6, contracts/correo-puerto.md). `smtplib` + `email.message` de
la biblioteca estandar -- sin dependencia nueva. Configuracion SIEMPRE
por variable de entorno, nunca en el repositorio (ninguna credencial
SMTP real se commitea, en ningun archivo, en ningun momento).
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from aerohub_contracts import EnviarCorreo, EnvioDeCorreoFallo, Mensaje


def crear_adaptador_smtp_desde_entorno() -> EnviarCorreo:
    host = os.environ.get("AEROHUB_SMTP_HOST", "localhost")
    puerto = int(os.environ.get("AEROHUB_SMTP_PORT", "1025"))
    usuario = os.environ.get("AEROHUB_SMTP_USUARIO", "")
    password = os.environ.get("AEROHUB_SMTP_PASSWORD", "")
    usar_tls = os.environ.get("AEROHUB_SMTP_TLS", "false").strip().lower() == "true"
    remitente = os.environ.get("AEROHUB_SMTP_REMITENTE", "no-responder@aerohub.test")

    def _enviar(mensaje: Mensaje) -> None:
        correo = EmailMessage()
        correo["Subject"] = mensaje.asunto
        correo["From"] = remitente
        correo["To"] = mensaje.destinatario
        correo.set_content(mensaje.cuerpo_texto)
        correo.add_alternative(mensaje.cuerpo_html, subtype="html")

        try:
            with smtplib.SMTP(host, puerto, timeout=10) as smtp:
                if usar_tls:
                    smtp.starttls()
                if usuario:
                    smtp.login(usuario, password)
                smtp.send_message(correo)
        except (OSError, smtplib.SMTPException) as exc:
            raise EnvioDeCorreoFallo(
                f"no se pudo entregar el correo a {mensaje.destinatario!r}"
            ) from exc

    return _enviar
