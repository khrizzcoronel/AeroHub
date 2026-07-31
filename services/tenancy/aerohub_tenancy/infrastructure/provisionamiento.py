"""Escritura de tenants.tenant y tenants.usuario para CU-O18 (Sprint S1.1).

Solo persiste: los valores ya llegan validados por domain/ y con `id`
generado por application/ (packages/kernel/identificador.py). No decide
alcance_global ni journal/auditoria -- eso lo orquesta application/, que
es quien conoce la transaccion completa.
"""

from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.engine import Connection

from .tablas import tenant, usuario


def insertar_tenant(
    conn: Connection,
    *,
    id: int,
    codigo: str,
    razon_social: str,
    aeropuerto_id: int,
    plan_id: int,
    estado: str,
    es_sandbox: bool = False,
) -> None:
    conn.execute(
        insert(tenant).values(
            id=id,
            codigo=codigo,
            razon_social=razon_social,
            aeropuerto_id=aeropuerto_id,
            plan_id=plan_id,
            estado=estado,
            es_sandbox=es_sandbox,
        )
    )


def insertar_usuario_admin(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    email: str,
    hash_credencial: str,
    nombre: str,
) -> None:
    conn.execute(
        insert(usuario).values(
            id=id,
            tenant_id=tenant_id,
            email=email,
            hash_credencial=hash_credencial,
            nombre=nombre,
            estado="activo",
            mfa_habilitado=False,
        )
    )
