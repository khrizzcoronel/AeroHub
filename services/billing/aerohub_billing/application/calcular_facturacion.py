"""Motor de facturacion (CU-O17, Sprint S1.6, RF-O15, RF-E02 parcial).
"Sistema" como actor -- sin intervencion humana en el calculo (ver
research.md Decision 1: invocado explicitamente via API, no un cron).

Por cada vuelo de la aerolinea en el periodo, genera un cargo_aeronautico
por cada concepto del tarifario vigente (idempotente: si el cargo ya
existe para ese (vuelo, concepto), se omite -- nunca se recalcula, ver
research.md Decision 5). Cantidad: `pax_estimado` del vuelo para el
concepto 'tasa_pasajero' (se omite si es NULL/0 -- sin dato, sin cargo);
1 para el resto (cargo por movimiento -- ops.vuelo no modela MTOW ni horas
de estacionamiento reales en este sprint, ver Assumptions de spec.md).

Todo o nada: si algun vuelo del periodo no tiene tarifario vigente que lo
cubra, la transaccion completa aborta -- no se factura parcialmente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import generar_id

from ..domain import Tarifario, calcular_monto
from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_cargo_aeronautico,
    insertar_factura,
    insertar_factura_linea,
    listar_cargos_no_facturados,
    listar_conceptos_de_tarifario,
    listar_tarifarios_vigentes,
    listar_vuelos_de_aerolinea_en_periodo,
    obtener_cargo_existente,
    obtener_concepto_cargo_por_id,
    obtener_factura_por_tenant_aerolinea_periodo,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)

_CODIGO_CONCEPTO_PAX = "tasa_pasajero"


class PeriodoInvalido(Exception):
    pass


class TarifarioVigenteNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCalcularFacturacion:
    factura_id: int | None
    cargos_calculados: int
    cargos_ya_existentes: int


@reintentar_en_conflicto()
def calcular_facturacion(
    *, aerolinea_id: int, periodo_inicio: date, periodo_fin: date
) -> ResultadoCalcularFacturacion:
    if periodo_fin < periodo_inicio:
        raise PeriodoInvalido(
            f"periodo_fin ({periodo_fin}) no puede ser anterior a periodo_inicio ({periodo_inicio})"
        )
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        vuelos = listar_vuelos_de_aerolinea_en_periodo(
            conn, aerolinea_id=aerolinea_id, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
        if not vuelos:
            # Edge case de spec.md: periodo sin vuelos -> cero cargos,
            # ninguna factura -- no es un error.
            return ResultadoCalcularFacturacion(
                factura_id=None, cargos_calculados=0, cargos_ya_existentes=0
            )

        tarifarios_vigentes = listar_tarifarios_vigentes(conn)
        if not tarifarios_vigentes:
            raise TarifarioVigenteNoEncontrado(
                f"no hay tarifario vigente para el tenant {tenant_id} -- "
                "activar uno antes de calcular la facturacion"
            )
        # Un solo tarifario vigente esperado (ver listar_tarifarios_vigentes).
        tarifario_row = tarifarios_vigentes[0]
        moneda = tarifario_row.moneda

        for vuelo in vuelos:
            if not Tarifario(
                id=tarifario_row.id,
                tenant_id=tarifario_row.tenant_id,
                nombre=tarifario_row.nombre,
                moneda=tarifario_row.moneda,
                vigente_desde=tarifario_row.vigente_desde,
                vigente_hasta=tarifario_row.vigente_hasta,
                estado=tarifario_row.estado,
                creado_por_usuario_id=tarifario_row.creado_por_usuario_id,
            ).vigente_en(vuelo.fecha_operacion):
                raise TarifarioVigenteNoEncontrado(
                    f"el tarifario vigente ({tarifario_row.id}) no cubre la fecha "
                    f"{vuelo.fecha_operacion} del vuelo {vuelo.id} -- todo o nada, "
                    "ningun cargo de este calculo se persiste"
                )

        conceptos_tarifario = listar_conceptos_de_tarifario(conn, tarifario_id=tarifario_row.id)

        cargos_calculados = 0
        cargos_ya_existentes = 0
        for vuelo in vuelos:
            for tc in conceptos_tarifario:
                if obtener_cargo_existente(
                    conn, vuelo_id=vuelo.id, concepto_cargo_id=tc.concepto_cargo_id
                ):
                    cargos_ya_existentes += 1
                    continue

                concepto = obtener_concepto_cargo_por_id(conn, tc.concepto_cargo_id)
                if concepto is None:
                    # fk_tarifario_concepto_concepto lo garantiza -- si
                    # falta, el entorno esta corrupto, no un dato invalido
                    # de usuario (mismo criterio que aerohub_ramp).
                    raise RuntimeError(
                        f"concepto_cargo {tc.concepto_cargo_id} referenciado sin existir"
                    )

                if concepto.codigo == _CODIGO_CONCEPTO_PAX:
                    if not vuelo.pax_estimado:
                        continue  # sin dato de pax, sin cargo -- no se inventa una cantidad
                    cantidad = vuelo.pax_estimado
                else:
                    cantidad = 1

                resultado_calculo = calcular_monto(
                    cantidad=cantidad,
                    tarifa_unitaria=tc.tarifa_unitaria,
                    moneda=moneda,
                    monto_minimo=tc.monto_minimo,
                    monto_maximo=tc.monto_maximo,
                )

                cargo_id = generar_id()
                insertar_cargo_aeronautico(
                    conn,
                    id=cargo_id,
                    tenant_id=tenant_id,
                    vuelo_id=vuelo.id,
                    concepto_cargo_id=tc.concepto_cargo_id,
                    tarifario_concepto_id=tc.id,
                    cantidad=cantidad,
                    tarifa_aplicada=resultado_calculo.tarifa_aplicada,
                    monto_calculado=resultado_calculo.monto.monto,
                )
                escribir_journal(
                    conn,
                    esquema="billing",
                    tabla="cargo_aeronautico",
                    operacion="INSERT",
                    clave_primaria={"id": cargo_id},
                    payload={"vuelo_id": vuelo.id, "concepto_cargo_id": tc.concepto_cargo_id},
                )
                registrar_auditoria(
                    conn,
                    esquema="billing",
                    tabla="cargo_aeronautico",
                    registro_id=cargo_id,
                    operacion="INSERT",
                    valores_nuevos={
                        "monto_calculado": str(resultado_calculo.monto.monto),
                        "tarifa_aplicada": str(resultado_calculo.tarifa_aplicada),
                    },
                )
                cargos_calculados += 1

        factura_existente = obtener_factura_por_tenant_aerolinea_periodo(
            conn, aerolinea_id=aerolinea_id, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
        if factura_existente is not None:
            factura_id = factura_existente.id
        else:
            factura_id = generar_id()
            insertar_factura(
                conn,
                id=factura_id,
                tenant_id=tenant_id,
                aerolinea_id=aerolinea_id,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
                moneda=moneda,
            )
            escribir_journal(
                conn,
                esquema="billing",
                tabla="factura",
                operacion="INSERT",
                clave_primaria={"id": factura_id},
                payload={"aerolinea_id": aerolinea_id},
            )
            registrar_auditoria(
                conn,
                esquema="billing",
                tabla="factura",
                registro_id=factura_id,
                operacion="INSERT",
                valores_nuevos={"aerolinea_id": aerolinea_id, "estado": "borrador"},
            )

        # Cada cargo del vuelo/periodo (nuevo o preexistente sin facturar
        # todavia) se agrupa en la factura -- una linea por cargo, UNIQUE
        # sobre cargo_aeronautico_id (ninguna se duplica).
        vuelo_ids = [v.id for v in vuelos]
        for cargo in listar_cargos_no_facturados(conn, vuelo_ids=vuelo_ids):
            concepto = obtener_concepto_cargo_por_id(conn, cargo.concepto_cargo_id)
            linea_id = generar_id()
            insertar_factura_linea(
                conn,
                id=linea_id,
                factura_id=factura_id,
                cargo_aeronautico_id=cargo.id,
                descripcion=concepto.nombre if concepto is not None else "cargo aeronautico",
                cantidad=cargo.cantidad,
                precio_unitario=cargo.tarifa_aplicada,
                monto=cargo.monto_calculado,
            )
            escribir_journal(
                conn,
                esquema="billing",
                tabla="factura_linea",
                operacion="INSERT",
                clave_primaria={"id": linea_id},
                payload={"factura_id": factura_id, "cargo_aeronautico_id": cargo.id},
            )
            registrar_auditoria(
                conn,
                esquema="billing",
                tabla="factura_linea",
                registro_id=linea_id,
                operacion="INSERT",
                valores_nuevos={
                    "cargo_aeronautico_id": cargo.id,
                    "monto": str(cargo.monto_calculado),
                },
            )

    return ResultadoCalcularFacturacion(
        factura_id=factura_id,
        cargos_calculados=cargos_calculados,
        cargos_ya_existentes=cargos_ya_existentes,
    )
