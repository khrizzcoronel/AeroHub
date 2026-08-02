"""Conciliacion de pasajeros por vuelo/periodo (Sprint S1.6, CU-O17 paso
de revision humana). role_billing_officer registra el conteo reportado
por la aerolinea; el sistema deriva la diferencia y solo permite marcar
'conciliado' si es cero (compuerta de pruebas obligatoria del sprint).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import ahora_utc, generar_id

from ..domain import diferencia as _diferencia
from ..domain import puede_conciliar
from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_conciliacion_pax,
    marcar_conciliacion_conciliada,
    obtener_conciliacion_por_id,
    obtener_conciliacion_por_vuelo_periodo,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from .gestionar_tarifario import UsuarioNoIdentificado


class ConciliacionYaExiste(Exception):
    pass


class ConciliacionNoEncontrada(Exception):
    pass


class DiferenciaNoNula(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoRegistrarConciliacion:
    conciliacion_id: int
    diferencia: int


@reintentar_en_conflicto()
def registrar_conciliacion(
    *,
    vuelo_id: int,
    periodo: str,
    pax_reportado_aerolinea: int,
    pax_registrado_sistema: int,
    fuente_reporte: str,
) -> ResultadoRegistrarConciliacion:
    tenant_id = contexto_tenant_id()
    conciliacion_id = generar_id()

    with sesion() as conn:
        if obtener_conciliacion_por_vuelo_periodo(conn, vuelo_id=vuelo_id, periodo=periodo):
            raise ConciliacionYaExiste(
                f"ya existe una conciliacion para vuelo {vuelo_id} en el periodo {periodo!r}"
            )

        insertar_conciliacion_pax(
            conn,
            id=conciliacion_id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            periodo=periodo,
            pax_reportado_aerolinea=pax_reportado_aerolinea,
            pax_registrado_sistema=pax_registrado_sistema,
            fuente_reporte=fuente_reporte,
        )
        escribir_journal(
            conn,
            esquema="billing",
            tabla="conciliacion_pax",
            operacion="INSERT",
            clave_primaria={"id": conciliacion_id},
            payload={"vuelo_id": vuelo_id, "periodo": periodo},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="conciliacion_pax",
            registro_id=conciliacion_id,
            operacion="INSERT",
            valores_nuevos={
                "pax_reportado_aerolinea": pax_reportado_aerolinea,
                "pax_registrado_sistema": pax_registrado_sistema,
            },
        )

    return ResultadoRegistrarConciliacion(
        conciliacion_id=conciliacion_id,
        diferencia=_diferencia(
            pax_reportado_aerolinea=pax_reportado_aerolinea,
            pax_registrado_sistema=pax_registrado_sistema,
        ),
    )


@reintentar_en_conflicto()
def conciliar(*, conciliacion_id: int) -> None:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("conciliar requiere una sesion con usuario identificado")
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        fila = obtener_conciliacion_por_id(conn, conciliacion_id)
        if fila is None:
            raise ConciliacionNoEncontrada(f"conciliacion {conciliacion_id} no encontrada")
        if not puede_conciliar(
            pax_reportado_aerolinea=fila.pax_reportado_aerolinea,
            pax_registrado_sistema=fila.pax_registrado_sistema,
        ):
            raise DiferenciaNoNula(
                f"conciliacion {conciliacion_id} tiene diferencia distinta de cero -- "
                "no se puede marcar como conciliada"
            )

        ahora = ahora_utc()
        marcar_conciliacion_conciliada(
            conn,
            id=conciliacion_id,
            tenant_id=tenant_id,
            conciliado_en=ahora,
            usuario_id=usuario_id,
        )
        escribir_journal(
            conn,
            esquema="billing",
            tabla="conciliacion_pax",
            operacion="UPDATE",
            clave_primaria={"id": conciliacion_id},
            payload={"id": conciliacion_id, "conciliado_en": ahora.isoformat()},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="conciliacion_pax",
            registro_id=conciliacion_id,
            operacion="UPDATE",
            valores_nuevos={"conciliado_por_usuario_id": usuario_id},
        )
