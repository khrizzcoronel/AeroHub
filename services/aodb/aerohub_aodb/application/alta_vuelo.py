"""Alta de vuelo (Sprint S1.1, Plan §8.1; RF-O02 parcial -- el vuelo en si,
sin asignacion de puerta, que llega en S1.4).

El `tenant_id` SIEMPRE viene de `contexto_tenant_id()` (P2, ADR-014) -- la
firma de esta funcion no acepta un tenant_id como parametro, precisamente
para que sea estructuralmente imposible que un cuerpo de peticion
malicioso lo inyecte (PN-02): aunque el llamador (api/) reciba un campo
`tenant_id` en el JSON, este caso de uso lo ignora por diseno.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from aerohub_kernel import generar_id

from ..domain import Vuelo
from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_vuelo,
    registrar_auditoria,
    sesion,
)


@dataclass(frozen=True, slots=True)
class ResultadoAltaVuelo:
    vuelo_id: int


def alta_vuelo(
    *,
    aerolinea_id: int,
    aeronave_id: int,
    numero_vuelo: str,
    tipo_vuelo_id: int,
    fecha_operacion: date,
    sentido: str,
    aeropuerto_origen_id: int,
    aeropuerto_destino_id: int,
    sta_utc: datetime,
    std_utc: datetime,
    pax_estimado: int | None = None,
) -> ResultadoAltaVuelo:
    tenant_id = contexto_tenant_id()
    vuelo_id = generar_id()

    # Domain valida ANTES de tocar la base -- fail fast (SRS RNF-M01).
    Vuelo(
        id=vuelo_id,
        tenant_id=tenant_id,
        aerolinea_id=aerolinea_id,
        aeronave_id=aeronave_id,
        numero_vuelo=numero_vuelo,
        tipo_vuelo_id=tipo_vuelo_id,
        fecha_operacion=fecha_operacion.isoformat(),
        sentido=sentido,
        aeropuerto_origen_id=aeropuerto_origen_id,
        aeropuerto_destino_id=aeropuerto_destino_id,
        sta_utc=sta_utc,
        std_utc=std_utc,
        pax_estimado=pax_estimado,
    )

    with sesion() as conn:
        insertar_vuelo(
            conn,
            id=vuelo_id,
            tenant_id=tenant_id,
            aerolinea_id=aerolinea_id,
            aeronave_id=aeronave_id,
            numero_vuelo=numero_vuelo,
            tipo_vuelo_id=tipo_vuelo_id,
            fecha_operacion=fecha_operacion,
            sentido=sentido,
            aeropuerto_origen_id=aeropuerto_origen_id,
            aeropuerto_destino_id=aeropuerto_destino_id,
            sta_utc=sta_utc,
            std_utc=std_utc,
            pax_estimado=pax_estimado,
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="vuelo",
            operacion="INSERT",
            clave_primaria={"id": vuelo_id},
            payload={"id": vuelo_id, "numero_vuelo": numero_vuelo, "sentido": sentido},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="vuelo",
            registro_id=vuelo_id,
            operacion="INSERT",
            valores_nuevos={"numero_vuelo": numero_vuelo, "sentido": sentido},
        )

    return ResultadoAltaVuelo(vuelo_id=vuelo_id)
