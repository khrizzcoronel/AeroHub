"""Pruebas de dominio de ticket (Sprint S1.8, US1): maquina de estados y
calculo de sla_objetivo_min (data-model.md, FR-002/FR-003)."""

from datetime import UTC, datetime

import pytest
from aerohub_support.domain import (
    Ticket,
    TicketInvalido,
    TicketMensaje,
    calcular_sla_objetivo_min,
    transicion_valida_ticket,
)


def _ticket(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        categoria_id=1,
        creado_por_usuario_id=1,
        severidad="alta",
        estado="abierto",
        asunto="Vuelo retrasado",
        creado_en=datetime(2026, 8, 1, tzinfo=UTC),
        sla_objetivo_min=119,
    )
    base.update(overrides)
    return Ticket(**base)


def test_ticket_valido_se_construye():
    t = _ticket()
    assert t.estado == "abierto"


def test_severidad_invalida_rechazada():
    with pytest.raises(TicketInvalido):
        _ticket(severidad="urgente")


def test_estado_invalido_rechazado():
    with pytest.raises(TicketInvalido):
        _ticket(estado="pendiente")


def test_asunto_vacio_rechazado():
    with pytest.raises(TicketInvalido):
        _ticket(asunto="   ")


def test_sla_objetivo_no_positivo_rechazado():
    with pytest.raises(TicketInvalido):
        _ticket(sla_objetivo_min=0)


def test_ticket_mensaje_valido():
    m = TicketMensaje(
        id=1,
        ticket_id=1,
        autor_usuario_id=1,
        cuerpo="Estamos investigando.",
        enviado_en=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert m.es_interno is False


def test_ticket_mensaje_cuerpo_vacio_rechazado():
    with pytest.raises(TicketInvalido):
        TicketMensaje(
            id=1,
            ticket_id=1,
            autor_usuario_id=1,
            cuerpo="   ",
            enviado_en=datetime(2026, 8, 1, tzinfo=UTC),
        )


@pytest.mark.parametrize("codigo", ["AODB", "aodb", "FIDS", "GATES"])
def test_sla_objetivo_menor_a_120_para_modulos_de_operacion_en_tiempo_real(codigo):
    assert calcular_sla_objetivo_min(codigo) < 120


def test_sla_objetivo_menor_a_240_para_rampa():
    assert calcular_sla_objetivo_min("RAMPA") < 240


def test_sla_objetivo_categoria_desconocida_usa_default_razonable():
    assert calcular_sla_objetivo_min("NO_EXISTE") > 0


@pytest.mark.parametrize(
    ("actual", "nuevo", "esperado"),
    [
        ("abierto", "en_progreso", True),
        ("abierto", "resuelto", False),
        ("abierto", "cerrado", False),
        ("en_progreso", "esperando_cliente", True),
        ("en_progreso", "resuelto", True),
        ("esperando_cliente", "en_progreso", True),
        ("esperando_cliente", "resuelto", False),
        ("resuelto", "cerrado", True),
        ("resuelto", "abierto", False),
        ("cerrado", "abierto", False),
        ("cerrado", "en_progreso", False),
    ],
)
def test_transicion_valida_ticket(actual, nuevo, esperado):
    assert transicion_valida_ticket(actual, nuevo) is esperado
