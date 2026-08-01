from datetime import UTC, datetime, timedelta

import pytest
from aerohub_ramp.domain import TareaTurnaround, TareaTurnaroundInvalida, excede_estandar

_T0 = datetime(2026, 11, 1, 8, 0, 0, tzinfo=UTC)


def _tarea(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        turnaround_id=1,
        tipo_tarea_id=1,
        agente_usuario_id=1,
        estado="en_curso",
    )
    base.update(overrides)
    return TareaTurnaround(**base)


def test_tarea_valida_se_construye():
    t = _tarea()
    assert t.estado == "en_curso"


def test_estado_invalido_rechazado():
    with pytest.raises(TareaTurnaroundInvalida):
        _tarea(estado="cancelada")


def test_inicio_real_naive_rechazado():
    naive = datetime(2026, 11, 1, 8, 0, 0)  # noqa: DTZ001 -- caso de prueba deliberado
    with pytest.raises(TareaTurnaroundInvalida):
        _tarea(inicio_real=naive)


def test_fin_real_naive_rechazado():
    naive = datetime(2026, 11, 1, 8, 0, 0)  # noqa: DTZ001 -- caso de prueba deliberado
    with pytest.raises(TareaTurnaroundInvalida):
        _tarea(inicio_real=_T0, fin_real=naive)


def test_fin_real_anterior_a_inicio_real_rechazado():
    with pytest.raises(TareaTurnaroundInvalida):
        _tarea(inicio_real=_T0 + timedelta(minutes=30), fin_real=_T0)


def test_fin_real_igual_a_inicio_real_no_se_rechaza():
    """CHK del DDL usa >=, no > -- una tarea de duracion cero es rara pero
    no invalida (p. ej. un doble-click en la UI que registra ambos
    timestamps casi simultaneos)."""
    t = _tarea(inicio_real=_T0, fin_real=_T0)
    assert t.duracion_minutos() == 0


# ---------------------------------------------------------------------------
# duracion_minutos -- derivada, nunca almacenada (SDD-DATA-001 §8.4)
# ---------------------------------------------------------------------------


def test_duracion_minutos_none_si_no_iniciada():
    t = _tarea(inicio_real=None, fin_real=None)
    assert t.duracion_minutos() is None


def test_duracion_minutos_none_si_iniciada_sin_finalizar():
    t = _tarea(inicio_real=_T0, fin_real=None)
    assert t.duracion_minutos() is None


def test_duracion_minutos_calculada_correctamente():
    t = _tarea(inicio_real=_T0, fin_real=_T0 + timedelta(minutes=45, seconds=30))
    assert t.duracion_minutos() == pytest.approx(45.5)


# ---------------------------------------------------------------------------
# excede_estandar
# ---------------------------------------------------------------------------


def test_duracion_igual_al_estandar_no_excede():
    assert not excede_estandar(duracion_minutos=30.0, duracion_estandar_min=30)


def test_duracion_menor_al_estandar_no_excede():
    assert not excede_estandar(duracion_minutos=25.0, duracion_estandar_min=30)


def test_duracion_mayor_al_estandar_excede():
    assert excede_estandar(duracion_minutos=30.1, duracion_estandar_min=30)
