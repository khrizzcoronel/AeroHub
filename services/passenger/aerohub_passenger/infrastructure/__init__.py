from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import contexto_rol_actor, contexto_tenant_id, contexto_usuario_id

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1
from .comandos import insertar_o_actualizar_tiempo_espera
from .consultas import (
    listar_asignaciones_completadas_de_terminal,
    listar_terminales,
    listar_tiempos_espera,
    listar_turnarounds_de_vuelos,
    obtener_franja_existente,
    obtener_terminal_por_id,
)

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository.
__all__ = [
    "obtener_terminal_por_id",
    "listar_terminales",
    "listar_asignaciones_completadas_de_terminal",
    "listar_turnarounds_de_vuelos",
    "obtener_franja_existente",
    "listar_tiempos_espera",
    "insertar_o_actualizar_tiempo_espera",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "reintentar_en_conflicto",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "contexto_rol_actor",
]
