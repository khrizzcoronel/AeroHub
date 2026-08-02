"""Puertos declarados entre modulos (SRS §2.3 — tabla de dependencias entre modulos).

Ningun modulo de services/ importa el domain/ ni el application/ de otro
modulo (ADR-017 §5.4). Cuando M4 necesita ETA y puerta asignada de M1/M3,
la dependencia se expresa aqui como evento o DTO, nunca como import directo.

`scopes.requiere_scope` (S1.2) es el primer inquilino de este paquete: no
es un DTO/evento de dominio, pero es exactamente el mismo problema
estructural -- una utilidad que TODO modulo de negocio necesita y que
ninguno puede importar de otro modulo sin romper la independencia.
"""

from .correo import EnviarCorreo, EnvioDeCorreoFallo, Mensaje
from .jwt_sesion import emitir_jwt_sesion, sesion_id_de_jwt
from .roles_modulos import MODULOS, Modulo, modulos_del_rol, scopes_del_rol
from .scopes import requiere_scope
from .ws_auth import IdentidadWebSocket, TokenWebSocketInvalido, autenticar_websocket

__all__ = [
    "requiere_scope",
    "autenticar_websocket",
    "IdentidadWebSocket",
    "TokenWebSocketInvalido",
    "EnviarCorreo",
    "EnvioDeCorreoFallo",
    "Mensaje",
    "MODULOS",
    "Modulo",
    "modulos_del_rol",
    "scopes_del_rol",
    "emitir_jwt_sesion",
    "sesion_id_de_jwt",
]
