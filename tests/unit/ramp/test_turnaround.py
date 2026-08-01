from datetime import UTC, datetime, timedelta

import pytest
from aerohub_ramp.domain import Turnaround, TurnaroundInvalido

_T0 = datetime(2026, 11, 1, 8, 0, 0, tzinfo=UTC)


def _turnaround(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        vuelo_llegada_id=1,
        vuelo_salida_id=2,
        aeronave_id=1,
        inicio_previsto=_T0,
        fin_previsto=_T0 + timedelta(hours=2),
        estado="planificado",
    )
    base.update(overrides)
    return Turnaround(**base)


def test_turnaround_valido_se_construye():
    t = _turnaround()
    assert t.estado == "planificado"


def test_vuelos_iguales_rechazado():
    with pytest.raises(TurnaroundInvalido):
        _turnaround(vuelo_llegada_id=5, vuelo_salida_id=5)


def test_estado_invalido_rechazado():
    with pytest.raises(TurnaroundInvalido):
        _turnaround(estado="cancelado")


def test_fin_previsto_no_posterior_a_inicio_previsto_rechazado():
    with pytest.raises(TurnaroundInvalido):
        _turnaround(inicio_previsto=_T0, fin_previsto=_T0)


def test_inicio_previsto_naive_rechazado():
    naive = datetime(2026, 11, 1, 8, 0, 0)  # noqa: DTZ001 -- caso de prueba deliberado
    with pytest.raises(TurnaroundInvalido):
        _turnaround(inicio_previsto=naive, fin_previsto=_T0 + timedelta(hours=2))


def test_fin_real_anterior_a_inicio_real_rechazado():
    with pytest.raises(TurnaroundInvalido):
        _turnaround(inicio_real=_T0 + timedelta(hours=1), fin_real=_T0)


def test_inicio_real_y_fin_real_none_no_se_valida():
    t = _turnaround(inicio_real=None, fin_real=None)
    assert t.inicio_real is None
