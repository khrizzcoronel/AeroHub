"""Asignacion automatica de puertas por programacion lineal (Sprint S1.4,
Plan §8.4: "asignacion automatica por programacion lineal (PuLP)
considerando envergadura, tipo contacto/remota y ventanas").

Modelo: variables binarias x[vuelo_id, puerta_id] = 1 si el vuelo se asigna
a esa puerta. Restricciones duras: (1) cada vuelo se asigna a A LO SUMO
una puerta compatible en envergadura; (2) dos vuelos cuyas ventanas
[std_utc, sta_utc) se solapan NUNCA comparten la misma puerta -- mismo
criterio que domain.intervalos_se_solapan, aplicado por pares. Objetivo:
maximizar vuelos asignados y, como desempate secundario, preferir puertas
'contacto' sobre 'remota' (Plan §8.4 la menciona como dimension a
considerar) -- se modela como preferencia en el objetivo, NO como
restriccion dura: sin un requisito explicito de que vuelo necesita
contacto, una restriccion rechazaria planes factibles sin motivo
declarado.

La ventana de cada vuelo se deriva de `vuelo.std_utc`/`sta_utc` (el tramo
origen-destino completo) por ausencia de un dato de ground-ops mas fino
antes de S1.5 (turnaround) -- misma simplificacion documentada en
asignar_puerta.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import pulp

from ..domain import (
    AsignacionPuertaInvalida,
    PuertaIncompatible,
    SolapamientoPuertaInvalido,
    intervalos_se_solapan,
)
from ..infrastructure import listar_puertas, listar_vuelos_sin_asignacion_con_envergadura, sesion
from .asignar_puerta import PuertaNoEncontrada, VueloNoEncontrado, asignar_puerta

_PESO_BASE = 10
_PREFERENCIA_TIPO = {"contacto": 1, "remota": 0}


@dataclass(frozen=True, slots=True)
class ResultadoAsignacionAutomatica:
    asignados: tuple[int, ...]
    sin_asignar: tuple[int, ...]


def ejecutar_asignacion_automatica() -> ResultadoAsignacionAutomatica:
    with sesion() as conn:
        vuelos = listar_vuelos_sin_asignacion_con_envergadura(conn)
        puertas = listar_puertas(conn)

    if not vuelos or not puertas:
        return ResultadoAsignacionAutomatica(
            asignados=(), sin_asignar=tuple(v.id for v in vuelos)
        )

    pares_compatibles = [
        (v, p) for v in vuelos for p in puertas if v.envergadura_m <= p.envergadura_max_m
    ]

    problema = pulp.LpProblem("asignacion_puertas", pulp.LpMaximize)
    x = {
        (v.id, p.id): pulp.LpVariable(f"x_{v.id}_{p.id}", cat="Binary")
        for v, p in pares_compatibles
    }

    puertas_por_id = {p.id: p for p in puertas}
    problema += pulp.lpSum(
        variable * (_PESO_BASE + _PREFERENCIA_TIPO.get(puertas_por_id[puerta_id].tipo, 0))
        for (_, puerta_id), variable in x.items()
    )

    for v in vuelos:
        variables_del_vuelo = [x[(v.id, p.id)] for p in puertas if (v.id, p.id) in x]
        if variables_del_vuelo:
            problema += pulp.lpSum(variables_del_vuelo) <= 1

    for p in puertas:
        vuelos_de_esta_puerta = [v for v in vuelos if (v.id, p.id) in x]
        for i, v_a in enumerate(vuelos_de_esta_puerta):
            for v_b in vuelos_de_esta_puerta[i + 1 :]:
                if intervalos_se_solapan(v_a.std_utc, v_a.sta_utc, v_b.std_utc, v_b.sta_utc):
                    problema += x[(v_a.id, p.id)] + x[(v_b.id, p.id)] <= 1

    problema.solve(pulp.PULP_CBC_CMD(msg=False))

    vuelos_por_id = {v.id: v for v in vuelos}
    asignados_ids: list[int] = []
    for (vuelo_id, puerta_id), variable in x.items():
        if pulp.value(variable) != 1:
            continue
        v = vuelos_por_id[vuelo_id]
        try:
            asignar_puerta(
                vuelo_id=vuelo_id,
                puerta_id=puerta_id,
                inicio_previsto=v.std_utc,
                fin_previsto=v.sta_utc,
            )
        except (
            SolapamientoPuertaInvalido,
            PuertaIncompatible,
            AsignacionPuertaInvalida,
            PuertaNoEncontrada,
            VueloNoEncontrado,
        ):
            # El plan del solver es un SNAPSHOT -- si el estado real cambio
            # entre el listado y el envio (otra asignacion concurrente), esta
            # asignacion puntual se descarta sin abortar el resto del plan.
            continue
        asignados_ids.append(vuelo_id)

    sin_asignar_ids = tuple(v.id for v in vuelos if v.id not in asignados_ids)
    return ResultadoAsignacionAutomatica(
        asignados=tuple(asignados_ids), sin_asignar=sin_asignar_ids
    )
