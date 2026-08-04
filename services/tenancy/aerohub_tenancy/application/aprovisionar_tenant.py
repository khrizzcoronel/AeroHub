"""CU-O18 -- Aprovisionar nuevo tenant con aislamiento verificado (Sprint
S1.1, Plan §8.1; RF-O01, RNF-P04).

`role_platform_admin` esta creando un tenant y su primer usuario admin --
por definicion, ninguno de los dos existe todavia bajo un tenant_id propio.
Se envuelve en `alcance_global`: es la excepcion nominal y auditada
correcta (ADR-019 G3), no un bypass silencioso -- el motivo y el rol quedan
en cada entrada de journal/auditoria de esta transaccion.
"""

from __future__ import annotations

import contextlib
import secrets
from dataclasses import dataclass

from aerohub_contracts import EnvioDeCorreoFallo
from aerohub_kernel import ahora_utc, generar_id
from aerohub_kernel import hash_credencial as _hash_credencial

from ..domain import Tenant, TenantInvalido
from ..infrastructure import (
    alcance_global,
    enviar_correo,
    escribir_journal,
    insertar_tenant,
    insertar_usuario_admin,
    insertar_usuario_rol,
    obtener_rol_por_codigo,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from .plantillas_correo import mensaje_bienvenida_tenant

_MOTIVO_ALCANCE_GLOBAL = "aprovisionamiento_tenant"
_ROL_APROVISIONAMIENTO = "role_platform_admin"
_ROL_ADMIN_DEL_TENANT = "role_tenant_admin"


@dataclass(frozen=True, slots=True)
class ResultadoAprovisionamiento:
    tenant_id: int
    usuario_admin_id: int
    password_temporal: str  # se muestra UNA sola vez; nunca se persiste en claro


@reintentar_en_conflicto()
def aprovisionar_tenant(
    *,
    codigo: str,
    razon_social: str,
    aeropuerto_id: int,
    plan_id: int,
    email_admin: str,
    nombre_admin: str,
    es_sandbox: bool = False,
) -> ResultadoAprovisionamiento:
    """Crea el tenant y su primer usuario administrador en una unica
    transaccion (P8): si cualquier paso falla, ninguno de los dos persiste.
    """
    # Domain valida ANTES de tocar la base -- fail fast (SRS RNF-M01).
    tenant_id = generar_id()
    Tenant(
        id=tenant_id,
        codigo=codigo,
        razon_social=razon_social,
        aeropuerto_id=aeropuerto_id,
        plan_id=plan_id,
        estado="en_onboarding",
        es_sandbox=es_sandbox,
    )

    usuario_admin_id = generar_id()
    password_temporal = secrets.token_urlsafe(18)
    hash_ = _hash_credencial(password_temporal)

    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_APROVISIONAMIENTO),
        sesion() as conn,
    ):
        insertar_tenant(
            conn,
            id=tenant_id,
            codigo=codigo,
            razon_social=razon_social,
            aeropuerto_id=aeropuerto_id,
            plan_id=plan_id,
            estado="en_onboarding",
            es_sandbox=es_sandbox,
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="tenant",
            operacion="INSERT",
            clave_primaria={"id": tenant_id},
            payload={"id": tenant_id, "codigo": codigo, "estado": "en_onboarding"},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="tenant",
            registro_id=tenant_id,
            operacion="INSERT",
            valores_nuevos={"codigo": codigo, "estado": "en_onboarding"},
            tenant_id=tenant_id,
        )

        insertar_usuario_admin(
            conn,
            id=usuario_admin_id,
            tenant_id=tenant_id,
            email=email_admin,
            hash_credencial=hash_,
            nombre=nombre_admin,
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario",
            operacion="INSERT",
            clave_primaria={"id": usuario_admin_id},
            payload={"id": usuario_admin_id, "tenant_id": tenant_id, "email": email_admin},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario",
            registro_id=usuario_admin_id,
            operacion="INSERT",
            valores_nuevos={"tenant_id": tenant_id, "email": email_admin},
            tenant_id=tenant_id,
        )

        # FIX S1.10 (tasks.md T020): sin esta asignacion, el usuario admin
        # recien creado no tiene ningun rol vigente y nunca podria
        # loguearse (iniciar_sesion.py exige un rol vigente, FR-014).
        rol_admin = obtener_rol_por_codigo(conn, _ROL_ADMIN_DEL_TENANT)
        if rol_admin is None:
            raise TenantInvalido(f"rol {_ROL_ADMIN_DEL_TENANT!r} no encontrado en tenants.rol")
        insertar_usuario_rol(
            conn,
            usuario_id=usuario_admin_id,
            rol_id=rol_admin.id,
            otorgado_por=usuario_admin_id,
            otorgado_en=ahora_utc(),
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="usuario_rol",
            operacion="INSERT",
            clave_primaria={"usuario_id": usuario_admin_id, "rol_id": rol_admin.id},
            payload={"usuario_id": usuario_admin_id, "rol_id": rol_admin.id},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="usuario_rol",
            registro_id=usuario_admin_id,
            operacion="INSERT",
            valores_nuevos={"rol_id": rol_admin.id, "rol_codigo": _ROL_ADMIN_DEL_TENANT},
            tenant_id=tenant_id,
        )

    # Envio de correo DESPUES de que la transaccion confirma -- mismo
    # criterio que P8 para eventos de dominio ("se publican despues de
    # que la transaccion confirma"). A diferencia de invitar_usuario
    # (S1.10), que envia el correo ANTES de persistir porque el correo
    # ES la entrega principal de esa operacion, aca el tenant y su admin
    # YA son el valor entregado -- un fallo de SMTP no debe destruir un
    # aprovisionamiento que de verdad ocurrio. Se degrada en silencio a
    # "solo pantalla" (que ya mostraba la contrasena desde S1.1) en vez
    # de propagar un 502 que le ocultaria password_temporal a quien crea
    # el tenant si justo el correo fallo.
    with contextlib.suppress(EnvioDeCorreoFallo, Exception):
        enviar_correo(
            mensaje_bienvenida_tenant(
                destinatario=email_admin,
                nombre_admin=nombre_admin,
                tenant_razon_social=razon_social,
                password_temporal=password_temporal,
            )
        )

    return ResultadoAprovisionamiento(
        tenant_id=tenant_id,
        usuario_admin_id=usuario_admin_id,
        password_temporal=password_temporal,
    )
