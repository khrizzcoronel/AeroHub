from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import contexto_tenant_id, contexto_usuario_id

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1 de ops.*
from .comandos import insertar_vuelo, insertar_vuelo_estado
from .consultas import (
    estado_vuelo_catalogo,
    listar_vuelos,
    obtener_estado_catalogo_por_codigo,
    obtener_estado_vuelo_actual_por_id,
    obtener_vuelo_por_id,
)
from .consultas_catalogo import (
    listar_aerolineas,
    listar_aeronaves,
    listar_aeropuertos,
    listar_tipos_vuelo,
)
from .consultas_informe import agrupar_vuelos_por_aerolinea, listar_vuelos_informe
from .eventos import EventoEstadoVuelo, broadcaster_global

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository. application/ obtiene
# sesion/journal/auditoria/contexto reexportados desde aqui, nunca del
# paquete transversal directamente.
__all__ = [
    "insertar_vuelo",
    "insertar_vuelo_estado",
    "obtener_vuelo_por_id",
    "obtener_estado_vuelo_actual_por_id",
    "obtener_estado_catalogo_por_codigo",
    "estado_vuelo_catalogo",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "broadcaster_global",
    "EventoEstadoVuelo",
    "reintentar_en_conflicto",
    "listar_aerolineas",
    "listar_aeronaves",
    "listar_tipos_vuelo",
    "listar_aeropuertos",
    "listar_vuelos_informe",
    "agrupar_vuelos_por_aerolinea",
    "listar_vuelos",
]
