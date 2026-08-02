"""Verificacion de licencia vigente por modulo (Sprint S1.7, RF-O18,
CU-O20). "Sistema" (el propio Gateway) es el actor -- se ejecuta despues
de autenticar, antes de despachar al router del modulo de negocio.

Vive en aerohub_gateway, no en aerohub_compliance: es un control
transversal de enrutamiento (mismo tipo que el rate limiting ya existente
en esta capa), no una regla de negocio de compliance -- ver
specs/009-compliance-licensing-hub/research.md Decision 1.
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc

from ..domain.licencia import resolver_modulo_de_ruta
from ..infrastructure import existe_licencia_vigente, registrar_auditoria, sesion


class LicenciaNoVigente(Exception):
    def __init__(self, modulo_codigo: str) -> None:
        self.modulo_codigo = modulo_codigo
        super().__init__(f"modulo {modulo_codigo!r} sin licencia vigente")


def verificar_licencia(*, path: str, tenant_id: int | None) -> None:
    """No hace nada (no bloquea) si la ruta no requiere licencia, o si la
    peticion no tiene tenant_id (actor de plataforma sin tenant propio,
    p. ej. aprovisionamiento -- CU-O18). Si la licencia no esta vigente,
    audita el intento (operacion='DENEGADO', ver PN-06/S1.2, el mismo
    valor ya usado para API Key revocada/expirada) y rechaza."""
    modulo_codigo = resolver_modulo_de_ruta(path)
    if modulo_codigo is None or tenant_id is None:
        return

    with sesion() as conn:
        vigente = existe_licencia_vigente(
            conn, tenant_id=tenant_id, modulo_codigo=modulo_codigo, ahora=ahora_utc()
        )
        if not vigente:
            registrar_auditoria(
                conn,
                esquema="tenants",
                tabla="licencia",
                registro_id=tenant_id,
                operacion="DENEGADO",
                valores_nuevos={"modulo": modulo_codigo, "resultado": "sin_licencia_vigente"},
            )
    if not vigente:
        raise LicenciaNoVigente(modulo_codigo)
