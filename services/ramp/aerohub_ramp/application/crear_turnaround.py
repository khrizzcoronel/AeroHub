"""Creacion manual de turnaround, emparejando vuelo de llegada y salida de
la MISMA aeronave (Sprint S1.5, Plan §8.5, RF-O16; SDD-DATA-001 §8.3).

No hay un CU dedicado a "crear turnaround" en el catalogo de casos de uso
(SRS/analisis v6.0) -- role_ramp_agent es el unico rol con I/Up sobre
`rampa` (97_grants_rampa.sql), asi que tambien crea el turnaround, ademas
de registrar sus tareas (CU-O16).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import generar_id

from ..domain import Turnaround
from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_turnaround,
    obtener_turnaround_por_vuelo_llegada,
    obtener_vuelo_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class VueloNoEncontrado(Exception):
    pass


class TurnaroundYaExiste(Exception):
    pass


class VuelosIncompatibles(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCrearTurnaround:
    turnaround_id: int


@reintentar_en_conflicto()
def crear_turnaround(
    *,
    vuelo_llegada_id: int,
    vuelo_salida_id: int,
    inicio_previsto: datetime,
    fin_previsto: datetime,
) -> ResultadoCrearTurnaround:
    tenant_id = contexto_tenant_id()
    turnaround_id = generar_id()

    with sesion() as conn:
        if obtener_turnaround_por_vuelo_llegada(conn, vuelo_llegada_id) is not None:
            raise TurnaroundYaExiste(
                f"el vuelo de llegada {vuelo_llegada_id} ya tiene un turnaround"
            )

        fila_llegada = obtener_vuelo_por_id(conn, vuelo_llegada_id)
        if fila_llegada is None:
            raise VueloNoEncontrado(f"vuelo {vuelo_llegada_id} no encontrado")
        fila_salida = obtener_vuelo_por_id(conn, vuelo_salida_id)
        if fila_salida is None:
            raise VueloNoEncontrado(f"vuelo {vuelo_salida_id} no encontrado")

        if fila_llegada.sentido != "L":
            raise VuelosIncompatibles(
                f"vuelo_llegada_id ({vuelo_llegada_id}) debe tener sentido 'L' "
                f"(tiene {fila_llegada.sentido!r})"
            )
        if fila_salida.sentido != "S":
            raise VuelosIncompatibles(
                f"vuelo_salida_id ({vuelo_salida_id}) debe tener sentido 'S' "
                f"(tiene {fila_salida.sentido!r})"
            )
        if fila_llegada.aeronave_id != fila_salida.aeronave_id:
            raise VuelosIncompatibles(
                "vuelo_llegada_id y vuelo_salida_id deben ser de la MISMA aeronave"
            )

        # Domain valida el resto de invariantes (vuelos distintos, ventana
        # tz-aware, fin>inicio) por construccion -- fail fast antes del
        # INSERT, mismo principio que aerohub_aodb.domain.Vuelo.
        Turnaround(
            id=turnaround_id,
            tenant_id=tenant_id,
            vuelo_llegada_id=vuelo_llegada_id,
            vuelo_salida_id=vuelo_salida_id,
            aeronave_id=fila_llegada.aeronave_id,
            inicio_previsto=inicio_previsto,
            fin_previsto=fin_previsto,
            estado="planificado",
        )

        insertar_turnaround(
            conn,
            id=turnaround_id,
            tenant_id=tenant_id,
            vuelo_llegada_id=vuelo_llegada_id,
            vuelo_salida_id=vuelo_salida_id,
            aeronave_id=fila_llegada.aeronave_id,
            inicio_previsto=inicio_previsto,
            fin_previsto=fin_previsto,
        )
        escribir_journal(
            conn,
            esquema="rampa",
            tabla="turnaround",
            operacion="INSERT",
            clave_primaria={"id": turnaround_id},
            payload={
                "id": turnaround_id,
                "vuelo_llegada_id": vuelo_llegada_id,
                "vuelo_salida_id": vuelo_salida_id,
            },
        )
        registrar_auditoria(
            conn,
            esquema="rampa",
            tabla="turnaround",
            registro_id=turnaround_id,
            operacion="INSERT",
            valores_nuevos={
                "vuelo_llegada_id": vuelo_llegada_id,
                "vuelo_salida_id": vuelo_salida_id,
            },
        )

    return ResultadoCrearTurnaround(turnaround_id=turnaround_id)
