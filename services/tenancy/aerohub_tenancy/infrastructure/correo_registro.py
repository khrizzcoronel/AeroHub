"""Registro del adaptador de correo inyectado (Sprint S1.10,
contracts/correo-puerto.md). `application/` depende solo del puerto
`EnviarCorreo` (`aerohub_contracts.correo`); el adaptador concreto
(`correo_smtp.crear_adaptador_smtp_desde_entorno`) se construye e
inyecta una sola vez desde el borde (`services/gateway/main.py`), igual
que cualquier otra dependencia de infraestructura de este proyecto.
"""

from __future__ import annotations

from aerohub_contracts import EnviarCorreo, Mensaje

_adaptador: EnviarCorreo | None = None


def configurar_adaptador_correo(adaptador: EnviarCorreo) -> None:
    global _adaptador  # noqa: PLW0603 -- registro de proceso, mismo patron que un singleton de conexion
    _adaptador = adaptador


def enviar_correo(mensaje: Mensaje) -> None:
    """Lanza si nadie configuro un adaptador -- fail loud, no un no-op
    silencioso que oculte que ningun correo sale nunca."""
    if _adaptador is None:
        raise RuntimeError(
            "ningun adaptador de correo configurado -- "
            "llamar configurar_adaptador_correo() al arrancar el proceso"
        )
    _adaptador(mensaje)
