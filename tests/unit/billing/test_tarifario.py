from datetime import date

from aerohub_billing.domain import Tarifario


def _tarifario(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        nombre="Tarifario de prueba",
        moneda="USD",
        vigente_desde=date(2026, 1, 1),
        estado="vigente",
        creado_por_usuario_id=1,
    )
    base.update(overrides)
    return Tarifario(**base)


def test_vigente_en_dentro_de_la_ventana():
    t = _tarifario(vigente_desde=date(2026, 1, 1), vigente_hasta=date(2026, 12, 31))
    assert t.vigente_en(date(2026, 6, 15)) is True


def test_no_vigente_antes_de_vigente_desde():
    t = _tarifario(vigente_desde=date(2026, 6, 1))
    assert t.vigente_en(date(2026, 1, 1)) is False


def test_no_vigente_despues_de_vigente_hasta():
    t = _tarifario(vigente_desde=date(2026, 1, 1), vigente_hasta=date(2026, 6, 30))
    assert t.vigente_en(date(2026, 7, 1)) is False


def test_sin_vigente_hasta_cubre_indefinidamente():
    t = _tarifario(vigente_desde=date(2026, 1, 1), vigente_hasta=None)
    assert t.vigente_en(date(2030, 1, 1)) is True


def test_estado_borrador_nunca_vigente():
    t = _tarifario(estado="borrador", vigente_desde=date(2026, 1, 1))
    assert t.vigente_en(date(2026, 1, 1)) is False
