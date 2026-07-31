"""Verificacion de API Key contra tenants.api_key (Sprint S1.2, Plan §8.2,
RF-O12, PN-06).

Declara su PROPIA Table de solo lectura sobre `tenants.api_key` en vez de
importar `aerohub_tenancy` -- el contrato de independencia de modulos
(.importlinter, "sin-importacion-cruzada-entre-modulos") prohibe que
aerohub_gateway importe cualquier otro modulo de negocio, incluso solo su
domain/. El guardian de tenant (ADR-019 G1/G2) resuelve el alcance por
(esquema, tabla), no por que modulo declaro el objeto Table de SQLAlchemy,
asi que esta declaracion local convive sin conflicto con la de
aerohub_tenancy (misma tabla fisica, dos objetos Python independientes).

Por el mismo motivo, la logica de "esta vigente" (estado + expiracion) se
reimplementa aqui en dos lineas en vez de reusar
`aerohub_tenancy.domain.ApiKey.esta_vigente` -- duplicacion pequeña y
deliberada, consecuencia directa de la independencia real entre modulos.
"""

from __future__ import annotations

from datetime import datetime

from aerohub_kernel import ahora_utc, verificar_credencial
from aerohub_repository import registrar_auditoria, sesion
from aerohub_repository.contexto import alcance_global
from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, select

from ..domain import Identidad

_metadata = MetaData()

_ROL_PARA_LA_CONSULTA = "role_platform_admin"  # SET ROLE para leer tenants.api_key (G3)
_ROL_DE_LA_IDENTIDAD = "role_operations_controller"  # rol real de la peticion autenticada
_MOTIVO_ALCANCE_GLOBAL = "autenticacion_api_key"

# Scopes por defecto para una identidad autenticada por API Key: acceso de
# lectura/escritura sobre vuelos del tenant propietario. Deliberadamente
# NO se otorgan scopes de administracion (tenants:administrar,
# api-keys:administrar) -- SRS §4 exige MFA para role_tenant_admin, que una
# API Key (secreto estatico, sin segundo factor) no puede satisfacer.
SCOPES_API_KEY = frozenset({"vuelos:leer", "vuelos:escribir"})

api_key = Table(
    "api_key",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("prefijo", String(12)),
    Column("hash_secreto", String(255)),
    Column("expira_en", DateTime(timezone=True)),
    Column("estado", String(20)),
    schema="tenants",
)


def _esta_vigente(estado: str, expira_en: datetime | None, ahora: datetime) -> bool:
    if estado != "activa":
        return False
    return expira_en is None or ahora < expira_en


def verificar_api_key(prefijo: str, secreto: str) -> Identidad | None:
    ahora = ahora_utc()
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        fila = conn.execute(select(api_key).where(api_key.c.prefijo == prefijo)).first()
        if fila is None:
            # Prefijo inexistente: nada que auditar contra una fila real.
            return None

        vigente = _esta_vigente(fila.estado, fila.expira_en, ahora)
        coincide = vigente and verificar_credencial(secreto, fila.hash_secreto)

        if not coincide:
            # PN-06: revocada, expirada o secreto incorrecto -> evento
            # auditado igual (no se distingue el motivo en la respuesta ni
            # en el log de aplicacion, solo en el detalle interno de
            # auditoria, para no darle a un atacante senales sobre cual
            # de los casos aplica).
            registrar_auditoria(
                conn,
                esquema="tenants",
                tabla="api_key",
                registro_id=fila.id,
                operacion="DENEGADO",
                valores_nuevos={"estado_en_el_momento": fila.estado},
                tenant_id=fila.tenant_id,
            )
            return None

        return Identidad(
            tenant_id=fila.tenant_id,
            rol=_ROL_DE_LA_IDENTIDAD,
            usuario_id=None,
            scopes=SCOPES_API_KEY,
        )
