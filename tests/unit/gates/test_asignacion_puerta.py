from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from aerohub_gates.domain import (
    AsignacionPuerta,
    AsignacionPuertaInvalida,
    IntervaloOcupado,
    PuertaIncompatible,
    SolapamientoPuertaInvalido,
    intervalos_se_solapan,
    puerta_ocupa_intervalo,
    verificar_compatibilidad_envergadura,
    verificar_no_solapamiento,
)

_T0 = datetime(2026, 11, 1, 9, 0, 0, tzinfo=UTC)


def _asignacion(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        vuelo_id=1,
        puerta_id=1,
        inicio_previsto=_T0,
        fin_previsto=_T0 + timedelta(hours=1),
        asignado_por_usuario_id=1,
        asignado_en=_T0,
        estado="planificada",
    )
    base.update(overrides)
    return AsignacionPuerta(**base)


# ---------------------------------------------------------------------------
# AsignacionPuerta -- invariantes
# ---------------------------------------------------------------------------


def test_asignacion_valida_se_construye():
    a = _asignacion()
    assert a.estado == "planificada"


def test_estado_invalido_rechazado():
    with pytest.raises(AsignacionPuertaInvalida):
        _asignacion(estado="en_curso")


def test_fin_previsto_no_posterior_a_inicio_previsto_rechazado():
    with pytest.raises(AsignacionPuertaInvalida):
        _asignacion(inicio_previsto=_T0, fin_previsto=_T0)


def test_fin_previsto_anterior_a_inicio_previsto_rechazado():
    with pytest.raises(AsignacionPuertaInvalida):
        _asignacion(inicio_previsto=_T0, fin_previsto=_T0 - timedelta(minutes=1))


def test_inicio_previsto_naive_rechazado():
    naive = datetime(2026, 11, 1, 9, 0, 0)  # noqa: DTZ001 -- caso de prueba deliberado
    with pytest.raises(AsignacionPuertaInvalida):
        _asignacion(inicio_previsto=naive, fin_previsto=_T0 + timedelta(hours=1))


def test_fin_real_no_posterior_a_inicio_real_rechazado():
    with pytest.raises(AsignacionPuertaInvalida):
        _asignacion(inicio_real=_T0, fin_real=_T0)


def test_inicio_real_y_fin_real_none_no_se_valida():
    a = _asignacion(inicio_real=None, fin_real=None)
    assert a.inicio_real is None


# ---------------------------------------------------------------------------
# puerta_ocupa_intervalo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("estado", ["planificada", "activa"])
def test_puerta_ocupa_intervalo_en_estados_activos(estado):
    assert puerta_ocupa_intervalo(estado)


@pytest.mark.parametrize("estado", ["finalizada", "cancelada"])
def test_puerta_no_ocupa_intervalo_en_estados_liberados(estado):
    assert not puerta_ocupa_intervalo(estado)


# ---------------------------------------------------------------------------
# intervalos_se_solapan -- exhaustivo (Plan §8.4: bordes fin==inicio,
# contencion, solape parcial)
# ---------------------------------------------------------------------------


def test_intervalos_identicos_se_solapan():
    assert intervalos_se_solapan(_T0, _T0 + timedelta(hours=1), _T0, _T0 + timedelta(hours=1))


def test_intervalos_disjuntos_no_se_solapan():
    a_inicio, a_fin = _T0, _T0 + timedelta(hours=1)
    b_inicio, b_fin = _T0 + timedelta(hours=2), _T0 + timedelta(hours=3)
    assert not intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)
    assert not intervalos_se_solapan(b_inicio, b_fin, a_inicio, a_fin)  # simetria


def test_borde_fin_a_igual_inicio_b_no_se_solapan():
    """[T0, T0+1h) y [T0+1h, T0+2h) SOLO se tocan -- semiabierto: no solapan."""
    a_inicio, a_fin = _T0, _T0 + timedelta(hours=1)
    b_inicio, b_fin = _T0 + timedelta(hours=1), _T0 + timedelta(hours=2)
    assert not intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


def test_borde_fin_b_igual_inicio_a_no_se_solapan():
    a_inicio, a_fin = _T0 + timedelta(hours=1), _T0 + timedelta(hours=2)
    b_inicio, b_fin = _T0, _T0 + timedelta(hours=1)
    assert not intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


def test_contencion_b_dentro_de_a_se_solapan():
    a_inicio, a_fin = _T0, _T0 + timedelta(hours=3)
    b_inicio, b_fin = _T0 + timedelta(hours=1), _T0 + timedelta(hours=2)
    assert intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


def test_contencion_a_dentro_de_b_se_solapan():
    a_inicio, a_fin = _T0 + timedelta(hours=1), _T0 + timedelta(hours=2)
    b_inicio, b_fin = _T0, _T0 + timedelta(hours=3)
    assert intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


def test_solape_parcial_por_la_izquierda_se_solapan():
    a_inicio, a_fin = _T0, _T0 + timedelta(hours=2)
    b_inicio, b_fin = _T0 + timedelta(hours=1), _T0 + timedelta(hours=3)
    assert intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


def test_solape_parcial_por_la_derecha_se_solapan():
    a_inicio, a_fin = _T0 + timedelta(hours=1), _T0 + timedelta(hours=3)
    b_inicio, b_fin = _T0, _T0 + timedelta(hours=2)
    assert intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


def test_solape_de_un_segundo_se_solapan():
    """Un solape minimo (1 segundo) sigue siendo solape -- no hay margen
    de tolerancia implicito en la comparacion."""
    a_inicio, a_fin = _T0, _T0 + timedelta(hours=1)
    b_inicio, b_fin = a_fin - timedelta(seconds=1), a_fin + timedelta(hours=1)
    assert intervalos_se_solapan(a_inicio, a_fin, b_inicio, b_fin)


# ---------------------------------------------------------------------------
# verificar_no_solapamiento
# ---------------------------------------------------------------------------


def test_verificar_no_solapamiento_sin_existentes_no_falla():
    verificar_no_solapamiento(inicio=_T0, fin=_T0 + timedelta(hours=1), existentes=[])


def test_verificar_no_solapamiento_con_existente_disjunto_no_falla():
    existente = IntervaloOcupado(
        inicio=_T0 + timedelta(hours=2), fin=_T0 + timedelta(hours=3), asignacion_id=99
    )
    verificar_no_solapamiento(inicio=_T0, fin=_T0 + timedelta(hours=1), existentes=[existente])


def test_verificar_no_solapamiento_con_existente_solapado_falla():
    existente = IntervaloOcupado(
        inicio=_T0 + timedelta(minutes=30), fin=_T0 + timedelta(hours=2), asignacion_id=99
    )
    with pytest.raises(SolapamientoPuertaInvalido) as exc_info:
        verificar_no_solapamiento(inicio=_T0, fin=_T0 + timedelta(hours=1), existentes=[existente])
    assert "99" in str(exc_info.value)


def test_verificar_no_solapamiento_reporta_el_primer_conflicto_entre_varios():
    existentes = [
        IntervaloOcupado(
            inicio=_T0 + timedelta(hours=5), fin=_T0 + timedelta(hours=6), asignacion_id=1
        ),
        IntervaloOcupado(
            inicio=_T0 + timedelta(minutes=30), fin=_T0 + timedelta(hours=2), asignacion_id=2
        ),
    ]
    with pytest.raises(SolapamientoPuertaInvalido) as exc_info:
        verificar_no_solapamiento(inicio=_T0, fin=_T0 + timedelta(hours=1), existentes=existentes)
    assert "2" in str(exc_info.value)


# ---------------------------------------------------------------------------
# verificar_compatibilidad_envergadura
# ---------------------------------------------------------------------------


def test_envergadura_igual_al_maximo_es_compatible():
    verificar_compatibilidad_envergadura(
        envergadura_aeronave_m=Decimal("35.80"), envergadura_max_puerta_m=Decimal("35.80")
    )


def test_envergadura_menor_al_maximo_es_compatible():
    verificar_compatibilidad_envergadura(
        envergadura_aeronave_m=Decimal("20.00"), envergadura_max_puerta_m=Decimal("35.80")
    )


def test_envergadura_mayor_al_maximo_es_incompatible():
    with pytest.raises(PuertaIncompatible):
        verificar_compatibilidad_envergadura(
            envergadura_aeronave_m=Decimal("40.00"), envergadura_max_puerta_m=Decimal("35.80")
        )
