"""Gestion de API Keys (Sprint S1.2, Plan §8.2, RF-O12).

`crear_api_key` es el UNICO lugar donde el secreto en claro existe -- se
genera, se hashea y se descarta antes de que la funcion retorne. Si se
pierde, no hay forma de recuperarlo (solo rotar/crear una nueva), igual que
`aprovisionar_tenant` con la password temporal.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc, generar_id, hash_credencial

from ..domain import ApiKey
from ..infrastructure import (
    actualizar_estado_api_key,
    contexto_tenant_id,
    escribir_journal,
    insertar_api_key,
    obtener_api_key_por_id,
    registrar_auditoria,
    sesion,
)


class ApiKeyNoEncontrada(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCrearApiKey:
    api_key_id: int
    api_key_en_claro: str  # "{prefijo}.{secreto}" -- se muestra UNA sola vez


def crear_api_key(*, expira_en: datetime | None = None) -> ResultadoCrearApiKey:
    tenant_id = contexto_tenant_id()
    api_key_id = generar_id()
    prefijo = secrets.token_hex(6)
    secreto = secrets.token_urlsafe(32)
    hash_secreto = hash_credencial(secreto)
    creada_en = ahora_utc()

    # Domain valida ANTES de tocar la base -- fail fast (SRS RNF-M01).
    ApiKey(
        id=api_key_id,
        tenant_id=tenant_id,
        prefijo=prefijo,
        hash_secreto=hash_secreto,
        creada_en=creada_en,
        estado="activa",
        expira_en=expira_en,
    )

    with sesion() as conn:
        insertar_api_key(
            conn,
            id=api_key_id,
            tenant_id=tenant_id,
            prefijo=prefijo,
            hash_secreto=hash_secreto,
            creada_en=creada_en,
            expira_en=expira_en,
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="api_key",
            operacion="INSERT",
            clave_primaria={"id": api_key_id},
            payload={"id": api_key_id, "prefijo": prefijo},
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="api_key",
            registro_id=api_key_id,
            operacion="INSERT",
            valores_nuevos={"prefijo": prefijo, "estado": "activa"},
        )

    return ResultadoCrearApiKey(api_key_id=api_key_id, api_key_en_claro=f"{prefijo}.{secreto}")


def revocar_api_key(*, api_key_id: int) -> None:
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        # PN-01: la api_key de otro tenant se ve identica a una inexistente.
        if obtener_api_key_por_id(conn, api_key_id) is None:
            raise ApiKeyNoEncontrada(f"api_key {api_key_id} no encontrada")

        actualizar_estado_api_key(conn, id=api_key_id, tenant_id=tenant_id, estado="revocada")
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="api_key",
            operacion="UPDATE",
            clave_primaria={"id": api_key_id},
            payload={"id": api_key_id, "estado": "revocada"},
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="api_key",
            registro_id=api_key_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "revocada"},
        )
