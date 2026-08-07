from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import contexto_tenant_id, contexto_usuario_id

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1 de ops.*
from .comandos import (
    actualizar_puerta,
    bloquear_puerta_para_asignacion,
    cancelar_asignacion_puerta,
    insertar_asignacion_puerta,
    insertar_puerta,
    insertar_terminal,
)
from .consultas import (
    listar_asignaciones,
    listar_asignaciones_que_ocupan_puerta,
    listar_puertas,
    listar_terminales,
    listar_vuelos_sin_asignacion_con_envergadura,
    obtener_asignacion_por_id,
    obtener_puerta_por_codigo,
    obtener_puerta_por_id,
    obtener_terminal_por_codigo,
    obtener_terminal_por_id,
    obtener_vuelo_con_envergadura,
)
from .consultas_informe import agrupar_asignaciones_por_puerta, listar_asignaciones_informe

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository. application/ obtiene
# sesion/journal/auditoria/contexto reexportados desde aqui, nunca del
# paquete transversal directamente.
__all__ = [
    "bloquear_puerta_para_asignacion",
    "insertar_asignacion_puerta",
    "cancelar_asignacion_puerta",
    "obtener_puerta_por_id",
    "obtener_asignacion_por_id",
    "listar_puertas",
    "listar_asignaciones_que_ocupan_puerta",
    "obtener_vuelo_con_envergadura",
    "listar_vuelos_sin_asignacion_con_envergadura",
    "listar_asignaciones",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "reintentar_en_conflicto",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "listar_asignaciones_informe",
    "agrupar_asignaciones_por_puerta",
    "listar_terminales",
    "obtener_terminal_por_id",
    "obtener_terminal_por_codigo",
    "obtener_puerta_por_codigo",
    "insertar_terminal",
    "insertar_puerta",
    "actualizar_puerta",
]
