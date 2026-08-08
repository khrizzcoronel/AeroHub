from aerohub_repository import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from aerohub_repository.contexto import (
    ContextoTenantAusente,
    alcance_global,
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
)

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1 de tenants.*
from .comandos_api_key import actualizar_estado_api_key, insertar_api_key, marcar_api_key_rotada
from .comandos_identidad import (
    actualizar_aerolinea_usuario,
    actualizar_estado_usuario,
    actualizar_ultimo_acceso,
    consumir_token,
    fijar_bloqueo,
    insertar_intento_acceso,
    insertar_invitacion,
    insertar_sesion,
    insertar_token_acceso,
    insertar_usuario_invitado,
    insertar_usuario_rol,
    invalidar_tokens,
    marcar_correo_verificado,
    marcar_invitacion_aceptada,
    marcar_password_cambiada,
    reasignar_rol_usuario,
    revocar_sesion,
    revocar_sesiones_del_usuario,
)
from .comandos_tenant import (
    actualizar_tenant,
    cambiar_estado_tenant,
    eliminar_tenant_y_relaciones_db,
)
from .consultas import (
    listar_api_keys_del_tenant,
    obtener_api_key_por_id,
    obtener_usuario_con_rol_por_id,
    obtener_usuario_por_id,
)
from .consultas_catalogo import listar_aeropuertos, listar_planes
from .consultas_identidad import (
    contar_intentos_fallidos_recientes,
    listar_roles_vigentes_del_usuario,
    listar_tokens_previos_no_consumidos,
    listar_usuarios_del_tenant,
    obtener_invitacion_por_token_id,
    obtener_rol_por_codigo,
    obtener_sesion_por_id,
    obtener_tenant_por_id_global,
    obtener_token_vigente_por_id,
    obtener_usuario_por_email,
    obtener_usuario_por_id_global,
)
from .consultas_informe import agrupar_tenants_por_plan_estado, listar_tenants_informe
from .consultas_tenant import (
    existe_tenant_codigo,
    existe_usuario_email,
    listar_tenants,
    obtener_tenant_por_id,
)
from .correo_registro import configurar_adaptador_correo, enviar_correo
from .correo_smtp import crear_adaptador_smtp_desde_entorno
from .licencia import existe_licencia_vigente, listar_licencias_del_tenant
from .provisionamiento import insertar_tenant, insertar_usuario_admin

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository. application/ obtiene
# sesion/journal/auditoria/contexto reexportados desde aqui, nunca del
# paquete transversal directamente.
__all__ = [
    "obtener_usuario_por_id",
    "obtener_usuario_con_rol_por_id",
    "obtener_api_key_por_id",
    "insertar_tenant",
    "insertar_usuario_admin",
    "insertar_api_key",
    "actualizar_estado_api_key",
    "marcar_api_key_rotada",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "alcance_global",
    "contexto_tenant_id",
    "contexto_usuario_id",
    "contexto_rol_actor",
    "ContextoTenantAusente",
    "reintentar_en_conflicto",
    "obtener_usuario_por_email",
    "obtener_usuario_por_id_global",
    "listar_roles_vigentes_del_usuario",
    "contar_intentos_fallidos_recientes",
    "obtener_sesion_por_id",
    "obtener_token_vigente_por_id",
    "listar_tokens_previos_no_consumidos",
    "obtener_invitacion_por_token_id",
    "obtener_tenant_por_id_global",
    "obtener_rol_por_codigo",
    "insertar_intento_acceso",
    "insertar_sesion",
    "revocar_sesion",
    "revocar_sesiones_del_usuario",
    "actualizar_ultimo_acceso",
    "fijar_bloqueo",
    "marcar_password_cambiada",
    "marcar_correo_verificado",
    "insertar_token_acceso",
    "consumir_token",
    "invalidar_tokens",
    "insertar_invitacion",
    "marcar_invitacion_aceptada",
    "insertar_usuario_invitado",
    "insertar_usuario_rol",
    "reasignar_rol_usuario",
    "actualizar_aerolinea_usuario",
    "actualizar_estado_usuario",
    "existe_licencia_vigente",
    "enviar_correo",
    "configurar_adaptador_correo",
    "crear_adaptador_smtp_desde_entorno",
    "listar_aeropuertos",
    "listar_planes",
    "listar_tenants",
    "obtener_tenant_por_id",
    "actualizar_tenant",
    "cambiar_estado_tenant",
    "eliminar_tenant_y_relaciones_db",
    "existe_tenant_codigo",
    "existe_usuario_email",
    "listar_usuarios_del_tenant",
    "listar_api_keys_del_tenant",
    "listar_licencias_del_tenant",
    "listar_tenants_informe",
    "agrupar_tenants_por_plan_estado",
]
