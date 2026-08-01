"""El agente de rampa marca el fin de una tarea de turnaround; el sistema
calcula la duracion y, si supera el estandar del tipo de tarea, genera una
incidencia de rampa EN LA MISMA TRANSACCION (Sprint S1.5, CU-O16 pasos 3-4;
RF-O16: "incidencia generada < 60s tras superar el estandar").

La deteccion es SINCRONICA con el propio cierre de la tarea, no un ciclo
periodico de fondo: el momento en que se CONOCE la duracion real es
exactamente el momento en que se marca el fin -- a diferencia de RNF-R04
(S1.3, deteccion de pantalla FIDS sin senal), que si necesitaba sondeo
periodico porque "silencio" es la AUSENCIA de un evento, no algo que un
evento explicito dispare. Aqui el propio POST de finalizar_tarea es el
evento; <60s se cumple por construccion (segundos, no un ciclo de
sondeo), y se mide explicitamente en la prueba de integracion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import es_utc, generar_id

from ..domain import excede_estandar, severidad_por_desviacion
from ..infrastructure import (
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    finalizar_tarea_turnaround,
    insertar_incidencia_rampa,
    obtener_tarea_turnaround_por_id,
    obtener_tipo_incidencia_por_codigo,
    obtener_tipo_tarea_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)

_ROL_CON_ACCESO_RESTRINGIDO = "role_ramp_agent"
_CODIGO_TIPO_INCIDENCIA_DESVIACION = "desviacion_estandar"


class TareaNoEncontrada(Exception):
    pass


class TareaTurnaroundInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoFinalizarTarea:
    tarea_id: int
    duracion_minutos: float
    incidencia_generada: bool


@reintentar_en_conflicto()
def finalizar_tarea(*, tarea_id: int, fin_real: datetime) -> ResultadoFinalizarTarea:
    if not es_utc(fin_real):
        raise TareaTurnaroundInvalida("fin_real debe ser datetime en UTC (tz-aware)")

    tenant_id = contexto_tenant_id()
    rol_actor = contexto_rol_actor()

    with sesion() as conn:
        fila_tarea = obtener_tarea_turnaround_por_id(conn, tarea_id)
        if fila_tarea is None:
            raise TareaNoEncontrada(f"tarea {tarea_id} no encontrada")
        if (
            rol_actor == _ROL_CON_ACCESO_RESTRINGIDO
            and fila_tarea.agente_usuario_id != contexto_usuario_id()
        ):
            # Minimo privilegio de role_ramp_agent (Plan §8.5): 404, nunca
            # 403 -- no confirma que la tarea de otro agente existe (PN-01).
            raise TareaNoEncontrada(f"tarea {tarea_id} no encontrada")
        if fin_real < fila_tarea.inicio_real:
            raise TareaTurnaroundInvalida(
                f"fin_real ({fin_real}) no puede ser anterior a "
                f"inicio_real ({fila_tarea.inicio_real})"
            )

        fila_tipo = obtener_tipo_tarea_por_id(conn, fila_tarea.tipo_tarea_id)
        if fila_tipo is None:
            # fk_tarea_turnaround_tipo_tarea garantiza que esto no ocurra --
            # RuntimeError, no assert (bandit B101: un assert desaparece
            # bajo bytecode optimizado, esta comprobacion debe quedarse).
            raise RuntimeError(f"tipo_tarea {fila_tarea.tipo_tarea_id} referenciado sin existir")

        duracion_minutos = (fin_real - fila_tarea.inicio_real).total_seconds() / 60

        finalizar_tarea_turnaround(conn, id=tarea_id, tenant_id=tenant_id, fin_real=fin_real)
        escribir_journal(
            conn,
            esquema="rampa",
            tabla="tarea_turnaround",
            operacion="UPDATE",
            clave_primaria={"id": tarea_id},
            payload={"id": tarea_id, "estado": "completada"},
        )
        registrar_auditoria(
            conn,
            esquema="rampa",
            tabla="tarea_turnaround",
            registro_id=tarea_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "completada", "duracion_minutos": duracion_minutos},
        )

        incidencia_generada = excede_estandar(
            duracion_minutos=duracion_minutos,
            duracion_estandar_min=fila_tipo.duracion_estandar_min,
        )
        if incidencia_generada:
            tipo_incidencia = obtener_tipo_incidencia_por_codigo(
                conn, _CODIGO_TIPO_INCIDENCIA_DESVIACION
            )
            if tipo_incidencia is None:
                # Sembrado por db/seeds/generate.py -- si falta, el entorno
                # no esta preparado, no es un dato de usuario invalido.
                raise RuntimeError(
                    f"rampa.tipo_incidencia_rampa sin fila "
                    f"{_CODIGO_TIPO_INCIDENCIA_DESVIACION!r} -- ejecutar "
                    "'uv run python -m db.seeds.generate'"
                )
            incidencia_id = generar_id()
            descripcion = (
                f"Tarea {fila_tipo.nombre!r} tardo {duracion_minutos:.1f} min, "
                f"supera el estandar de {fila_tipo.duracion_estandar_min} min "
                f"({duracion_minutos - fila_tipo.duracion_estandar_min:.1f} min de desviacion)."
            )
            severidad = severidad_por_desviacion(es_ruta_critica=fila_tipo.es_ruta_critica)
            insertar_incidencia_rampa(
                conn,
                id=incidencia_id,
                tenant_id=tenant_id,
                tarea_turnaround_id=tarea_id,
                tipo_incidencia_id=tipo_incidencia.id,
                descripcion=descripcion,
                severidad=severidad,
            )
            escribir_journal(
                conn,
                esquema="rampa",
                tabla="incidencia_rampa",
                operacion="INSERT",
                clave_primaria={"id": incidencia_id},
                payload={"id": incidencia_id, "tarea_turnaround_id": tarea_id},
            )
            registrar_auditoria(
                conn,
                esquema="rampa",
                tabla="incidencia_rampa",
                registro_id=incidencia_id,
                operacion="INSERT",
                valores_nuevos={"tarea_turnaround_id": tarea_id, "severidad": severidad},
            )

    return ResultadoFinalizarTarea(
        tarea_id=tarea_id,
        duracion_minutos=duracion_minutos,
        incidencia_generada=incidencia_generada,
    )
