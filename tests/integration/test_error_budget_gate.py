"""Compuertas de pruebas de S1.8 (Plan Sec8.8, US3): los 4 casos de
`tools/verificar_error_budget.py` -- bloquea, override con motivo (auditado
en compliance.log_auditoria real), override sin motivo (sin auditar), no
bloquea -- Escenario 3 de quickstart.md. El consumo de error budget se fija
por fixture (monkeypatch de la consulta a Prometheus, sin depender de
trafico real ni de tumbar el Gateway 80% de un mes); la escritura de
auditoria SI es contra MonetDB real.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

_RUTA_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "verificar_error_budget.py"
_spec = importlib.util.spec_from_file_location(
    "_verificar_error_budget_bajo_prueba", _RUTA_SCRIPT
)
assert _spec is not None and _spec.loader is not None
verificar_error_budget = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = verificar_error_budget
_spec.loader.exec_module(verificar_error_budget)


def _fijar_uptime(monkeypatch: pytest.MonkeyPatch, uptime_pct: float) -> None:
    monkeypatch.setattr(
        "aerohub_support.application.consultar_observabilidad.consultar_uptime_mensual",
        lambda servicio, **kwargs: uptime_pct,
    )


def _contar_auditoria(admin_engine) -> int:
    with admin_engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT COUNT(*) FROM compliance.log_auditoria "
                "WHERE esquema = 'observabilidad' AND tabla = 'bloqueo_despliegue'"
            )
        ).scalar_one()


def test_bloquea_sin_override(monkeypatch):
    _fijar_uptime(monkeypatch, 50.0)  # muy por debajo de 99.9% -> consumo >> 80%
    codigo = verificar_error_budget.main(["--servicio", "aodb"])
    assert codigo == 1


def test_no_bloquea_cuando_consumo_bajo(monkeypatch):
    _fijar_uptime(monkeypatch, 99.95)  # por encima del objetivo -> consumo < 80%
    codigo = verificar_error_budget.main(["--servicio", "aodb"])
    assert codigo == 0


def test_override_sin_motivo_rechazado_sin_auditar(monkeypatch, admin_engine):
    _fijar_uptime(monkeypatch, 50.0)
    antes = _contar_auditoria(admin_engine)

    codigo = verificar_error_budget.main(["--servicio", "aodb", "--override"])
    assert codigo == 2

    assert _contar_auditoria(admin_engine) == antes


def test_override_con_motivo_libera_y_audita(monkeypatch, admin_engine):
    _fijar_uptime(monkeypatch, 50.0)
    antes = _contar_auditoria(admin_engine)

    codigo = verificar_error_budget.main(
        ["--servicio", "aodb", "--override", "--motivo", "prueba de integracion S1.8"]
    )
    assert codigo == 0

    assert _contar_auditoria(admin_engine) == antes + 1
