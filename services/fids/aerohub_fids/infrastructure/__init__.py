from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import alcance_global, contexto_tenant_id, contexto_usuario_id

from . import (
    alcances as _alcances,  # noqa: F401 -- side effect: registra G1 de plantilla_fids/pantalla_fids
)
from .comandos import (
    actualizar_plantilla_de_pantalla,
    insertar_pantalla,
    insertar_plantilla,
    marcar_pantalla_sin_senal,
    registrar_heartbeat,
)
from .consultas import (
    listar_pantallas,
    listar_pantallas_para_monitoreo,
    listar_plantillas,
    obtener_pantalla_por_codigo,
    obtener_pantalla_por_id,
    obtener_plantilla_por_id,
    obtener_ultima_version_plantilla,
)
from .consultas_catalogo import listar_terminales
from .contexto_ws import limpiar_contexto_ws, poblar_contexto_ws
from .eventos import EventoPlantillaPantalla, broadcaster_global

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository. application/ obtiene
# sesion/journal/auditoria/contexto reexportados desde aqui, nunca del
# paquete transversal directamente.
__all__ = [
    "insertar_plantilla",
    "insertar_pantalla",
    "actualizar_plantilla_de_pantalla",
    "registrar_heartbeat",
    "marcar_pantalla_sin_senal",
    "obtener_plantilla_por_id",
    "obtener_pantalla_por_id",
    "obtener_pantalla_por_codigo",
    "obtener_ultima_version_plantilla",
    "listar_pantallas_para_monitoreo",
    "listar_plantillas",
    "listar_pantallas",
    "listar_terminales",
    "broadcaster_global",
    "EventoPlantillaPantalla",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "reintentar_en_conflicto",
    "alcance_global",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "poblar_contexto_ws",
    "limpiar_contexto_ws",
]
