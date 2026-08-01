from datetime import UTC, datetime

import pytest
from aerohub_ramp.domain import IncidenciaRampa, IncidenciaRampaInvalida, severidad_por_desviacion

_AHORA = datetime(2026, 11, 1, 8, 0, 0, tzinfo=UTC)


def _incidencia(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        tarea_turnaround_id=1,
        tipo_incidencia_id=1,
        descripcion="desviacion detectada",
        severidad="media",
        detectada_en=_AHORA,
    )
    base.update(overrides)
    return IncidenciaRampa(**base)


def test_incidencia_valida_se_construye():
    i = _incidencia()
    assert i.severidad == "media"


def test_descripcion_vacia_rechazada():
    with pytest.raises(IncidenciaRampaInvalida):
        _incidencia(descripcion="   ")


def test_severidad_invalida_rechazada():
    with pytest.raises(IncidenciaRampaInvalida):
        _incidencia(severidad="urgente")


def test_severidad_por_desviacion_ruta_critica_es_alta():
    assert severidad_por_desviacion(es_ruta_critica=True) == "alta"


def test_severidad_por_desviacion_no_critica_es_media():
    assert severidad_por_desviacion(es_ruta_critica=False) == "media"
