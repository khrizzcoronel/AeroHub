"""El agente de rampa marca el inicio de una tarea de turnaround (Sprint
S1.5, CU-O16, paso 2: "Marca inicio de la tarea; el sistema registra el
timestamp y el usuario"). Crea la fila -- no hay tareas pre-creadas sin
agente en el alcance de S1.5 (ver db/ddl/monetdb/11_rampa.sql).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import ahora_utc, generar_id

from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_tarea_turnaround,
    obtener_tipo_tarea_por_id,
    obtener_turnaround_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class TurnaroundNoEncontrado(Exception):
    pass


class TipoTareaNoEncontrado(Exception):
    pass


class UsuarioNoIdentificado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoIniciarTarea:
    tarea_id: int


@reintentar_en_conflicto()
def iniciar_tarea(*, turnaround_id: int, tipo_tarea_id: int) -> ResultadoIniciarTarea:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("iniciar_tarea requiere una sesion con usuario identificado")
    tenant_id = contexto_tenant_id()
    tarea_id = generar_id()

    with sesion() as conn:
        if obtener_turnaround_por_id(conn, turnaround_id) is None:
            raise TurnaroundNoEncontrado(f"turnaround {turnaround_id} no encontrado")
        if obtener_tipo_tarea_por_id(conn, tipo_tarea_id) is None:
            raise TipoTareaNoEncontrado(f"tipo de tarea {tipo_tarea_id} no encontrado")

        inicio_real = ahora_utc()
        insertar_tarea_turnaround(
            conn,
            id=tarea_id,
            tenant_id=tenant_id,
            turnaround_id=turnaround_id,
            tipo_tarea_id=tipo_tarea_id,
            agente_usuario_id=usuario_id,
            inicio_real=inicio_real,
        )
        escribir_journal(
            conn,
            esquema="rampa",
            tabla="tarea_turnaround",
            operacion="INSERT",
            clave_primaria={"id": tarea_id},
            payload={
                "id": tarea_id,
                "turnaround_id": turnaround_id,
                "tipo_tarea_id": tipo_tarea_id,
            },
        )
        registrar_auditoria(
            conn,
            esquema="rampa",
            tabla="tarea_turnaround",
            registro_id=tarea_id,
            operacion="INSERT",
            valores_nuevos={"turnaround_id": turnaround_id, "tipo_tarea_id": tipo_tarea_id},
        )

    return ResultadoIniciarTarea(tarea_id=tarea_id)
