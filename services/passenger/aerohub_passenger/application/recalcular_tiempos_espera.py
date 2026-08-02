"""Motor de estimacion de tiempos de espera (CU-O19, Sprint S1.6, RF-O17).
"Sistema" como actor -- agrega ops.asignacion_puerta (ocupacion de puerta)
y rampa.turnaround (duracion real de procesos) del terminal/fecha, sin
ningun dato individual de pasajero (PN-11).

Invocacion explicita via API (research.md Decision 2) -- la responsabilidad
de invocarlo cada <= 15 min (RF-O17) es operativa, no de este modulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aerohub_kernel import ahora_utc, generar_id

from ..domain import agregacion_por_franja, descarta_por_muestra_insuficiente, franja_de
from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_o_actualizar_tiempo_espera,
    listar_asignaciones_completadas_de_terminal,
    listar_turnarounds_de_vuelos,
    obtener_franja_existente,
    obtener_terminal_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class TerminalNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoRecalcular:
    franjas_actualizadas: int
    franjas_descartadas_por_muestra_insuficiente: int


@reintentar_en_conflicto()
def recalcular_tiempos_espera(
    *, terminal_id: int, fecha: date, franja_minutos: int
) -> ResultadoRecalcular:
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        if obtener_terminal_por_id(conn, terminal_id) is None:
            raise TerminalNoEncontrado(f"terminal {terminal_id} no encontrado")

        asignaciones = listar_asignaciones_completadas_de_terminal(
            conn, terminal_id=terminal_id, fecha=fecha
        )

        # Segunda senal (rampa.turnaround): duracion real de los procesos
        # de rampa del mismo vuelo, cuando existe -- combinada con la
        # ocupacion de puerta en la MISMA franja (bucketizada por el
        # inicio_previsto de la asignacion, unico dato con hora del dia
        # disponible en ambas fuentes).
        vuelo_ids = [a.vuelo_id for a in asignaciones]
        turnarounds_por_vuelo: dict[int, list] = {}
        for t in listar_turnarounds_de_vuelos(conn, vuelo_ids=vuelo_ids):
            for v_id in (t.vuelo_llegada_id, t.vuelo_salida_id):
                turnarounds_por_vuelo.setdefault(v_id, []).append(t)

        muestras_por_franja: dict[tuple, list[Decimal]] = {}
        for a in asignaciones:
            franja_inicio, franja_fin = franja_de(
                a.inicio_previsto.timetz().replace(tzinfo=None), franja_minutos=franja_minutos
            )
            clave = (franja_inicio, franja_fin)
            duracion_asignacion = Decimal(
                (a.fin_real - a.inicio_real).total_seconds() / 60
            )
            muestras_por_franja.setdefault(clave, []).append(duracion_asignacion)

            for t in turnarounds_por_vuelo.get(a.vuelo_id, []):
                duracion_turnaround = Decimal((t.fin_real - t.inicio_real).total_seconds() / 60)
                muestras_por_franja[clave].append(duracion_turnaround)

        ahora = ahora_utc()
        franjas_actualizadas = 0
        franjas_descartadas = 0
        for (franja_inicio, franja_fin), duraciones in muestras_por_franja.items():
            resultado = agregacion_por_franja(duraciones)
            if descarta_por_muestra_insuficiente(resultado.muestra_n):
                franjas_descartadas += 1
                continue

            existente = obtener_franja_existente(
                conn, terminal_id=terminal_id, fecha=fecha, franja_inicio=franja_inicio
            )
            fila_id = existente.id if existente is not None else generar_id()
            insertar_o_actualizar_tiempo_espera(
                conn,
                id=fila_id,
                tenant_id=tenant_id,
                terminal_id=terminal_id,
                fecha=fecha,
                franja_inicio=franja_inicio,
                franja_fin=franja_fin,
                minutos_estimados=resultado.minutos_estimados,
                muestra_n=resultado.muestra_n,
                calculado_en=ahora,
                existente_id=existente.id if existente is not None else None,
            )
            escribir_journal(
                conn,
                esquema="billing",
                tabla="tiempo_espera_agregado",
                operacion="UPDATE" if existente is not None else "INSERT",
                clave_primaria={"id": fila_id},
                payload={"terminal_id": terminal_id, "franja_inicio": franja_inicio.isoformat()},
            )
            registrar_auditoria(
                conn,
                esquema="billing",
                tabla="tiempo_espera_agregado",
                registro_id=fila_id,
                operacion="UPDATE" if existente is not None else "INSERT",
                valores_nuevos={
                    "minutos_estimados": str(resultado.minutos_estimados),
                    "muestra_n": resultado.muestra_n,
                },
            )
            franjas_actualizadas += 1

    return ResultadoRecalcular(
        franjas_actualizadas=franjas_actualizadas,
        franjas_descartadas_por_muestra_insuficiente=franjas_descartadas,
    )
