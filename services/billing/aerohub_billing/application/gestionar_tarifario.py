"""Alta y activacion de tarifarios (Sprint S1.6, RF-T10; CU-O17
prerequisito). role_billing_officer publica versiones de precios sin
desplegar codigo -- la formula de calculo no cambia, solo los datos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aerohub_kernel import generar_id

from ..domain import Tarifario
from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_o_actualizar_tarifario_concepto,
    insertar_tarifario,
    marcar_tarifario_vigente,
    obtener_concepto_cargo_por_id,
    obtener_concepto_de_tarifario,
    obtener_tarifario_por_id,
    obtener_tarifario_vigente,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class ConceptoCargoNoEncontrado(Exception):
    pass


class TarifarioNoEncontrado(Exception):
    pass


class TarifarioYaVigente(Exception):
    pass


class UsuarioNoIdentificado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCrearTarifario:
    tarifario_id: int


@reintentar_en_conflicto()
def crear_tarifario(
    *, nombre: str, moneda: str, vigente_desde: date, vigente_hasta: date | None
) -> ResultadoCrearTarifario:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("crear_tarifario requiere una sesion con usuario identificado")
    tenant_id = contexto_tenant_id()
    tarifario_id = generar_id()

    # Domain valida las invariantes de una fila aislada (moneda ISO 4217,
    # ventana de vigencia, estado) antes del INSERT -- fail fast.
    Tarifario(
        id=tarifario_id,
        tenant_id=tenant_id,
        nombre=nombre,
        moneda=moneda,
        vigente_desde=vigente_desde,
        vigente_hasta=vigente_hasta,
        estado="borrador",
        creado_por_usuario_id=usuario_id,
    )

    with sesion() as conn:
        insertar_tarifario(
            conn,
            id=tarifario_id,
            tenant_id=tenant_id,
            nombre=nombre,
            moneda=moneda,
            vigente_desde=vigente_desde,
            vigente_hasta=vigente_hasta,
            creado_por_usuario_id=usuario_id,
        )
        escribir_journal(
            conn,
            esquema="billing",
            tabla="tarifario",
            operacion="INSERT",
            clave_primaria={"id": tarifario_id},
            payload={"id": tarifario_id, "nombre": nombre, "moneda": moneda},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="tarifario",
            registro_id=tarifario_id,
            operacion="INSERT",
            valores_nuevos={"nombre": nombre, "moneda": moneda, "estado": "borrador"},
        )

    return ResultadoCrearTarifario(tarifario_id=tarifario_id)


@dataclass(frozen=True, slots=True)
class ResultadoAgregarConcepto:
    tarifario_concepto_id: int


@reintentar_en_conflicto()
def agregar_concepto_a_tarifario(
    *,
    tarifario_id: int,
    concepto_cargo_id: int,
    tarifa_unitaria: Decimal,
    monto_minimo: Decimal | None,
    monto_maximo: Decimal | None,
) -> ResultadoAgregarConcepto:
    with sesion() as conn:
        if obtener_tarifario_por_id(conn, tarifario_id) is None:
            raise TarifarioNoEncontrado(f"tarifario {tarifario_id} no encontrado")
        if obtener_concepto_cargo_por_id(conn, concepto_cargo_id) is None:
            raise ConceptoCargoNoEncontrado(f"concepto de cargo {concepto_cargo_id} no encontrado")

        existente = obtener_concepto_de_tarifario(
            conn, tarifario_id=tarifario_id, concepto_cargo_id=concepto_cargo_id
        )
        tarifario_concepto_id = existente.id if existente is not None else generar_id()

        insertar_o_actualizar_tarifario_concepto(
            conn,
            id=tarifario_concepto_id,
            tarifario_id=tarifario_id,
            concepto_cargo_id=concepto_cargo_id,
            tarifa_unitaria=tarifa_unitaria,
            monto_minimo=monto_minimo,
            monto_maximo=monto_maximo,
            existente_id=existente.id if existente is not None else None,
        )
        escribir_journal(
            conn,
            esquema="billing",
            tabla="tarifario_concepto",
            operacion="UPDATE" if existente is not None else "INSERT",
            clave_primaria={"id": tarifario_concepto_id},
            payload={"tarifario_id": tarifario_id, "concepto_cargo_id": concepto_cargo_id},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="tarifario_concepto",
            registro_id=tarifario_concepto_id,
            operacion="UPDATE" if existente is not None else "INSERT",
            valores_nuevos={"tarifa_unitaria": str(tarifa_unitaria)},
        )

    return ResultadoAgregarConcepto(tarifario_concepto_id=tarifario_concepto_id)


@reintentar_en_conflicto()
def activar_tarifario(*, tarifario_id: int) -> None:
    """Transiciona 'borrador' -> 'vigente'. A lo sumo un tarifario vigente
    por (tenant_id, moneda) -- regla de dominio que domain/ no puede
    validar por si sola (necesita consultar otras filas), se aplica aqui."""
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        fila = obtener_tarifario_por_id(conn, tarifario_id)
        if fila is None:
            raise TarifarioNoEncontrado(f"tarifario {tarifario_id} no encontrado")

        vigente_actual = obtener_tarifario_vigente(conn, moneda=fila.moneda)
        if vigente_actual is not None and vigente_actual.id != tarifario_id:
            raise TarifarioYaVigente(
                f"ya existe un tarifario vigente ({vigente_actual.id}) para moneda "
                f"{fila.moneda!r} -- desactivarlo antes de activar otro"
            )

        marcar_tarifario_vigente(conn, id=tarifario_id, tenant_id=tenant_id)
        escribir_journal(
            conn,
            esquema="billing",
            tabla="tarifario",
            operacion="UPDATE",
            clave_primaria={"id": tarifario_id},
            payload={"id": tarifario_id, "estado": "vigente"},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="tarifario",
            registro_id=tarifario_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "vigente"},
        )
