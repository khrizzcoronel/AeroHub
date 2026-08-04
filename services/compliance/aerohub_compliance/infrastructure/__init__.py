from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import contexto_rol_actor, contexto_tenant_id, contexto_usuario_id

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1
from .comandos import (
    actualizar_causa_raiz_post_mortem,
    completar_post_mortem_accion,
    insertar_acceso_auditor,
    insertar_control_soc2,
    insertar_evidencia_soc2,
    insertar_incidente_seguridad,
    insertar_post_mortem,
    insertar_post_mortem_accion,
    insertar_reporte_dgac,
    insertar_tipo_incidente,
    insertar_tipo_reporte_regulatorio,
    publicar_post_mortem,
)
from .consultas import (
    listar_acciones_de_post_mortem,
    listar_accesos_auditor,
    listar_evidencia_soc2,
    listar_incidentes,
    listar_post_mortems,
    listar_reportes_dgac,
    obtener_post_mortem_accion_por_id,
    obtener_post_mortem_por_id,
    obtener_tipo_incidente_por_id,
)
from .consultas_catalogo import (
    listar_controles_soc2,
    listar_tipos_incidente,
    listar_tipos_reporte_regulatorio,
)
from .consultas_informe import agrupar_reportes_dgac_por_tipo, listar_eventos_auditoria_informe

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository.
__all__ = [
    "obtener_tipo_incidente_por_id",
    "listar_incidentes",
    "obtener_post_mortem_por_id",
    "listar_acciones_de_post_mortem",
    "obtener_post_mortem_accion_por_id",
    "insertar_tipo_incidente",
    "insertar_incidente_seguridad",
    "insertar_tipo_reporte_regulatorio",
    "insertar_reporte_dgac",
    "insertar_acceso_auditor",
    "insertar_control_soc2",
    "insertar_evidencia_soc2",
    "insertar_post_mortem",
    "actualizar_causa_raiz_post_mortem",
    "publicar_post_mortem",
    "insertar_post_mortem_accion",
    "completar_post_mortem_accion",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "reintentar_en_conflicto",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "contexto_rol_actor",
    "listar_eventos_auditoria_informe",
    "agrupar_reportes_dgac_por_tipo",
    "listar_post_mortems",
    "listar_reportes_dgac",
    "listar_accesos_auditor",
    "listar_evidencia_soc2",
    "listar_tipos_incidente",
    "listar_tipos_reporte_regulatorio",
    "listar_controles_soc2",
]
