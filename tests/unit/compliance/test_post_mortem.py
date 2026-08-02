from datetime import UTC, datetime

import pytest
from aerohub_compliance.domain import PostMortem, PostMortemInvalido, puede_publicar


def test_puede_publicar_todas_completadas():
    assert puede_publicar(["completada", "completada"]) is True


def test_no_puede_publicar_con_pendiente():
    assert puede_publicar(["completada", "pendiente"]) is False


def test_no_puede_publicar_con_en_progreso():
    assert puede_publicar(["en_progreso"]) is False


def test_puede_publicar_sin_acciones():
    assert puede_publicar([]) is True


def _post_mortem(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        incidente_ref="INC-2026-001",
        severidad="alta",
        estado="en_progreso",
        iniciado_en=datetime(2026, 8, 1, tzinfo=UTC),
    )
    base.update(overrides)
    return PostMortem(**base)


def test_post_mortem_valido_se_construye():
    pm = _post_mortem()
    assert pm.estado == "en_progreso"


def test_severidad_invalida_rechazada():
    with pytest.raises(PostMortemInvalido):
        _post_mortem(severidad="urgente")


def test_incidente_ref_vacio_rechazado():
    with pytest.raises(PostMortemInvalido):
        _post_mortem(incidente_ref="   ")


def test_tiempo_resolucion_negativo_rechazado():
    with pytest.raises(PostMortemInvalido):
        _post_mortem(tiempo_resolucion_min=-1)
