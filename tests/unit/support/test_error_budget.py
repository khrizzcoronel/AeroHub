"""Pruebas de dominio de calculo de error budget (Sprint S1.8, US2), casos
borde 0%/100%/>100% (spec.md Acceptance Scenarios de US2)."""

import pytest
from aerohub_support.domain import ErrorBudgetInvalido, calcular_consumo_error_budget


def test_uptime_perfecto_consume_cero_por_ciento():
    consumo = calcular_consumo_error_budget(uptime_observado_pct=100.0, objetivo_slo_pct=99.9)
    assert consumo == pytest.approx(0.0)


def test_uptime_igual_al_objetivo_consume_cien_por_ciento():
    """spec.md US2 Acceptance Scenario 3: uptime == objetivo -> consumo == 100%."""
    consumo = calcular_consumo_error_budget(uptime_observado_pct=99.9, objetivo_slo_pct=99.9)
    assert consumo == pytest.approx(100.0)


def test_uptime_por_debajo_del_objetivo_supera_cien_por_ciento():
    consumo = calcular_consumo_error_budget(uptime_observado_pct=99.5, objetivo_slo_pct=99.9)
    assert consumo > 100.0


def test_uptime_fuera_de_rango_rechazado():
    with pytest.raises(ErrorBudgetInvalido):
        calcular_consumo_error_budget(uptime_observado_pct=101.0, objetivo_slo_pct=99.9)
    with pytest.raises(ErrorBudgetInvalido):
        calcular_consumo_error_budget(uptime_observado_pct=-1.0, objetivo_slo_pct=99.9)


def test_objetivo_slo_fuera_de_rango_rechazado():
    with pytest.raises(ErrorBudgetInvalido):
        calcular_consumo_error_budget(uptime_observado_pct=99.9, objetivo_slo_pct=100.0)
    with pytest.raises(ErrorBudgetInvalido):
        calcular_consumo_error_budget(uptime_observado_pct=99.9, objetivo_slo_pct=0.0)
