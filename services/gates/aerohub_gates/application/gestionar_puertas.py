"""Alta de terminal y puerta, edicion de puerta (Fase 3 de
docs/diseno/PLAN_CORRECCION_MODULOS.md, causa raiz backend: M3 solo tenia
el tablero de solo lectura y el flujo de asignacion -- ninguna forma de
dar de alta la terminal o la puerta misma desde la API).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import generar_id

from ..domain import validar_puerta, validar_terminal
from ..infrastructure import (
    actualizar_puerta as _actualizar_puerta_infra,
)
from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_puerta,
    insertar_terminal,
    listar_terminales,
    obtener_puerta_por_codigo,
    obtener_puerta_por_id,
    obtener_terminal_por_codigo,
    obtener_terminal_por_id,
    registrar_auditoria,
    sesion,
)
from .asignar_puerta import PuertaNoEncontrada

__all__ = [
    "TerminalDuplicada",
    "PuertaDuplicada",
    "TerminalNoEncontrada",
    "TerminalListado",
    "ResultadoCrearTerminal",
    "ResultadoCrearPuerta",
    "crear_terminal",
    "listar_terminales_del_tenant",
    "crear_puerta",
    "actualizar_puerta",
]


class TerminalDuplicada(Exception):
    pass


class PuertaDuplicada(Exception):
    pass


class TerminalNoEncontrada(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TerminalListado:
    id: int
    codigo: str
    nombre: str


@dataclass(frozen=True, slots=True)
class ResultadoCrearTerminal:
    terminal_id: int


@dataclass(frozen=True, slots=True)
class ResultadoCrearPuerta:
    puerta_id: int


def crear_terminal(*, codigo: str, nombre: str) -> ResultadoCrearTerminal:
    validar_terminal(codigo=codigo, nombre=nombre)
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        if obtener_terminal_por_codigo(conn, codigo) is not None:
            raise TerminalDuplicada(f"ya existe una terminal con codigo {codigo!r}")
        terminal_id = generar_id()
        insertar_terminal(conn, id=terminal_id, tenant_id=tenant_id, codigo=codigo, nombre=nombre)
        escribir_journal(
            conn,
            esquema="ops",
            tabla="terminal",
            operacion="INSERT",
            clave_primaria={"id": terminal_id},
            payload={"codigo": codigo, "nombre": nombre},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="terminal",
            registro_id=terminal_id,
            operacion="INSERT",
            valores_nuevos={"codigo": codigo, "nombre": nombre},
        )
    return ResultadoCrearTerminal(terminal_id=terminal_id)


def listar_terminales_del_tenant() -> list[TerminalListado]:
    with sesion() as conn:
        filas = listar_terminales(conn)
    return [TerminalListado(id=f.id, codigo=f.codigo, nombre=f.nombre) for f in filas]


def crear_puerta(
    *, terminal_id: int, codigo: str, tipo: str, envergadura_max_m: float, tiene_pasarela: bool
) -> ResultadoCrearPuerta:
    validar_puerta(codigo=codigo, tipo=tipo, envergadura_max_m=envergadura_max_m)
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        if obtener_terminal_por_id(conn, terminal_id) is None:
            raise TerminalNoEncontrada(f"terminal {terminal_id} no encontrada")
        if obtener_puerta_por_codigo(conn, codigo) is not None:
            raise PuertaDuplicada(f"ya existe una puerta con codigo {codigo!r}")
        puerta_id = generar_id()
        insertar_puerta(
            conn,
            id=puerta_id,
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            codigo=codigo,
            tipo=tipo,
            envergadura_max_m=envergadura_max_m,
            tiene_pasarela=tiene_pasarela,
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="puerta",
            operacion="INSERT",
            clave_primaria={"id": puerta_id},
            payload={"codigo": codigo, "tipo": tipo},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="puerta",
            registro_id=puerta_id,
            operacion="INSERT",
            valores_nuevos={"codigo": codigo, "tipo": tipo},
        )
    return ResultadoCrearPuerta(puerta_id=puerta_id)


def actualizar_puerta(
    *,
    puerta_id: int,
    terminal_id: int,
    codigo: str,
    tipo: str,
    envergadura_max_m: float,
    tiene_pasarela: bool,
) -> None:
    validar_puerta(codigo=codigo, tipo=tipo, envergadura_max_m=envergadura_max_m)
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        fila_actual = obtener_puerta_por_id(conn, puerta_id)
        if fila_actual is None:
            raise PuertaNoEncontrada(f"puerta {puerta_id} no encontrada")
        if obtener_terminal_por_id(conn, terminal_id) is None:
            raise TerminalNoEncontrada(f"terminal {terminal_id} no encontrada")
        if codigo != fila_actual.codigo and obtener_puerta_por_codigo(conn, codigo) is not None:
            raise PuertaDuplicada(f"ya existe una puerta con codigo {codigo!r}")
        _actualizar_puerta_infra(
            conn,
            id=puerta_id,
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            codigo=codigo,
            tipo=tipo,
            envergadura_max_m=envergadura_max_m,
            tiene_pasarela=tiene_pasarela,
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="puerta",
            operacion="UPDATE",
            clave_primaria={"id": puerta_id},
            payload={"codigo": codigo, "tipo": tipo},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="puerta",
            registro_id=puerta_id,
            operacion="UPDATE",
            valores_nuevos={"codigo": codigo, "tipo": tipo},
        )
