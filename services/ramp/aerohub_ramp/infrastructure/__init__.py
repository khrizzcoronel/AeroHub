from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import contexto_rol_actor, contexto_tenant_id, contexto_usuario_id

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1
from .comandos import (
    finalizar_tarea_turnaround,
    insertar_incidencia_rampa,
    insertar_tarea_turnaround,
    insertar_turnaround,
)
from .consultas import (
    listar_incidencias,
    listar_tareas_de_turnaround,
    listar_turnarounds,
    obtener_tarea_turnaround_por_id,
    obtener_tipo_incidencia_por_codigo,
    obtener_tipo_tarea_por_id,
    obtener_turnaround_por_id,
    obtener_turnaround_por_vuelo_llegada,
    obtener_vuelo_por_id,
)
from .consultas_informe import agrupar_turnarounds_por_tipo_tarea, listar_turnarounds_informe

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository. application/ obtiene
# sesion/journal/auditoria/contexto reexportados desde aqui, nunca del
# paquete transversal directamente.
__all__ = [
    "insertar_turnaround",
    "insertar_tarea_turnaround",
    "finalizar_tarea_turnaround",
    "insertar_incidencia_rampa",
    "obtener_vuelo_por_id",
    "obtener_tipo_tarea_por_id",
    "obtener_tipo_incidencia_por_codigo",
    "obtener_turnaround_por_id",
    "obtener_turnaround_por_vuelo_llegada",
    "obtener_tarea_turnaround_por_id",
    "listar_tareas_de_turnaround",
    "listar_turnarounds",
    "listar_incidencias",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "reintentar_en_conflicto",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "contexto_rol_actor",
    "listar_turnarounds_informe",
    "agrupar_turnarounds_por_tipo_tarea",
]
