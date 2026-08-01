"""Asignacion manual de puerta a un vuelo (Sprint S1.4, Plan §8.4, RF-O02,
PN-05).

`inicio_previsto`/`fin_previsto` los provee quien asigna -- son la ventana
de OCUPACION de la puerta (que no coincide con `vuelo.std_utc`/`sta_utc`,
el tramo origen-destino completo del vuelo; SDD-DATA-001 §7.5 las modela
como columnas propias de `asignacion_puerta`, independientes). El
asignador automatico (asignacion_automatica.py) si deriva la ventana de
`vuelo.std_utc`/`sta_utc` por ausencia de un dato de ground-ops mas fino
antes de S1.5 (turnaround).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import es_utc, generar_id

from ..domain import (
    AsignacionPuertaInvalida,
    IntervaloOcupado,
    verificar_compatibilidad_envergadura,
    verificar_no_solapamiento,
)
from ..infrastructure import (
    bloquear_puerta_para_asignacion,
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_asignacion_puerta,
    listar_asignaciones_que_ocupan_puerta,
    obtener_puerta_por_id,
    obtener_vuelo_con_envergadura,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class PuertaNoEncontrada(Exception):
    pass


class VueloNoEncontrado(Exception):
    pass


class UsuarioNoIdentificado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoAsignarPuerta:
    asignacion_id: int


@reintentar_en_conflicto()
def asignar_puerta(
    *, vuelo_id: int, puerta_id: int, inicio_previsto: datetime, fin_previsto: datetime
) -> ResultadoAsignarPuerta:
    # Fail fast, sin tocar la base: intervalos_se_solapan() asume que AMBOS
    # limites de cada intervalo son tz-aware (compara directamente contra
    # inicio_previsto/fin_previsto ya leidos de MonetDB, siempre UTC) --
    # un datetime naive (p. ej. un <input type="datetime-local"> del
    # navegador enviado sin sufijo de zona) revienta la comparacion con
    # TypeError en vez de un 422 legible (hallazgo empirico, apps/web).
    if not es_utc(inicio_previsto) or not es_utc(fin_previsto):
        raise AsignacionPuertaInvalida(
            "inicio_previsto y fin_previsto deben ser datetime en UTC (tz-aware)"
        )
    if fin_previsto <= inicio_previsto:
        raise AsignacionPuertaInvalida(
            f"fin_previsto ({fin_previsto}) debe ser posterior a "
            f"inicio_previsto ({inicio_previsto})"
        )

    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("asignar_puerta requiere una sesion con usuario identificado")
    tenant_id = contexto_tenant_id()
    asignacion_id = generar_id()

    with sesion() as conn:
        fila_puerta = obtener_puerta_por_id(conn, puerta_id)
        if fila_puerta is None:
            raise PuertaNoEncontrada(f"puerta {puerta_id} no encontrada")
        fila_vuelo = obtener_vuelo_con_envergadura(conn, vuelo_id)
        if fila_vuelo is None:
            raise VueloNoEncontrado(f"vuelo {vuelo_id} no encontrado")

        verificar_compatibilidad_envergadura(
            envergadura_aeronave_m=fila_vuelo.envergadura_m,
            envergadura_max_puerta_m=fila_puerta.envergadura_max_m,
        )

        # "Bloqueo de fila" ANTES de leer las asignaciones existentes -- ver
        # el docstring de bloquear_puerta_para_asignacion (PN-05, variante
        # concurrente).
        bloquear_puerta_para_asignacion(conn, tenant_id=tenant_id, puerta_id=puerta_id)

        existentes = listar_asignaciones_que_ocupan_puerta(conn, puerta_id=puerta_id)
        verificar_no_solapamiento(
            inicio=inicio_previsto,
            fin=fin_previsto,
            existentes=[
                IntervaloOcupado(inicio=f.inicio_previsto, fin=f.fin_previsto, asignacion_id=f.id)
                for f in existentes
            ],
        )

        insertar_asignacion_puerta(
            conn,
            id=asignacion_id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            puerta_id=puerta_id,
            inicio_previsto=inicio_previsto,
            fin_previsto=fin_previsto,
            asignado_por_usuario_id=usuario_id,
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="asignacion_puerta",
            operacion="INSERT",
            clave_primaria={"id": asignacion_id},
            payload={"id": asignacion_id, "vuelo_id": vuelo_id, "puerta_id": puerta_id},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="asignacion_puerta",
            registro_id=asignacion_id,
            operacion="INSERT",
            valores_nuevos={"vuelo_id": vuelo_id, "puerta_id": puerta_id},
        )

    return ResultadoAsignarPuerta(asignacion_id=asignacion_id)
