"""Ciclo programado de recalculo de tiempos de espera (RF-O17, 2026-08-08).

RF-O17 pide que el estimado se refresque cada <= 15 minutos, pero
`recalcular_tiempos_espera` (CU-O19, S1.6) se construyo como invocacion
explicita por API y su propio docstring dejaba la periodicidad como
"responsabilidad operativa, no de este modulo". En la practica eso
significaba que el dato quedaba tan fresco como la ultima vez que alguien
apretara un boton -- desde S1.6 nadie lo invocaba nunca, porque el modulo
ni siquiera tenia vista.

Mismo patron que el monitor de senal FIDS (RNF-R04, S1.3): un proceso de
plataforma SIN tenant ambiente que recorre todos los tenants bajo
`alcance_global()` (ADR-019 G3), invocado por una tarea de fondo del
gateway. No es un contenedor aparte como `continuidad-agente`: eso es
infraestructura (snapshots, shipper); esto es logica de un modulo de
negocio y vive con el.

Rol del alcance global: `role_operations_controller`, no
`role_platform_admin` como el monitor FIDS. Es el unico rol con el juego
COMPLETO de GRANTs que el ciclo necesita -- SELECT sobre ops.terminal/
puerta/asignacion_puerta y rampa.turnaround, mas INSERT/UPDATE sobre
billing.tiempo_espera_agregado (98_grants_billing.sql:54, que ya lo
designa como el "Sistema" que ejecuta CU-O19). Con role_platform_admin
haria falta un GRANT de escritura nuevo sobre esa tabla.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import ahora_utc

from ..infrastructure import (
    alcance_global,
    listar_terminales_de_todos_los_tenants,
    sesion,
)
from .recalcular_tiempos_espera import recalcular_para_terminal

_MOTIVO_ALCANCE_GLOBAL = "recalculo_programado_tiempos_espera"
_ROL_CICLO = "role_operations_controller"

# Ancho de franja del ciclo automatico. 30 min es el mismo valor por
# defecto que ya usaba el endpoint desde S1.6 -- el ciclo no introduce un
# criterio nuevo de bucketizacion.
FRANJA_MINUTOS_POR_DEFECTO = 30


@dataclass(frozen=True, slots=True)
class ResultadoCicloRecalculo:
    terminales_evaluadas: int
    franjas_actualizadas: int
    franjas_descartadas: int
    terminales_con_error: int


def ejecutar_ciclo_recalculo(
    *, fecha: date | None = None, franja_minutos: int = FRANJA_MINUTOS_POR_DEFECTO
) -> ResultadoCicloRecalculo:
    """Recalcula el dia en curso para TODAS las terminales de TODOS los
    tenants.

    `fecha=None` usa el dia UTC actual: RF-O17 es sobre el tiempo de espera
    de AHORA, no un reproceso historico. Se deja parametrizable solo para
    poder verificarlo contra un dia con datos sembrados.

    Un fallo sobre una terminal no aborta el ciclo -- se cuenta y se sigue
    con la siguiente. Que una terminal quede sin refrescar no justifica
    dejar sin refrescar a las demas.
    """
    dia = fecha if fecha is not None else ahora_utc().date()
    terminales_evaluadas = 0
    franjas_actualizadas = 0
    franjas_descartadas = 0
    terminales_con_error = 0

    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_CICLO), sesion() as conn:
        filas = listar_terminales_de_todos_los_tenants(conn)
        for fila in filas:
            terminales_evaluadas += 1
            try:
                resultado = recalcular_para_terminal(
                    conn,
                    tenant_id=fila.tenant_id,
                    terminal_id=fila.id,
                    fecha=dia,
                    franja_minutos=franja_minutos,
                )
            except Exception:
                terminales_con_error += 1
                continue
            franjas_actualizadas += resultado.franjas_actualizadas
            franjas_descartadas += resultado.franjas_descartadas_por_muestra_insuficiente

    return ResultadoCicloRecalculo(
        terminales_evaluadas=terminales_evaluadas,
        franjas_actualizadas=franjas_actualizadas,
        franjas_descartadas=franjas_descartadas,
        terminales_con_error=terminales_con_error,
    )
